from __future__ import annotations
import argparse,json,random,re,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).parents[1]; ART=ROOT/"artifacts"; ART.mkdir(exist_ok=True)
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
def execute(command): return subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
def main(argv=None):
 p=argparse.ArgumentParser(); p.add_argument("--url-timeout",type=int,default=12); p.add_argument("--human-reviews",type=Path,default=None,help="optional JSON produced by an identified human reviewer"); p.add_argument("--live",action="store_true"); p.add_argument("--rounds",type=int,default=3); a=p.parse_args(argv)
 cli_command=[sys.executable,"-m","src.cli","--title","죄와 벌","--author","표도르 도스토옙스키","--output","artifacts/crime-and-punishment.html","--seed","1866","--rounds",str(a.rounds)]
 if not a.live: cli_command.append("--fixture")
 cli=execute(cli_command)
 tests=execute([sys.executable,"-m","unittest","discover","-s","tests","-v"])
 data=json.loads((ART/"crime-and-punishment.json").read_text()); status=json.loads((ART/"crime-and-punishment-status.json").read_text())
 from src.source_validator import check_url
 urls=sorted({s["url"] for e in data["edges"] for s in e["sources"]}); url_checks=[check_url(u,a.url_timeout) for u in urls]
 sample=random.Random(1866).sample(data["edges"],min(10,len(data["edges"]))); reviews={}
 if a.human_reviews and a.human_reviews.exists():
  raw=json.loads(a.human_reviews.read_text()); reviews={x["edge_id"]:x for x in raw.get("reviews",[])}
 sampled=[]
 for edge in sample:
  review=reviews.get(edge["id"]); valid=bool(review and review.get("review_type")=="human" and review.get("verdict") in {"supports","does_not_support"} and review.get("reviewer") and review.get("reviewed_at") and review.get("source_url") in {s["url"] for s in edge["sources"]} and review.get("evidence_locator") and review.get("source_excerpt") and review.get("source_excerpt")!=edge["evidence_summary"])
  sampled.append({"edge_id":edge["id"],"human_reviewed":valid,"verdict":review.get("verdict") if valid else "pending","review":review if valid else None})
 complete=len(sampled)==10 and all(x["human_reviewed"] for x in sampled)
 audit={"seed":1866,"checked_at":datetime.now(timezone.utc).isoformat(),"url_check_method":"actual HEAD followed by GET on failure","url_checks":url_checks,"all_urls_success":bool(url_checks) and all(x["ok"] for x in url_checks),"sampled_edges":sampled,"human_support_count":sum(x["verdict"]=="supports" for x in sampled),"human_review_complete":complete,"human_review_status":"complete" if complete else "not_performed_or_incomplete"}
 (ART/"crime-and-punishment-audit.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2))
 secret=re.compile(rb"(?i)(sk-[a-z0-9_-]{16,}|bearer\s+[a-z0-9._-]{16,}|(?:api[_-]?key|session[_-]?token|cookie)\s*[:=]\s*[a-z0-9._-]{16,})")
 scan=[x for x in ROOT.rglob("*") if x.is_file() and not any(part in {".git",".venv","__pycache__"} for part in x.parts)]; secret_hits=[str(x.relative_to(ROOT)) for x in scan if secret.search(x.read_bytes())]
 n=data["nodes"]; paid=status.get("execution",{}); checks={"cli_exit_zero":cli.returncode==0,"tests_exit_zero":tests.returncode==0,"generated_files":all((ART/x).is_file() for x in ("crime-and-punishment.html","crime-and-punishment.json","crime-and-punishment-status.json")),"node_minimum":len(n)>=20,"prior_minimum":sum(x["side"]=="prior" for x in n)>=12,"later_minimum":sum(x["side"]=="later" for x in n)>=5,"ancient_minimum":sum(x["kind"] in ("scripture","thinker") and ("기원전" in x["era"] or x["kind"]=="scripture") for x in n)>=3,"orphan_zero":all(any(e["source"]==x["id"] or e["target"]==x["id"] for e in data["edges"]) for x in n if x["side"]!="anchor"),"limits":len(n)<=50 and len(data["edges"])<=80,"timeout_not_over_2400":data.get("meta",{}).get("execution",{}).get("elapsed_seconds",2401)<=2400,"secret_scan_zero":not secret_hits,"url_success_100_percent":audit["all_urls_success"],"paid_api_calls_zero_from_adapter_log":paid.get("verified_no_paid_path") is True and paid.get("paid_api_calls")==0}
 if a.human_reviews:
  checks["human_sample_10_of_10"]=audit["human_review_complete"] and audit["human_support_count"]==10
 report={"success":all(checks.values()),"checked_at":datetime.now(timezone.utc).isoformat(),"commands":{"cli":{"exit_code":cli.returncode,"stdout":cli.stdout[-2000:],"stderr":cli.stderr[-2000:]},"tests":{"exit_code":tests.returncode,"stdout":tests.stdout[-4000:],"stderr":tests.stderr[-4000:]}},"checks":checks,"counts":{"nodes":len(n),"edges":len(data["edges"]),"unique_urls":len(urls)},"limitations":{"human_claim_verification":audit["human_review_status"],"note":"Structural and source-policy checks do not prove that every literary influence claim is factually correct."}}
 (ART/"acceptance-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)); print(json.dumps(report,ensure_ascii=False)); return 0 if report["success"] else 1
if __name__=="__main__": raise SystemExit(main())
