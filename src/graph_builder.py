from .source_validator import classify, publisher_key


GRADE={"A":0,"B":1,"C":2}
INTERPRETIVE={"thematic","ideological","critical_response","movement"}
MAX_ATLAS_NODES=200
MAX_ATLAS_EDGES=320


def _curate_edge(edge):
    """Return a policy-compliant copy or None when evidence is insufficient."""
    sources=[]
    for source in edge.get("sources",[]):
        policy=classify(source.get("url",""))
        if not policy.get("allowed"):
            continue
        source=dict(source)
        maximum=policy.get("maximum_grade","C")
        current=source.get("grade","C")
        if GRADE.get(current,2)<GRADE.get(maximum,2):
            source["grade"]=maximum
        sources.append(source)
    strong=[s for s in sources if s.get("grade") in ("A","B")]
    if not strong:
        return None
    if edge.get("relation_type") in INTERPRETIVE and len({publisher_key(s) for s in strong})<2:
        return None
    edge=dict(edge); edge["sources"]=sources
    edge["source_url"]=sources[0]["url"]
    edge["material_title"]=sources[0]["title"]
    return edge


def build(data):
    anchor=data["meta"]["anchor_id"]
    dropped=[]; curated=[]
    for edge in data.get("edges",[]):
        clean=_curate_edge(edge)
        if clean is None: dropped.append(edge.get("id","unknown"))
        else: curated.append(clean)
    data.setdefault("meta",{}).setdefault("curation",{})["dropped_edge_ids"]=dropped
    unique={}
    for e in curated:
        key=(e["source"],e["target"],e["relation_type"])
        if key not in unique: unique[key]=e
        else:
            seen={s["url"] for s in unique[key]["sources"]}
            unique[key]["sources"] += [s for s in e["sources"] if s["url"] not in seen]
    edges=sorted(unique.values(),key=lambda e:(GRADE[e["confidence"]],-e["importance"],e["source"],e["target"],e["id"]))[:MAX_ATLAS_EDGES]
    by_id={n["id"]:n for n in data.get("nodes",[])}
    # Select endpoints through the best edges, rather than truncating nodes and
    # accidentally retaining an endpoint whose only edge was then discarded.
    selected={anchor} if anchor in by_id else set()
    kept=[]
    for edge in edges:
        endpoints={edge["source"],edge["target"]}
        if not endpoints <= by_id.keys():
            continue
        if len(selected | endpoints) <= MAX_ATLAS_NODES:
            selected |= endpoints
            kept.append(edge)
    edges=kept
    degree={node_id:0 for node_id in selected}
    for edge in edges:
        degree[edge["source"]]+=1; degree[edge["target"]]+=1
    selected={node_id for node_id,count in degree.items() if node_id==anchor or count>0}
    # The product is one lineage network anchored on the input book. A small
    # internally connected island is still irrelevant if no path reaches the
    # anchor, so retain only the anchor's undirected connected component.
    adjacency={node_id:set() for node_id in selected}
    for edge in edges:
        if edge["source"] in selected and edge["target"] in selected:
            adjacency[edge["source"]].add(edge["target"])
            adjacency[edge["target"]].add(edge["source"])
    reachable=set()
    frontier=[anchor] if anchor in adjacency else []
    while frontier:
        node_id=frontier.pop()
        if node_id in reachable: continue
        reachable.add(node_id)
        frontier.extend(adjacency[node_id]-reachable)
    selected &= reachable
    nodes=sorted((by_id[i] for i in selected),key=lambda n:(n["id"]!=anchor,n["side"],n["id"]))
    edges=[e for e in edges if e["source"] in selected and e["target"] in selected]
    data["nodes"],data["edges"]=nodes,edges
    return data
