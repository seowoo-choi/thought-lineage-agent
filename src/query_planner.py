from __future__ import annotations

import json


def normalize(title: str, author: str) -> tuple[str, str]:
    return " ".join(title.split()).strip("《》\"'"), " ".join(author.split())


def _snapshot(data: dict | None) -> dict:
    if not data:
        return {"nodes": [], "edges": []}
    return {
        "nodes": [
            {k: node.get(k) for k in ("id", "label", "kind", "era", "side")}
            for node in data.get("nodes", [])
        ],
        "edges": [
            {k: edge.get(k) for k in ("id", "source", "target", "relation_type")}
            for edge in data.get("edges", [])
        ],
    }


def select_frontier(data: dict | None, per_direction: int = 8) -> list[dict]:
    """Choose nodes needing a dedicated outward-expansion investigation."""
    if not data:
        return []
    nodes = {node["id"]: node for node in data.get("nodes", [])}
    incoming = {node_id: 0 for node_id in nodes}
    outgoing = {node_id: 0 for node_id in nodes}
    importance = {node_id: 0 for node_id in nodes}
    for edge in data.get("edges", []):
        source, target = edge.get("source"), edge.get("target")
        if source in outgoing: outgoing[source] += 1
        if target in incoming: incoming[target] += 1
        score = int(edge.get("importance", 0))
        if source in importance: importance[source] = max(importance[source], score)
        if target in importance: importance[target] = max(importance[target], score)
    # A node is not 'finished' merely because one child was found. Nietzsche,
    # for example, can lead to both Foucault and Kundera. Dedicated-attempt
    # history in research_engine, not degree zero, decides completion.
    prior = [node for node in nodes.values() if node.get("side") == "prior"]
    later = [node for node in nodes.values() if node.get("side") == "later"]
    key = lambda node: (-importance[node["id"]], node.get("era", ""), node.get("label", ""))
    result = []
    for direction, candidates in (("prior", prior), ("later", later)):
        for node in sorted(candidates, key=key)[:per_direction]:
            result.append({
                "id": node["id"], "label": node["label"], "kind": node["kind"],
                "era": node["era"], "direction": direction,
            })
    return result


def build_prompt(title: str, author: str, seed: int,
                 existing: dict | None = None, round_index: int = 0,
                 focus: list[str] | tuple[str, ...] | None = None,
                 frontier_override: list[dict] | None = None) -> str:
    title, author = normalize(title, author)
    if not existing:
        expansion = """Start with the anchor and discover both directions. Build a useful multi-hop network when evidence allows, but do not force fixed counts or ancient sources when they are not relevant to the input. Do not stop at a star-shaped list of direct neighbors. Include documented chains such as author→work→movement→anchor and anchor→later author→later work. Quantitative minimums for a representative fixture belong to acceptance tests, not to arbitrary live inputs."""
    else:
        snapshot = json.dumps(_snapshot(existing), ensure_ascii=False, separators=(",", ":"))
        frontier_items = select_frontier(existing) if frontier_override is None else frontier_override
        frontier = json.dumps(frontier_items, ensure_ascii=False, separators=(",", ":"))
        expansion = f"""This is recursive expansion round {round_index + 1}. The existing graph snapshot is below.
{snapshot}

The algorithm selected these EXPANSION CANDIDATES for this round:
{frontier}

This is a dedicated expansion call: investigate EVERY listed item and no other candidate. A candidate may already have one or more edges; those do not make its influence coverage complete. For direction=prior, find 3–5 additional older documented sources that lead into that node. For direction=later, find 3–5 additional later authors, works, schools, or critical responses influenced by that node. Do not return relationships already present in the snapshot. Every new node must have an edge to the selected candidate or to another new node on a supported path from it. You may reference existing node ids as edge endpoints. It is acceptable to return none when evidence is insufficient. Prefer multi-hop paths. Avoid duplicate labels and duplicate relationships. For later reception, search critical engagement and opposition as well as direct influence; classify documented disagreement as critical_response rather than generic thematic similarity."""
    focus_items = [item.strip() for item in (focus or []) if item.strip()]
    focus_instruction = ""
    if focus_items:
        focus_instruction = f"""
Explicitly investigate these user-supplied possible omissions: {json.dumps(focus_items, ensure_ascii=False)}.
They are candidates, not presumed facts. A candidate does NOT need a direct edge to the anchor. Search for the shortest well-supported path from ANY existing node to the candidate, and return every necessary intermediate node and edge. Evaluate each edge separately. Prefer an existing frontier node over inventing an anchor→candidate relationship. For example, when an existing intermediary can be documented as influencing a focused later author, connect intermediary→that author; do not force anchor→that author. Include each candidate only when admissible sources document every added edge. A documented rejection or opposition must be relation_type=critical_response. If no complete supported path to the existing graph meets the source policy, omit the candidate and do not invent a connection."""
    return f"""Research a bidirectional literary influence graph anchored on {title} by {author}.
Use live public web research and return JSON only, exactly matching the supplied schema. Seed={seed}.
{expansion}
{focus_instruction}

Trace prior works/authors/movements/ancient scriptures into the anchor and later works/authors/movements influenced by or critically responding to it. Prefer strong, important evidence; maximum 50 nodes and 80 edges; no orphan nodes.
Every edge needs a reader-friendly explanation, relation_type, evidence summary, material title, URL, grade, importance and sources. Never use blogs, Wikipedia, search-result pages, DOAJ or other index/aggregator pages as evidence, or unsupported summaries. When an index identifies a paper, cite the original journal or university publisher page. Explicit relationships require >=1 A/B source. Interpretive thematic/ideological/critical_response/movement relationships require >=2 A/B sources from independent publishers. The first source must duplicate source_url/material_title. Do not infer influence from similarity alone. Do not include credentials, tokens, cookies, environment data, or prose outside JSON."""
