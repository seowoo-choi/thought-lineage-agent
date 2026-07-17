from __future__ import annotations

import argparse
import json
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .graph_builder import build
from .html_renderer import render
from .research_engine import run
from .result_validator import assert_valid


RUNTIME_JS = r"""
(() => {
  const restoreKey = 'thought-lineage-last-expansion';
  const controls = document.querySelector('.controls');
  const button = document.createElement('button');
  const status = document.createElement('span');
  button.textContent = '노드를 선택하세요';
  button.disabled = true;
  button.id = 'expand-selected';
  status.style.cssText = 'font-size:11px;color:#98a2bc;min-width:120px';
  controls.append(button, status);
  let selected = null;
  document.addEventListener('click', event => {
    const node = event.target.closest && event.target.closest('.node');
    if (!node) return;
    selected = node.getAttribute('data-id');
    const label = (node.querySelector('text') || {}).textContent || selected;
    button.disabled = false;
    button.textContent = `${label} 다시 분석·확장`;
    status.textContent = '';
  }, true);
  button.addEventListener('click', async () => {
    if (!selected) return;
    button.disabled = true;
    status.textContent = 'Codex가 웹을 조사 중입니다…';
    try {
      const response = await fetch('/api/expand', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({node_id: selected})
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
      if (result.added_nodes === 0 && result.added_edges === 0) {
        status.textContent = '검증 기준을 통과한 새 연결이 없습니다';
        button.disabled = false;
        window.atlasUI?.selectNode(selected, true);
        return;
      }
      sessionStorage.setItem(restoreKey, JSON.stringify(result));
      status.textContent = `노드 ${result.added_nodes}개 · 연결 ${result.added_edges}개 추가 · 확장 지도로 이동 중`;
      window.location.reload();
    } catch (error) {
      status.textContent = `실패: ${error.message}`;
      button.disabled = false;
    }
  });
  const restoredRaw = sessionStorage.getItem(restoreKey);
  if (restoredRaw) {
    sessionStorage.removeItem(restoreKey);
    try {
      const restored = JSON.parse(restoredRaw);
      requestAnimationFrame(() => requestAnimationFrame(() => {
        if (!window.atlasUI?.selectNode(restored.node_id, true)) return;
        selected = restored.node_id;
        button.disabled = false;
        button.textContent = `${restored.node_label || restored.node_id} 다시 분석·확장`;
        status.textContent = `확장 완료 · 노드 +${restored.added_nodes} · 연결 +${restored.added_edges}`;
      }));
    } catch (_) {
      // A stale browser-session value must never break the atlas.
    }
  }
})();
"""


class ExpansionApp:
    def __init__(self, root: Path, checkpoint: Path, html: Path,
                 title: str, author: str, timeout: int,
                 expansion_rounds: int = 3, expansion_width: int = 2):
        self.root = root
        self.checkpoint = checkpoint
        self.html = html
        self.title = title
        self.author = author
        self.timeout = timeout
        self.expansion_rounds = max(1, expansion_rounds)
        self.expansion_width = max(1, expansion_width)
        self.lock = threading.Lock()

    def _load(self) -> dict:
        data = build(json.loads(self.checkpoint.read_text(encoding="utf-8")))
        assert_valid(data)
        return data

    def page(self) -> bytes:
        # Always render from the checkpoint so a source-code/UI update is
        # visible immediately even when an older HTML file already exists.
        render(self._load(), self.html)
        source = self.html.read_text(encoding="utf-8")
        source = source.replace("</body>", '<script src="/app-runtime.js"></script></body>')
        return source.encode("utf-8")

    def expand(self, node_id: str) -> dict:
        initial = self._load()
        selected = next((node for node in initial["nodes"] if node["id"] == node_id), None)
        if selected is None:
            raise ValueError("선택한 노드를 현재 그래프에서 찾을 수 없습니다")
        before_nodes, before_edges = len(initial["nodes"]), len(initial["edges"])
        started = time.monotonic()
        data = run(
            self.title, self.author, initial.get("meta", {}).get("seed", 1866),
            self.timeout, self.root, self.checkpoint, initial=initial,
            deadline=started + self.timeout, rounds=self.expansion_rounds,
            frontier_width=self.expansion_width,
            expand_node_id=node_id,
        )
        data.setdefault("meta", {})["title"] = self.title
        data["meta"]["author"] = self.author
        # Keep the original anchor for validation and cumulative merging, but
        # render the latest clicked node as the temporary center of the map.
        data["meta"]["view_anchor_id"] = node_id
        data["meta"]["last_expansion"] = {
            "node_id": node_id,
            "node_label": selected["label"],
            "added_nodes": max(0, len(data["nodes"]) - before_nodes),
            "added_edges": max(0, len(data["edges"]) - before_edges),
        }
        assert_valid(data)
        self.checkpoint.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        render(data, self.html)
        return {
            "status": data["status"], "node_id": node_id,
            "node_label": selected["label"],
            "nodes": len(data["nodes"]), "edges": len(data["edges"]),
            "added_nodes": max(0, len(data["nodes"]) - before_nodes),
            "added_edges": max(0, len(data["edges"]) - before_edges),
        }


