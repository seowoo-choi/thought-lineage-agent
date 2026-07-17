import copy, unittest, random, subprocess, sys, json
from src.representative_data import crime_and_punishment
from src.result_validator import validate
from src.graph_builder import build, MAX_ATLAS_NODES, MAX_ATLAS_EDGES
from src.source_validator import allowed, classify
from src.research_engine import run
from src.query_planner import build_prompt, select_frontier
from pathlib import Path
import tempfile
from unittest.mock import patch

class PipelineTests(unittest.TestCase):
 def test_representative_valid_and_minimums(self):
    d=crime_and_punishment(); assert validate(d)==[]
    self.assertTrue(len(d["nodes"])>=20 and sum(n["side"]=="prior" for n in d["nodes"])>=12)
    self.assertGreaterEqual(sum(n["side"]=="later" for n in d["nodes"]),5)
    self.assertGreaterEqual(sum(n["kind"] in ("scripture","thinker") and ("기원전" in n["era"] or n["kind"]=="scripture") for n in d["nodes"]),3)
 def test_orphan_and_independent_sources_and_blocklist(self):
    d=crime_and_punishment(); d["nodes"].append({"id":"x","label":"x","kind":"book","era":"x","side":"prior","summary":"x"})
    assert any("orphan" in e for e in validate(d))
    d=crime_and_punishment(); d["edges"][0]["sources"]=d["edges"][0]["sources"][:1]
    assert any("independent" in e for e in validate(d))
    d=crime_and_punishment(); d["edges"][0]["sources"][0]["url"]="https://wikipedia.org/x"
    assert any("prohibited" in e for e in validate(d))
 def test_limits_dedupe_and_secret_detection(self):
    d=crime_and_punishment(); d["meta"]["note"]="api_key="
    assert any("secret" in e for e in validate(d))
    d=crime_and_punishment(); d["edges"] += copy.deepcopy(d["edges"])*5
    self.assertTrue(len(build(d)["edges"])<=MAX_ATLAS_EDGES and len(build(d)["nodes"])<=MAX_ATLAS_NODES)
 def test_graph_builder_property_never_creates_orphans(self):
    for seed in range(100):
      rng=random.Random(seed); count=rng.randint(2,120)
      nodes=[{"id":f"n{i}","label":f"N{i}","kind":"book","era":"x","side":"anchor" if i==0 else rng.choice(["prior","later"]),"summary":"x"} for i in range(count)]
      edges=[]
      for i in range(rng.randint(0,200)):
        s,t=rng.sample(range(count),2)
        edges.append({"id":f"e{i}","source":f"n{s}","target":f"n{t}","direction":"source_to_target","relation_type":"explicit","explanation":"x","evidence_summary":"x","material_title":"x","source_url":"https://www.gutenberg.org/","confidence":rng.choice(["A","B","C"]),"importance":rng.randint(0,100),"sources":[{"url":"https://www.gutenberg.org/","title":"x","publisher":"Project Gutenberg","grade":"A","support":"x"}]})
      result=build({"meta":{"anchor_id":"n0"},"status":"complete","nodes":nodes,"edges":edges})
      ids={n["id"] for n in result["nodes"]}; degree={i:0 for i in ids}
      for edge in result["edges"]:
        self.assertIn(edge["source"],ids); self.assertIn(edge["target"],ids)
        degree[edge["source"]]+=1; degree[edge["target"]]+=1
      self.assertLessEqual(len(ids),MAX_ATLAS_NODES); self.assertLessEqual(len(result["edges"]),MAX_ATLAS_EDGES)
      self.assertFalse([i for i,d in degree.items() if i!="n0" and d==0])
 def test_explicit_allowlist_rejects_unknown_personal_search_and_spoofing(self):
    self.assertTrue(allowed("https://www.gutenberg.org/files/2554/2554-h/2554-h.htm"))
    self.assertTrue(allowed("https://granta.com/the-story-of-a-variation/"))
    self.assertTrue(allowed("https://uplopen.com/reader/chapters/pdf/example"))
    for url,reason in [
      ("https://thoughts.example.net/my-review","unclassified_domain"),
      ("https://medium.com/@reader/review","unclassified_domain"),
      ("https://google.com/search?q=crime+punishment","search_results_page"),
      ("https://gutenberg.org.evil.example/x","unclassified_domain"),
      ("https://britannica.com/x?url=https://personal.example/x","redirect_wrapper")]:
        self.assertFalse(allowed(url),url); self.assertEqual(classify(url)["reason"],reason)
 def test_builder_curates_sources_and_drops_weak_interpretive_edges(self):
    d={"meta":{"anchor_id":"anchor"},"status":"complete","nodes":[
      {"id":"anchor","label":"Anchor","kind":"book","era":"1900","side":"anchor","summary":"x"},
      {"id":"explicit","label":"Explicit","kind":"book","era":"1800","side":"prior","summary":"x"},
      {"id":"weak","label":"Weak","kind":"book","era":"2000","side":"later","summary":"x"}],"edges":[]}
    base={"direction":"source_to_target","explanation":"x","evidence_summary":"x","importance":5,"confidence":"A"}
    d["edges"]=[dict(base,id="keep",source="explicit",target="anchor",relation_type="explicit",material_title="x",source_url="https://www.gutenberg.org/x",sources=[{"url":"https://www.gutenberg.org/x","title":"x","publisher":"Project Gutenberg","grade":"A","support":"x"}]),
      dict(base,id="drop",source="anchor",target="weak",relation_type="thematic",material_title="x",source_url="https://www.cambridge.org/x",sources=[{"url":"https://www.cambridge.org/x","title":"x","publisher":"Cambridge University Press","grade":"A","support":"x"}])]
    result=build(d)
    self.assertEqual([e["id"] for e in result["edges"]],["keep"])
    self.assertNotIn("weak",{n["id"] for n in result["nodes"]})
    self.assertEqual(result["meta"]["curation"]["dropped_edge_ids"],["drop"])
 def test_research_engine_merges_multiple_rounds(self):
    first=crime_and_punishment()
    extra={"meta":dict(first["meta"]),"status":"complete","nodes":[
      {"id":"new_later","label":"New Later","kind":"book","era":"2000","side":"later","summary":"x"}],"edges":[{
      "id":"new_edge","source":first["meta"]["anchor_id"],"target":"new_later","direction":"source_to_target","relation_type":"explicit","explanation":"x","evidence_summary":"x","material_title":"x","source_url":"https://www.gutenberg.org/x","confidence":"A","importance":10,"sources":[{"url":"https://www.gutenberg.org/x","title":"x","publisher":"Project Gutenberg","grade":"A","support":"x"}]}]}
    out=Path(tempfile.mkdtemp())/"recursive.json"
    with patch("src.research_engine.research",side_effect=[first,extra]):
      result=run("죄와 벌","표도르 도스토옙스키",1866,30,Path.cwd(),out,rounds=2,reserve_seconds=0,frontier_width=1)
    self.assertIn("new_later",{n["id"] for n in result["nodes"]})
    self.assertEqual(result["meta"]["execution"]["rounds_completed"],2)
 def test_focus_prompt_treats_candidate_as_unproven_critical_response(self):
    existing=crime_and_punishment()
    prompt=build_prompt("죄와 벌","표도르 도스토옙스키",1866,existing,0,["Milan Kundera"])
    self.assertIn("Milan Kundera",prompt)
    self.assertIn("candidates, not presumed facts",prompt)
    self.assertIn("critical_response",prompt)
    self.assertIn("ANY existing node",prompt)
    self.assertIn("intermediary→that author",prompt)
 def test_arbitrary_anchor_prompt_has_no_crime_and_punishment_requirement(self):
    prompt=build_prompt("The Left Hand of Darkness","Ursula K. Le Guin",42)
    self.assertNotIn("Crime and Punishment representative case",prompt)
    self.assertIn("do not force fixed counts",prompt)
    self.assertIn("representative fixture",prompt)
 def test_recursive_frontier_automatically_includes_later_leaf_nietzsche(self):
    existing=crime_and_punishment()
    frontier=select_frontier(existing)
    by_id={item["id"]:item for item in frontier}
    self.assertIn("nietzsche",by_id)
    self.assertEqual(by_id["nietzsche"]["direction"],"later")
    prompt=build_prompt("죄와 벌","표도르 도스토옙스키",1866,existing,1)
    self.assertIn('"id":"nietzsche"',prompt)
    self.assertIn("dedicated expansion call",prompt)
    one=build_prompt("죄와 벌","표도르 도스토옙스키",1866,existing,1,frontier_override=[by_id["nietzsche"]])
    self.assertIn('"id":"nietzsche"',one)
    self.assertNotIn('"id":"freud"',one.split("The algorithm selected",1)[1].split("This is a dedicated",1)[0])
 def test_nietzsche_remains_expansion_candidate_after_foucault_child_exists(self):
    existing=crime_and_punishment()
    existing["nodes"].append({"id":"foucault_test","label":"Michel Foucault","kind":"thinker","era":"1926–1984","side":"later","summary":"x"})
    existing["edges"].append({"id":"nf","source":"nietzsche","target":"foucault_test","direction":"source_to_target","relation_type":"explicit","explanation":"x","evidence_summary":"x","material_title":"x","source_url":"https://www.cambridge.org/x","confidence":"A","importance":10,"sources":[{"url":"https://www.cambridge.org/x","title":"x","publisher":"Cambridge University Press","grade":"A","support":"x"}]})
    self.assertIn("nietzsche",{item["id"] for item in select_frontier(existing,50)})
 def test_engine_makes_one_dedicated_call_per_selected_frontier(self):
    prompts=[]
    def fake_research(prompt,*args,**kwargs):
      prompts.append(prompt); return crime_and_punishment()
    out=Path(tempfile.mkdtemp())/"frontier.json"
    with patch("src.research_engine.research",side_effect=fake_research):
      result=run("죄와 벌","표도르 도스토옙스키",1866,30,Path.cwd(),out,initial=crime_and_punishment(),rounds=1,frontier_width=2,reserve_seconds=0)
    self.assertEqual(len(prompts),2)
    selected=[p.split("The algorithm selected",1)[1].split("This is a dedicated",1)[0] for p in prompts]
    self.assertTrue(all(chunk.count('"id"')==1 for chunk in selected))
    self.assertIn('"id":"nietzsche"',selected[0])
    self.assertEqual(len(result["meta"]["frontier_attempts"]),2)
 def test_click_style_expansion_forces_selected_existing_node(self):
    prompts=[]
    def fake_research(prompt,*args,**kwargs):
      prompts.append(prompt); return crime_and_punishment()
    existing=crime_and_punishment()
    existing.setdefault("meta",{})["frontier_attempts"]=[{"node_id":"nietzsche","status":"expanded"}]
    out=Path(tempfile.mkdtemp())/"clicked.json"
    with patch("src.research_engine.research",side_effect=fake_research):
      run("죄와 벌","표도르 도스토옙스키",1866,30,Path.cwd(),out,initial=existing,rounds=1,frontier_width=1,reserve_seconds=0,expand_node_id="nietzsche")
    self.assertEqual(len(prompts),2)
    selected=[p.split("The algorithm selected",1)[1].split("This is a dedicated",1)[0] for p in prompts]
    self.assertTrue(all('"id":"nietzsche"' in chunk for chunk in selected))
    self.assertTrue(all('"id":"freud"' not in chunk for chunk in selected))
    self.assertIn('"direction":"prior"',selected[0])
    self.assertIn('"direction":"later"',selected[1])
 def test_click_expansion_recurses_into_new_nodes_only(self):
    prompts=[]; existing=crime_and_punishment(); anchor=existing["meta"]["anchor_id"]
    def addition(node_id,label,source,target):
      return {"meta":dict(existing["meta"]),"status":"complete","nodes":[
        {"id":node_id,"label":label,"kind":"book","era":"2000","side":"later","summary":"x"}],"edges":[{
        "id":"edge_"+node_id,"source":source,"target":target,"direction":"source_to_target","relation_type":"explicit","explanation":"x","evidence_summary":"x","material_title":"x","source_url":"https://www.gutenberg.org/x","confidence":"A","importance":8,"sources":[{"url":"https://www.gutenberg.org/x","title":"x","publisher":"Project Gutenberg","grade":"A","support":"x"}]}]}
    responses=[addition("new_prior","New Prior","new_prior","nietzsche"),addition("new_later","New Later","nietzsche","new_later")]
    def fake_research(prompt,*args,**kwargs):
      prompts.append(prompt)
      return responses.pop(0) if responses else {"meta":dict(existing["meta"]),"status":"complete","nodes":[],"edges":[]}
    out=Path(tempfile.mkdtemp())/"clicked-recursive.json"
    with patch("src.research_engine.research",side_effect=fake_research):
      result=run("죄와 벌","표도르 도스토옙스키",1866,30,Path.cwd(),out,initial=existing,rounds=2,frontier_width=2,reserve_seconds=0,expand_node_id="nietzsche")
    self.assertEqual(len(prompts),4)
    recursive="\n".join(prompts[2:])
    self.assertIn('"id":"new_later"',recursive)
    self.assertIn('"id":"new_prior"',recursive)
    self.assertNotIn('"id":"freud"',recursive.split("The algorithm selected",1)[1].split("This is a dedicated",1)[0])
    self.assertIn("new_later",{node["id"] for node in result["nodes"]})
 def test_builder_removes_disconnected_non_orphan_island(self):
    d=crime_and_punishment()
    d["nodes"] += [
      {"id":"island_a","label":"Island A","kind":"book","era":"2000","side":"later","summary":"x"},
      {"id":"island_b","label":"Island B","kind":"book","era":"2001","side":"later","summary":"x"}]
    d["edges"].append({"id":"island_edge","source":"island_a","target":"island_b","direction":"source_to_target","relation_type":"explicit","explanation":"x","evidence_summary":"x","material_title":"x","source_url":"https://www.gutenberg.org/x","confidence":"A","importance":100,"sources":[{"url":"https://www.gutenberg.org/x","title":"x","publisher":"Project Gutenberg","grade":"A","support":"x"}]})
    result=build(d)
    ids={n["id"] for n in result["nodes"]}
    self.assertNotIn("island_a",ids); self.assertNotIn("island_b",ids)
 def test_all_research_failures_save_valid_partial_checkpoint(self):
    out=Path(tempfile.mkdtemp())/"partial.json"
    with patch("src.research_engine.research",side_effect=ValueError("bad JSON")):
      d=run("임의 책","저자",1,2,Path.cwd(),out)
    self.assertEqual(d["status"],"partial"); self.assertTrue(out.exists()); self.assertEqual(validate(d),[])
    self.assertEqual(d["meta"]["execution"]["calls"],[])
 def test_readme_cli_output_directory_and_zero_timeout(self):
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
      rel=Path(tmp).relative_to(Path.cwd())
      command=[sys.executable,"-m","src.cli","--title","죄와 벌","--author","표도르 도스토옙스키","--output-dir",str(rel),"--output","atlas.html","--seed","1866","--fixture"]
      proc=subprocess.run(command,cwd=Path.cwd(),capture_output=True,text=True)
      self.assertEqual(proc.returncode,0,proc.stderr); self.assertTrue((Path(tmp)/"atlas.html").exists())
      timed=subprocess.run([sys.executable,"-m","src.cli","--title","임의 책","--author","저자","--output-dir",str(rel),"--output","timeout.html","--timeout","0"],cwd=Path.cwd(),capture_output=True,text=True)
      self.assertEqual(timed.returncode,0,timed.stderr)
      self.assertEqual(json.loads((Path(tmp)/"timeout.json").read_text())["status"],"timed_out")
 def test_cli_resume_cleans_legacy_disconnected_island_before_validation(self):
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
      rel=Path(tmp).relative_to(Path.cwd()); source=Path(tmp)/"legacy.json"
      d=crime_and_punishment(); d["nodes"] += [
        {"id":"old_island_a","label":"Old A","kind":"book","era":"2000","side":"later","summary":"x"},
        {"id":"old_island_b","label":"Old B","kind":"book","era":"2001","side":"later","summary":"x"}]
      d["edges"].append({"id":"old_island_edge","source":"old_island_a","target":"old_island_b","direction":"source_to_target","relation_type":"explicit","explanation":"x","evidence_summary":"x","material_title":"x","source_url":"https://www.gutenberg.org/x","confidence":"A","importance":100,"sources":[{"url":"https://www.gutenberg.org/x","title":"x","publisher":"Project Gutenberg","grade":"A","support":"x"}]})
      source.write_text(json.dumps(d,ensure_ascii=False),encoding="utf-8")
      proc=subprocess.run([sys.executable,"-m","src.cli","--title","죄와 벌","--author","표도르 도스토옙스키","--output-dir",str(rel),"--output","cleaned.html","--resume",str(source),"--timeout","0"],cwd=Path.cwd(),capture_output=True,text=True)
      self.assertEqual(proc.returncode,0,proc.stderr)
      cleaned=json.loads((Path(tmp)/"cleaned.json").read_text())
      self.assertEqual(cleaned["meta"]["resume_cleanup"]["removed_node_ids"],["old_island_a","old_island_b"])
