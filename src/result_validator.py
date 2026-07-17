from __future__ import annotations
import json, re
from pathlib import Path
from .source_validator import allowed, classify, publisher_key
from .graph_builder import MAX_ATLAS_NODES, MAX_ATLAS_EDGES

SECRET=re.compile(r"(?i)(sk-[a-z0-9_-]{16,}|bearer\s+[a-z0-9._-]{16,}|api[_-]?key\s*[:=]|session[_-]?token\s*[:=]|cookie\s*[:=])")
INTERPRETIVE={"thematic","ideological","critical_response","movement"}
def validate(data, schema_path=None):
    schema_path=schema_path or Path(__file__).parents[1]/"schema/research-result.schema.json"
    schema=json.loads(Path(schema_path).read_text())
    errors=[]
    if not isinstance(data,dict): return ["result must be an object"]
    for key in schema["required"]:
        if key not in data: errors.append(f"missing required field: {key}")
    if data.get("status") not in ("complete","timed_out","partial"): errors.append("invalid status")
    if len(data.get("nodes",[]))>MAX_ATLAS_NODES: errors.append(f"more than {MAX_ATLAS_NODES} nodes")
    if len(data.get("edges",[]))>MAX_ATLAS_EDGES: errors.append(f"more than {MAX_ATLAS_EDGES} edges")
    node_req=("id","label","kind","era","side","summary")
    edge_req=("id","source","target","direction","relation_type","explanation","evidence_summary","material_title","source_url","confidence","importance","sources")
    for i,n in enumerate(data.get("nodes",[])):
        for k in node_req:
            if k not in n: errors.append(f"node {i}: missing {k}")
    for i,e in enumerate(data.get("edges",[])):
        for k in edge_req:
            if k not in e: errors.append(f"edge {i}: missing {k}")
        if e.get("direction")!="source_to_target": errors.append(f"edge {i}: invalid direction")
        if e.get("confidence") not in ("A","B","C"): errors.append(f"edge {i}: invalid confidence")
        if not isinstance(e.get("importance"),int) or not 0<=e.get("importance",-1)<=100: errors.append(f"edge {i}: invalid importance")
    ids=[n["id"] for n in data.get("nodes",[])]; idset=set(ids)
    if len(ids)!=len(idset): errors.append("duplicate node id")
    anchor=data.get("meta",{}).get("anchor_id")
    degree={i:0 for i in ids}
    for e in data.get("edges",[]):
        if e.get("source") not in idset or e.get("target") not in idset: errors.append(f"{e.get('id')}: dangling endpoint")
        for x in (e.get("source"),e.get("target")):
            if x in degree: degree[x]+=1
        sources=e.get("sources",[])
        if not all(allowed(s.get("url","")) for s in sources): errors.append(f"{e.get('id')}: prohibited or unclassified source")
        for s in sources:
            policy=classify(s.get("url",""))
            if policy.get("allowed") and s.get("grade") < policy.get("maximum_grade","C"):
                errors.append(f"{e.get('id')}: source grade exceeds domain policy")
        strong=[s for s in sources if s.get("grade") in ("A","B")]
        if not strong: errors.append(f"{e.get('id')}: no A/B source")
        if e.get("relation_type") in INTERPRETIVE and len({publisher_key(s) for s in strong})<2: errors.append(f"{e.get('id')}: needs two independent A/B publishers")
    orphan=[i for i,d in degree.items() if i!=anchor and d==0]
    if orphan: errors.append("orphan nodes: "+", ".join(orphan))
    adjacency={i:set() for i in ids}
    for e in data.get("edges",[]):
        if e.get("source") in adjacency and e.get("target") in adjacency:
            adjacency[e["source"]].add(e["target"]); adjacency[e["target"]].add(e["source"])
    reachable=set(); frontier=[anchor] if anchor in adjacency else []
    while frontier:
        node_id=frontier.pop()
        if node_id in reachable: continue
        reachable.add(node_id); frontier.extend(adjacency[node_id]-reachable)
    disconnected=idset-reachable
    if disconnected: errors.append("nodes disconnected from anchor: "+", ".join(sorted(disconnected)))
    if SECRET.search(json.dumps(data)): errors.append("possible secret detected")
    return errors

def assert_valid(data, schema_path=None):
    errors=validate(data,schema_path)
    if errors: raise ValueError("invalid result:\n- " + "\n- ".join(errors))