def make_handler(app: ExpansionApp):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlparse(self.path).path
            if path in {"/", "/index.html"}:
                self._send(200, app.page(), "text/html; charset=utf-8")
            elif path == "/app-runtime.js":
                self._send(200, RUNTIME_JS.encode("utf-8"), "text/javascript; charset=utf-8")
            else:
                self._send(404, b"not found", "text/plain; charset=utf-8")

        def do_POST(self):
            if urlparse(self.path).path != "/api/expand":
                self._send(404, b'{"error":"not found"}', "application/json")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 4096:
                    raise ValueError("잘못된 요청 크기입니다")
                payload = json.loads(self.rfile.read(length))
                node_id = payload.get("node_id")
                if not isinstance(node_id, str) or not node_id:
                    raise ValueError("node_id가 필요합니다")
                if not app.lock.acquire(blocking=False):
                    self._send(409, json.dumps({"error":"다른 노드를 조사 중입니다"}, ensure_ascii=False).encode(), "application/json; charset=utf-8")
                    return
                try:
                    result = app.expand(node_id)
                finally:
                    app.lock.release()
                self._send(200, json.dumps(result, ensure_ascii=False).encode(), "application/json; charset=utf-8")
            except Exception as exc:
                body = json.dumps({"error":f"{type(exc).__name__}: {str(exc)[-800:]}"}, ensure_ascii=False).encode()
                self._send(500, body, "application/json; charset=utf-8")

        def log_message(self, format, *args):
            return

    return Handler


def main(argv=None):
    parser = argparse.ArgumentParser(description="클릭 확장을 지원하는 로컬 사상의 그물망")
    parser.add_argument("--checkpoint", type=Path, default=Path("artifacts/crime-and-punishment.json"))
    parser.add_argument("--html", type=Path, default=Path("artifacts/crime-and-punishment.html"))
    parser.add_argument("--title")
    parser.add_argument("--author")
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--expansion-rounds", type=int, default=3,
                        help="선택 노드에서 이어서 조사할 재귀 라운드 수")
    parser.add_argument("--expansion-width", type=int, default=2,
                        help="추가 라운드마다 조사할 새 노드 수")
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args(argv)
    root = Path.cwd().resolve()
    checkpoint = (root / args.checkpoint).resolve()
    html = (root / args.html).resolve()
    if root not in checkpoint.parents or root not in html.parents:
        parser.error("checkpoint and html must be inside the working directory")
    if not checkpoint.is_file():
        parser.error(f"checkpoint not found: {checkpoint}")
    meta = json.loads(checkpoint.read_text(encoding="utf-8")).get("meta", {})
    app = ExpansionApp(root, checkpoint, html, args.title or meta.get("title", "책"),
                       args.author or meta.get("author", "저자"), max(1, args.timeout),
                       max(1, args.expansion_rounds), max(1, args.expansion_width))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(app))
    url = f"http://127.0.0.1:{args.port}/"
    print(f"사상의 그물망 확장 모드: {url}")
    print("종료하려면 이 터미널에서 Control+C")
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
