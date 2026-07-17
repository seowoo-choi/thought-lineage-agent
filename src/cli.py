from __future__ import annotations
import argparse, json, os, time
from pathlib import Path
from .html_renderer import render
from .graph_builder import build
from .representative_data import crime_and_punishment
from .research_engine import run
from .result_validator import assert_valid

def main(argv=None):
    started=time.monotonic()
    p=argparse.ArgumentParser(description="오프라인 문학 영향 지도 생성")
    p.add_argument("--title",required=True); p.add_argument("--author",required=True); p.add_argument("--output",required=True,type=Path)
    p.add_argument("--output-dir",type=Path,default=None,help="relative outputs are resolved below this workspace directory")
    p.add_argument("--seed",type=int,default=1866); p.add_argument("--timeout",type=int,default=2400)
    p.add_argument("--rounds",type=int,default=3,help="recursive live-research rounds")
    p.add_argument("--frontier-width",type=int,default=4,help="dedicated frontier-node calls per recursive round")
    p.add_argument("--resume",type=Path,help="merge new research into an existing checkpoint JSON")
    p.add_argument("--focus",action="append",default=[],help="candidate author/work/movement to investigate; repeatable")
    p.add_argument("--expand-node",help="re-investigate one existing node regardless of previous edges or attempts")
    p.add_argument("--fixture",action="store_true",help="use deterministic demo data instead of live research")
    p.add_argument("--live",action="store_true",help="deprecated compatibility flag; live research is now the default")
    a=p.parse_args(argv); root=Path.cwd().resolve(); base=a.output_dir or (Path(os.environ["BOOK_ATLAS_OUTPUT_DIR"]) if "BOOK_ATLAS_OUTPUT_DIR" in os.environ else root)
    base=(root/base).resolve() if not base.is_absolute() else base.resolve()
    out=(base/a.output).resolve() if not a.output.is_absolute() else a.output.resolve()
    if root not in out.parents: p.error("output must be inside working directory")
    out.parent.mkdir(parents=True,exist_ok=True); checkpoint=out.with_suffix(".json")
    deadline=started+max(0,a.timeout)
    fixture=crime_and_punishment if a.fixture else None
    initial=None
    if a.resume:
        resume=(root/a.resume).resolve() if not a.resume.is_absolute() else a.resume.resolve()
        if root not in resume.parents or not resume.is_file(): p.error("resume must be an existing JSON file inside working directory")
        initial=json.loads(resume.read_text(encoding="utf-8"))
        before_ids={node.get("id") for node in initial.get("nodes",[])}
        initial=build(initial)
        after_ids={node.get("id") for node in initial.get("nodes",[])}
        initial.setdefault("meta",{})["resume_cleanup"]={
            "removed_node_ids":sorted(before_ids-after_ids),
            "reason":"pruned invalid, unsupported, orphaned, or anchor-disconnected legacy nodes before resume",
        }
        assert_valid(initial)
    data=run(a.title,a.author,a.seed,a.timeout,root,checkpoint,fixture,deadline=deadline,rounds=a.rounds,initial=initial,focus=a.focus,frontier_width=max(1,a.frontier_width),expand_node_id=a.expand_node)
    data.setdefault("meta",{})["title"]=a.title
    data["meta"]["author"]=a.author
    assert_valid(data); render(data,out)
    calls=data.get("meta",{}).get("execution",{}).get("calls",[])
    paid=[c for c in calls if c.get("paid_api") is True]
    status={"status":data["status"],"html":str(out.relative_to(root)),"checkpoint":str(checkpoint.relative_to(root)),"nodes":len(data["nodes"]),"edges":len(data["edges"]),
            "execution":{"adapter_calls":calls,"paid_api_calls":len(paid),"paid_api_cost":sum(float(c.get("cost",0)) for c in paid),
                         "verified_no_paid_path":bool(calls) and all(c.get("paid_api") is False for c in calls)}}
    out.with_name(out.stem+"-status.json").write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(status,ensure_ascii=False)); return 0
if __name__=="__main__": raise SystemExit(main())
