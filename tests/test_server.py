import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.representative_data import crime_and_punishment
from src.server import ExpansionApp, RUNTIME_JS


class ServerTests(unittest.TestCase):
    def test_local_mode_injects_runtime_without_polluting_offline_html(self):
        root = Path(tempfile.mkdtemp(dir=Path.cwd()))
        checkpoint = root / "atlas.json"
        html = root / "atlas.html"
        checkpoint.write_text(json.dumps(crime_and_punishment(), ensure_ascii=False), encoding="utf-8")
        app = ExpansionApp(root, checkpoint, html, "죄와 벌", "표도르 도스토옙스키", 60)
        served = app.page().decode("utf-8")
        offline = html.read_text(encoding="utf-8")
        self.assertIn('/app-runtime.js', served)
        self.assertNotIn('/app-runtime.js', offline)
        self.assertNotIn('fetch(', offline)
        self.assertIn("fetch('/api/expand'", RUNTIME_JS)
        self.assertIn("다시 분석·확장", RUNTIME_JS)
        self.assertIn("sessionStorage", RUNTIME_JS)
        self.assertIn("result.added_nodes === 0", RUNTIME_JS)

    def test_expansion_persists_clicked_node_as_view_anchor(self):
        root = Path(tempfile.mkdtemp(dir=Path.cwd()))
        checkpoint = root / "atlas.json"
        html = root / "atlas.html"
        data = crime_and_punishment()
        checkpoint.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        app = ExpansionApp(root, checkpoint, html, "죄와 벌", "표도르 도스토옙스키", 60)
        with patch("src.server.run", return_value=data):
            result = app.expand("nietzsche")
        saved = json.loads(checkpoint.read_text(encoding="utf-8"))
        self.assertEqual(saved["meta"]["anchor_id"], data["meta"]["anchor_id"])
        self.assertEqual(saved["meta"]["view_anchor_id"], "nietzsche")
        expected = next(node["label"] for node in data["nodes"] if node["id"] == "nietzsche")
        self.assertEqual(result["node_label"], expected)
        self.assertIn('"view_anchor_id": "nietzsche"', html.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
