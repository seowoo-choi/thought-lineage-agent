from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from .codex_adapter import research
from .evidence_extractor import extract
from .graph_builder import build, MAX_ATLAS_NODES, MAX_ATLAS_EDGES
from .query_planner import build_prompt, select_frontier


def _merge(base: dict | None, addition: dict) -> dict:
    if not base:
        return addition
    merged = dict(base)
    merged["status"] = addition.get("status", base.get("status", "complete"))
    nodes = {node["id"]: node for node in base.get("nodes", [])}
    for node in addition.get("nodes", []):
        nodes.setdefault(node["id"], node)
    edge_by_key = {
        (edge["source"], edge["target"], edge["relation_type"]): edge
        for edge in base.get("edges", [])
    }
    for edge in addition.get("edges", []):
        key = (edge["source"], edge["target"], edge["relation_type"])
        if key not in edge_by_key:
            edge_by_key[key] = edge
            continue
        current = edge_by_key[key]
        seen = {source["url"] for source in current.get("sources", [])}
        current["sources"] += [
            source for source in edge.get("sources", [])
            if source["url"] not in seen
        ]
        current["importance"] = max(current.get("importance", 0), edge.get("importance", 0))
    merged["nodes"] = list(nodes.values())
    merged["edges"] = list(edge_by_key.values())
    return merged


def _frontier_batch(current: dict, width: int, attempted: set[str]) -> list[dict]:
    candidates = [item for item in select_frontier(current, per_direction=50)
                  if item["id"] not in attempted]
    later = [item for item in candidates if item["direction"] == "later"]
    prior = [item for item in candidates if item["direction"] == "prior"]
    ordered=[]
    for index in range(max(len(later),len(prior))):
        if index < len(later): ordered.append(later[index])
        if index < len(prior): ordered.append(prior[index])
    # Persist a FIFO queue. Newly discovered leaves are appended behind older
    # unattempted leaves, preventing a successful branch from starving peers.
    meta=current.setdefault("meta",{})
    if meta.get("frontier_strategy_version") != 2:
        meta["frontier_queue"]=[]
        meta["frontier_strategy_version"]=2
    queue=meta.setdefault("frontier_queue",[])
    valid={item["id"]:item for item in ordered}
    queue[:]=[valid[item["id"]] for item in queue
              if item.get("id") in valid and item.get("id") not in attempted]
    queued={item["id"] for item in queue}
    queue.extend(item for item in ordered if item["id"] not in queued)
    batch=queue[:width]
    del queue[:width]
    return batch


