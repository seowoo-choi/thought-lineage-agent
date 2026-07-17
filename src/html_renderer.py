from __future__ import annotations

import json
from pathlib import Path

from thought_lineage_svg_renderer import HTML


def render(data: dict, output: Path) -> None:
    """Render a zoomable, layered SVG graph as one offline HTML file."""
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(HTML.replace("__DATA__", payload), encoding="utf-8")
