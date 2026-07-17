import json,re,unittest,tempfile
from pathlib import Path
from src.html_renderer import render
from src.representative_data import crime_and_punishment

class HtmlTests(unittest.TestCase):
 def test_html_is_single_file_and_interactive(self):
    out=Path(tempfile.mkdtemp())/"atlas.html"; render(crime_and_punishment(),out); s=out.read_text()
    assert "id=\"svg\"" in s and "id=\"viewport\"" in s
    assert "function highlightNode" in s and "function fit" in s
    assert "marker-end" in s and "critical_response" in s
    assert "인물 · 사상가" in s and "문헌 · 작품 · 경전" in s and "사조 · 개념" in s
    assert "laneOf" in s and "relativeSide" in s and "view_anchor_id" in s
    assert "window.atlasUI" in s and "function centerNode" in s
    assert "classList.add('selected')" in s and "aria-selected" in s
    assert "closest('.node,.edge')" in s
    assert not re.search(r"<(?:script|link)[^>]+(?:src|href)=[\"']https?://",s,re.I)
    assert "fetch(" not in s and "XMLHttpRequest" not in s
    payload=re.search(r'<script id="atlas-data" type="application/json">(.*?)</script>',s,re.S).group(1)
    assert len(json.loads(payload)["nodes"])>=20
    assert "static-demo-notice" not in s  # 오프라인 산출물에는 데모 전용 문구가 없어야 한다

 def test_pages_demo_publish_injects_local_only_notice(self):
    import subprocess,sys
    tmp=Path(tempfile.mkdtemp()); checkpoint=tmp/"demo.json"; out=tmp/"index.html"
    checkpoint.write_text(json.dumps(crime_and_punishment(),ensure_ascii=False),encoding="utf-8")
    proc=subprocess.run([sys.executable,"thought_lineage_svg_renderer.py",str(checkpoint),str(out)],cwd=Path.cwd(),capture_output=True,text=True)
    self.assertEqual(proc.returncode,0,proc.stderr)
    s=out.read_text(encoding="utf-8")
    self.assertIn("static-demo-notice",s)
    self.assertIn("로컬 서버 모드",s)
    plain=subprocess.run([sys.executable,"thought_lineage_svg_renderer.py",str(checkpoint),str(out),"--no-demo-note"],cwd=Path.cwd(),capture_output=True,text=True)
    self.assertEqual(plain.returncode,0,plain.stderr)
    self.assertNotIn("static-demo-notice",out.read_text(encoding="utf-8"))