def _write_checkpoint(current: dict, checkpoint: Path, calls: list,
                      rounds_completed: int, started: float) -> None:
    current.setdefault("meta", {})["execution"] = {
        "calls": calls,
        "rounds_completed": rounds_completed,
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
    checkpoint.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")


def run(title, author, seed, timeout, cwd, checkpoint, fixture=None,
        deadline=None, reserve_seconds=None, rounds=3, initial=None, focus=None,
        frontier_width=4, expand_node_id=None):
    started = time.monotonic()
    deadline = deadline if deadline is not None else started + max(0, timeout)
    reserve_seconds = min(10.0, max(.05, timeout * .05)) if reserve_seconds is None else reserve_seconds
    work_deadline = deadline - reserve_seconds
    calls = []
    current = build(initial) if initial else None
    rounds_completed = 0
    failures = []
    expansion_queue = {"prior": [], "later": []}
    expansion_queued = set()

    if fixture is not None:
        current = build(fixture(seed))
        calls.append({"adapter": "fixture", "paid_api": False, "completed": True})
        rounds_completed = 1
    else:
        for round_index in range(max(1, rounds)):
            if time.monotonic() >= work_deadline:
                break
            # The first call seeds a new graph. Every later call is dedicated
            # to exactly one frontier node, so the model cannot silently skip it.
            if current is None:
                try:
                    payload = extract(research(
                        build_prompt(title, author, seed, None, round_index, focus),
                        cwd / "schema/research-result.schema.json", cwd,
                        max(.05, work_deadline-time.monotonic()), calls,
                    ))
                    current = build(payload)
                    rounds_completed += 1
                    current.setdefault("meta", {})["round"] = round_index + 1
                    _write_checkpoint(current, checkpoint, calls, rounds_completed, started)
                except (TimeoutError, subprocess.TimeoutExpired) as exc:
                    failures.append(exc); break
                except Exception as exc:
                    failures.append(exc); break
                continue

            attempts = current.setdefault("meta", {}).setdefault("frontier_attempts", [])
            attempted_ids = {item.get("node_id") for item in attempts
                             if item.get("status") in {"expanded", "no_supported_additions"}}
            if expand_node_id and round_index == 0:
                node = next((item for item in current.get("nodes", [])
                             if item.get("id") == expand_node_id), None)
                if node is None:
                    failures.append(ValueError(f"unknown expansion node: {expand_node_id}"))
                    break
                # A clicked node becomes a local research anchor. Investigate
                # both what led into it and what grew out of it, regardless of
                # which side it occupied in the original atlas.
                directions = ["prior", "later"]
                batch = [{
                    "id": node["id"], "label": node["label"], "kind": node["kind"],
                    "era": node["era"], "direction": direction, "depth": 0,
                } for direction in directions]
            elif expand_node_id:
                batch = []
                for index in range(max(1, frontier_width)):
                    preferred = "later" if index % 2 == 0 else "prior"
                    fallback = "prior" if preferred == "later" else "later"
                    queue = expansion_queue[preferred] or expansion_queue[fallback]
                    if not queue:
                        break
                    batch.append(queue.pop(0))
            else:
                batch = _frontier_batch(current, max(1, frontier_width), attempted_ids)
            if not batch:
                break
            wave_growth = False
            for frontier in batch:
                if time.monotonic() >= work_deadline:
                    break
                before_ids = {node["id"] for node in current.get("nodes", [])}
                before_nodes = len(before_ids)
                before_edges = len(current.get("edges", []))
                attempt = {
                    "round": round_index + 1, "node_id": frontier["id"],
                    "label": frontier["label"], "direction": frontier["direction"],
                    "status": "running",
                }
                attempts.append(attempt)
                try:
                    payload = extract(research(
                        build_prompt(title, author, seed, current, round_index, focus,
                                     frontier_override=[frontier]),
                        cwd / "schema/research-result.schema.json", cwd,
                        max(.05, work_deadline-time.monotonic()), calls,
                    ))
                    current = build(_merge(current, payload))
                    if expand_node_id:
                        next_depth = int(frontier.get("depth", 0)) + 1
                        for added in current.get("nodes", []):
                            if added["id"] in before_ids:
                                continue
                            key = (added["id"], frontier["direction"])
                            if key in expansion_queued:
                                continue
                            expansion_queued.add(key)
                            expansion_queue[frontier["direction"]].append({
                                "id": added["id"], "label": added["label"],
                                "kind": added["kind"], "era": added["era"],
                                "direction": frontier["direction"], "depth": next_depth,
                            })
                    added_nodes = len(current.get("nodes", [])) - before_nodes
                    added_edges = len(current.get("edges", [])) - before_edges
                    attempt.update(
                        status="expanded" if added_nodes > 0 or added_edges > 0 else "no_supported_additions",
                        added_nodes=max(0, added_nodes), added_edges=max(0, added_edges),
                    )
                    wave_growth = wave_growth or added_nodes > 0 or added_edges > 0
                except (TimeoutError, subprocess.TimeoutExpired) as exc:
                    attempt.update(status="timed_out", error=type(exc).__name__)
                    failures.append(exc)
                    break
                except Exception as exc:
                    attempt.update(status="failed", error=type(exc).__name__)
                    failures.append(exc)
                _write_checkpoint(current, checkpoint, calls, rounds_completed, started)
                if len(current.get("nodes", [])) >= MAX_ATLAS_NODES or len(current.get("edges", [])) >= MAX_ATLAS_EDGES:
                    break
            rounds_completed += 1
            current.setdefault("meta", {})["round"] = round_index + 1
            current["meta"].setdefault("frontier_history", []).append({
                "round": round_index + 1, "nodes": batch,
            })
            _write_checkpoint(current, checkpoint, calls, rounds_completed, started)
            if len(current.get("nodes", [])) >= MAX_ATLAS_NODES or len(current.get("edges", [])) >= MAX_ATLAS_EDGES:
                break

    if current is None:
        status = "timed_out" if time.monotonic() >= work_deadline else "partial"
        current = _fallback(title, author, seed, status, failures[-1] if failures else TimeoutError("research did not start"))
    else:
        current = build(current)
        if failures:
            current["status"] = "partial"
            current.setdefault("meta", {})["failure"] = {
                "type": type(failures[-1]).__name__, "message": str(failures[-1])[-2000:]
            }
        elif time.monotonic() >= work_deadline:
            current["status"] = "timed_out"
        else:
            current["status"] = "complete"

    current.setdefault("meta", {})["execution"] = {
        "calls": calls,
        "rounds_completed": rounds_completed,
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
    if focus:
        current["meta"]["focus_candidates"] = list(focus)
    checkpoint.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    return current


def _fallback(title, author, seed, status, exc):
    return {
        "meta": {
            "title": title, "author": author, "anchor_id": "anchor", "seed": seed,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "failure": {"type": type(exc).__name__, "message": str(exc)[-2000:]},
        },
        "status": status,
        "nodes": [{
            "id": "anchor", "label": f"{title} — {author}", "kind": "book",
            "era": "unknown", "side": "anchor", "summary": "조사 실패 시 보존된 중심 앵커",
        }],
        "edges": [],
    }
