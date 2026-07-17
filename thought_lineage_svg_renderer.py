from __future__ import annotations

import argparse
import json
from pathlib import Path


HTML = r'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>사상의 그물망</title>
<style>
:root{--bg:#0d1222;--panel:#11182b;--panel2:#171f36;--line:#59647f;--ink:#f2efe7;--muted:#98a2bc;--prior:#79c8ed;--later:#f2bc68;--anchor:#ff7868;--critical:#d59af0;--direct:#f4d06f}
*{box-sizing:border-box}html,body{height:100%;margin:0}body{background:radial-gradient(circle at 45% -20%,#202b59 0,#0d1222 48%);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;overflow:hidden}
header{height:84px;padding:17px 22px;border-bottom:1px solid #2b3550;display:flex;align-items:center;gap:18px;background:rgba(13,18,34,.88);backdrop-filter:blur(12px)}
.brand{min-width:300px}.brand h1{font-family:Georgia,"Noto Serif KR",serif;font-size:24px;margin:0 0 4px}.brand h1 em{font-style:normal;color:var(--anchor)}.brand p{margin:0;color:var(--muted);font-size:12px}
.controls{display:flex;align-items:center;gap:8px;margin-left:auto}.controls input{width:230px;border:1px solid #394663;background:#151d32;color:var(--ink);padding:9px 11px;border-radius:9px;outline:none}.controls button{border:1px solid #3a4765;background:#172039;color:var(--ink);padding:9px 12px;border-radius:9px;cursor:pointer}.controls button:hover{border-color:#7583a7}
.app{height:calc(100% - 84px);display:grid;grid-template-columns:minmax(0,1fr) 340px}.canvas{position:relative;overflow:hidden}.canvas svg{width:100%;height:100%;display:block;touch-action:none;cursor:grab}.canvas svg.dragging{cursor:grabbing}
.legend{position:absolute;left:18px;bottom:16px;display:flex;gap:14px;flex-wrap:wrap;padding:9px 12px;border:1px solid #303b58;border-radius:10px;background:rgba(15,21,39,.9);font-size:11px;color:var(--muted);pointer-events:none}.legend i{display:inline-block;width:20px;border-top:2px solid;margin-right:5px;vertical-align:3px}.legend .dash{border-top-style:dashed}.legend .crit{border-color:var(--critical)}
.hint{position:absolute;top:14px;left:18px;color:var(--muted);font-size:11px;background:rgba(13,18,34,.78);padding:7px 10px;border-radius:8px;pointer-events:none}
aside{border-left:1px solid #2b3550;background:rgba(16,23,41,.95);padding:22px;overflow:auto}aside h2{font-family:Georgia,"Noto Serif KR",serif;margin:0 0 16px;font-size:20px}aside h3{line-height:1.4;margin:0 0 8px}.eyebrow{color:var(--anchor);font-size:10px;letter-spacing:.14em;text-transform:uppercase;margin-bottom:7px}.summary{color:#d7dbe6;line-height:1.65;font-size:13px}.facts{display:grid;grid-template-columns:80px 1fr;gap:7px 8px;margin:17px 0;font-size:12px}.facts dt{color:var(--muted)}.facts dd{margin:0}.source{border-top:1px solid #2d3752;padding:12px 0;font-size:12px;line-height:1.5}.source a{color:#91d7fa;overflow-wrap:anywhere}.source small{color:var(--muted)}
.empty{color:var(--muted);line-height:1.7;font-size:13px}.badge{display:inline-block;border:1px solid #485470;padding:3px 7px;border-radius:999px;margin:2px 3px 2px 0;color:#cdd3e2;font-size:10px}
.era-line{stroke:#2b3450;stroke-width:1;stroke-dasharray:2 7}.era-label{fill:#77839f;font-size:11px;letter-spacing:.08em}.lane-line{stroke:#35405e;stroke-width:1}.lane-label{fill:#b3bdd3;font-size:11px;font-weight:700;letter-spacing:.12em}.edge{fill:none;stroke:var(--line);stroke-width:1.5;stroke-opacity:.48;transition:.2s;cursor:pointer}.edge.explicit,.edge.citation,.edge.adaptation{stroke:var(--direct);stroke-opacity:.62}.edge.thematic,.edge.ideological,.edge.movement{stroke-dasharray:5 5}.edge.critical_response{stroke:var(--critical);stroke-dasharray:2 5}.edge.active{stroke-opacity:1;stroke-width:3}.edge.faded{stroke-opacity:.055}.node{cursor:pointer;transition:.2s}.node rect{fill:#18223a;stroke:#485675;stroke-width:1.1}.node.author rect,.node.thinker rect{fill:#20243a}.node.book rect,.node.scripture rect{fill:#17263a}.node.movement rect{fill:#28213a;stroke-dasharray:4 3}.node.prior rect{stroke:var(--prior)}.node.later rect{stroke:var(--later)}.node.anchor rect{fill:#39202b;stroke:var(--anchor);stroke-width:2.6;filter:drop-shadow(0 0 10px rgba(255,120,104,.35))}.node text{fill:var(--ink);font-size:12px;pointer-events:none}.node .meta{fill:var(--muted);font-size:9.5px}.node.active rect{stroke:#fff;stroke-width:2.4;filter:drop-shadow(0 0 8px rgba(255,255,255,.28))}.node.faded{opacity:.13}.node.match rect{stroke:#fff;stroke-width:3}.level-pill{fill:#141c31;stroke:#313d59}.level-text{fill:#9da8c0;font-size:10px}
.node.origin-anchor:not(.anchor) rect{stroke:var(--anchor);stroke-width:2;stroke-dasharray:6 3}.node.selected rect{stroke:#fff;stroke-width:3.4;filter:drop-shadow(0 0 11px rgba(255,255,255,.5))}
@media(max-width:900px){header{height:112px;align-items:flex-start;flex-wrap:wrap}.brand{min-width:0}.controls{width:100%;margin:0}.controls input{flex:1}.app{height:calc(100% - 112px);grid-template-columns:1fr}aside{display:none}.legend{right:12px}.brand h1{font-size:20px}}
</style>
</head>
<body>
<header><div class="brand"><h1>사상의 그물망 <em id="anchorTitle"></em></h1><p id="subtitle"></p></div><div class="controls"><input id="search" placeholder="저자·작품·사조 검색"><button id="fit">전체 보기</button><button id="reset">강조 해제</button></div></header>
<main class="app"><section class="canvas"><svg id="svg" role="img" aria-label="시대순 사상 계보 그래프"><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#7d88a2"/></marker></defs><g id="viewport"><g id="eras"></g><g id="edges"></g><g id="nodes"></g></g></svg><div class="hint">휠로 확대·축소 · 빈 곳을 드래그해 이동 · 별을 누르면 앞뒤 계보가 강조됩니다</div><div class="legend"><span><i style="border-color:var(--direct)"></i>직접 인용·명시</span><span><i class="dash"></i>사상적 영향</span><span><i class="crit"></i>비판적 응답</span></div></section><aside><h2>계보 상세</h2><div id="detail" class="empty">별이나 연결선을 선택하면 근거와 출처를 볼 수 있습니다.<br><br>입력한 책은 끝점이 아니라 시간축 위의 중심점입니다.</div></aside></main>
<script id="atlas-data" type="application/json">__DATA__</script>
<script>
const data=JSON.parse(document.getElementById('atlas-data').textContent);
const byId=Object.fromEntries(data.nodes.map(n=>[n.id,n]));
const originalAnchor=data.meta.anchor_id;
const anchor=byId[data.meta.view_anchor_id]?data.meta.view_anchor_id:originalAnchor;
const incoming={}, outgoing={};
for(const n of data.nodes){incoming[n.id]=[];outgoing[n.id]=[]}
for(const e of data.edges){(outgoing[e.source]||=[]).push(e);(incoming[e.target]||=[]).push(e)}
document.getElementById('anchorTitle').textContent=`— ${byId[anchor]?.label||data.meta.title}`;
const focusNote=anchor===originalAnchor?'':`확장 기준 · 최초 입력: ${byId[originalAnchor]?.label||data.meta.title} · `;
document.getElementById('subtitle').textContent=`${focusNote}${data.nodes.length}개의 별 · ${data.edges.length}개의 근거 있는 연결 · 생성형 AI 조사 결과는 원문 확인이 필요합니다`;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function distances(start, adjacency, sign){const d={[start]:0},q=[start];while(q.length){const id=q.shift();for(const e of adjacency[id]||[]){const next=sign<0?e.source:e.target;if(d[next]===undefined){d[next]=d[id]+sign;q.push(next)}}}return d}
const prior=distances(anchor,incoming,-1), later=distances(anchor,outgoing,1), levels={...prior,...later,[anchor]:0};
for(const n of data.nodes)if(levels[n.id]===undefined)levels[n.id]=n.side==='prior'?-1:n.side==='later'?1:0;
const laneOf=n=>n.kind==='author'||n.kind==='thinker'?'people':n.kind==='movement'?'ideas':'texts';
const laneDefs=[['people','인물 · 사상가'],['texts','문헌 · 작품 · 경전'],['ideas','사조 · 개념']];
const grouped={};for(const n of data.nodes)(grouped[levels[n.id]]??=[]).push(n);
const levelKeys=Object.keys(grouped).map(Number).sort((a,b)=>a-b);
const nodeW=190,nodeH=60,gapX=76,gapY=22,marginX=85,marginY=88;
const laneMax={people:1,texts:1,ideas:1};for(const items of Object.values(grouped))for(const [key] of laneDefs)laneMax[key]=Math.max(laneMax[key],items.filter(n=>laneOf(n)===key).length);
const laneHeight={};for(const [key] of laneDefs)laneHeight[key]=Math.max(180,laneMax[key]*(nodeH+gapY)+70);
const laneTop={};let laneCursor=62;for(const [key] of laneDefs){laneTop[key]=laneCursor;laneCursor+=laneHeight[key]}
const worldW=marginX*2+levelKeys.length*(nodeW+gapX)-gapX, worldH=Math.max(760,laneCursor+35);
const levelX={};levelKeys.forEach((l,i)=>levelX[l]=marginX+i*(nodeW+gapX));
const pos={};
for(const level of levelKeys)for(const [lane] of laneDefs){const items=grouped[level].filter(n=>laneOf(n)===lane).sort((a,b)=>String(a.era).localeCompare(String(b.era),'ko')||a.label.localeCompare(b.label,'ko'));const block=items.length*nodeH+Math.max(0,items.length-1)*gapY;const top=laneTop[lane]+48+Math.max(0,(laneHeight[lane]-70-block)/2);items.forEach((n,i)=>pos[n.id]={x:levelX[level],y:top+i*(nodeH+gapY)})}

const NS='http://www.w3.org/2000/svg', svg=document.getElementById('svg'), viewport=document.getElementById('viewport'), eras=document.getElementById('eras'), edgeG=document.getElementById('edges'), nodeG=document.getElementById('nodes');
function el(name,attrs,parent){const x=document.createElementNS(NS,name);for(const[k,v]of Object.entries(attrs||{}))x.setAttribute(k,v);if(parent)parent.appendChild(x);return x}
for(const [key,label] of laneDefs){const y=laneTop[key]+28;el('line',{x1:18,x2:worldW-18,y1:y,y2:y,class:'lane-line'},eras);const t=el('text',{x:24,y:y-9,class:'lane-label'},eras);t.textContent=label}
for(const level of levelKeys){const x=levelX[level]+nodeW/2;el('line',{x1:x,x2:x,y1:48,y2:worldH-35,class:'era-line'},eras);const pill=el('g',{},eras);el('rect',{x:x-50,y:20,width:100,height:24,rx:12,class:'level-pill'},pill);const t=el('text',{x,y:36,'text-anchor':'middle',class:'level-text'},pill);t.textContent=level===0?(anchor===originalAnchor?'입력한 책':'확장 기준'):level<0?`${Math.abs(level)}단계 전`:`${level}단계 후`}
function pathFor(e){const a=pos[e.source],b=pos[e.target],x1=a.x+nodeW,y1=a.y+nodeH/2,x2=b.x,y2=b.y+nodeH/2,dx=Math.max(40,(x2-x1)*.48);return `M${x1},${y1} C${x1+dx},${y1} ${x2-dx},${y2} ${x2},${y2}`}
const edgeEls={};for(const e of data.edges){const p=el('path',{d:pathFor(e),class:`edge ${e.relation_type}`,'marker-end':'url(#arrow)','data-id':e.id},edgeG);p.onclick=ev=>{ev.stopPropagation();showEdge(e);highlightEdge(e)};edgeEls[e.id]=p}
function lines(label){if(label.length<=25)return[label];const cut=Math.max(label.lastIndexOf(' ',25),label.lastIndexOf('·',25));return cut>8?[label.slice(0,cut),label.slice(cut+1)]:[label.slice(0,24),label.slice(24,46)]}
const relativeSide=n=>n.id===anchor?'anchor':levels[n.id]<0?'prior':levels[n.id]>0?'later':n.side;
const nodeEls={};for(const n of data.nodes){const p=pos[n.id],origin=n.id===originalAnchor&&n.id!==anchor?' origin-anchor':'',g=el('g',{transform:`translate(${p.x} ${p.y})`,class:`node ${relativeSide(n)} ${n.kind}${origin}`,'data-id':n.id,tabindex:'0',role:'button','aria-label':n.label},nodeG);const radius=n.kind==='author'||n.kind==='thinker'?28:n.kind==='movement'?4:10;el('rect',{width:nodeW,height:nodeH,rx:radius},g);const ls=lines(n.label);ls.forEach((s,i)=>{const t=el('text',{x:12,y:ls.length===1?24:18+i*15},g);t.textContent=s});const m=el('text',{x:12,y:49,class:'meta'},g);m.textContent=`${n.era} · ${n.kind}`;g.addEventListener('click',ev=>{ev.stopPropagation();selectNode(n.id,false)});g.addEventListener('keydown',ev=>{if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();selectNode(n.id,false)}});nodeEls[n.id]=g}

function closure(start,adj,back){const nodes=new Set([start]),edges=new Set(),q=[start];while(q.length){const id=q.shift();for(const e of adj[id]||[]){edges.add(e.id);const next=back?e.source:e.target;if(!nodes.has(next)){nodes.add(next);q.push(next)}}}return{nodes,edges}}
function clearHighlight(){Object.values(nodeEls).forEach(x=>{x.classList.remove('active','faded','match','selected');x.removeAttribute('aria-selected')});Object.values(edgeEls).forEach(x=>x.classList.remove('active','faded'))}
function highlightNode(id){clearHighlight();const a=closure(id,incoming,true),d=closure(id,outgoing,false),ns=new Set([...a.nodes,...d.nodes]),es=new Set([...a.edges,...d.edges]);Object.entries(nodeEls).forEach(([k,x])=>x.classList.add(ns.has(k)?'active':'faded'));Object.entries(edgeEls).forEach(([k,x])=>x.classList.add(es.has(k)?'active':'faded'));if(nodeEls[id]){nodeEls[id].classList.add('selected');nodeEls[id].setAttribute('aria-selected','true')}}
function highlightEdge(e){clearHighlight();Object.entries(nodeEls).forEach(([k,x])=>x.classList.add(k===e.source||k===e.target?'active':'faded'));Object.entries(edgeEls).forEach(([k,x])=>x.classList.add(k===e.id?'active':'faded'))}
function showNode(n){const ins=incoming[n.id]||[],outs=outgoing[n.id]||[],role=n.id===anchor?'현재 확장 기준':n.id===originalAnchor?'최초 입력 책':levels[n.id]<0?'선행 계보':'후대 계보';document.getElementById('detail').innerHTML=`<div class="eyebrow">${role}</div><h3>${esc(n.label)}</h3><p class="summary">${esc(n.summary)}</p><dl class="facts"><dt>시대</dt><dd>${esc(n.era)}</dd><dt>종류</dt><dd>${esc(n.kind)}</dd><dt>앞에서 옴</dt><dd>${ins.length}개</dd><dt>뒤로 이어짐</dt><dd>${outs.length}개</dd></dl>${[...ins,...outs].map(e=>`<span class="badge">${esc(byId[e.source].label)} → ${esc(byId[e.target].label)}</span>`).join('')}`}
function showEdge(e){document.getElementById('detail').innerHTML=`<div class="eyebrow">${esc(e.relation_type)}</div><h3>${esc(byId[e.source].label)} → ${esc(byId[e.target].label)}</h3><p class="summary">${esc(e.explanation)}</p><dl class="facts"><dt>근거 요약</dt><dd>${esc(e.evidence_summary)}</dd><dt>신뢰도</dt><dd>${esc(e.confidence)}</dd><dt>중요도</dt><dd>${e.importance}</dd></dl><h4>출처</h4>${e.sources.map(s=>`<div class="source"><a href="${esc(s.url)}" target="_blank" rel="noreferrer">${esc(s.title)}</a><br><small>${esc(s.publisher)} · ${esc(s.grade)}</small><br>${esc(s.support)}</div>`).join('')}`}

let scale=1,tx=0,ty=0,drag=null;
function apply(){viewport.setAttribute('transform',`translate(${tx} ${ty}) scale(${scale})`)}
function fit(){const box=svg.getBoundingClientRect(),pad=40;scale=Math.min((box.width-pad*2)/worldW,(box.height-pad*2)/worldH,1.2);tx=(box.width-worldW*scale)/2;ty=(box.height-worldH*scale)/2;apply()}
function centerNode(id){const p=pos[id];if(!p)return false;const box=svg.getBoundingClientRect();scale=Math.max(.78,Math.min(1.25,scale));tx=box.width/2-(p.x+nodeW/2)*scale;ty=box.height/2-(p.y+nodeH/2)*scale;apply();return true}
function selectNode(id,center=false){const n=byId[id];if(!n)return false;showNode(n);highlightNode(id);if(center)centerNode(id);return true}
svg.addEventListener('wheel',e=>{e.preventDefault();const r=svg.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top,old=scale;scale=Math.max(.3,Math.min(2.4,scale*Math.exp(-e.deltaY*.001)));tx=mx-(mx-tx)*(scale/old);ty=my-(my-ty)*(scale/old);apply()},{passive:false});
svg.addEventListener('pointerdown',e=>{if(e.target.closest('.node,.edge'))return;drag={x:e.clientX,y:e.clientY,tx,ty};svg.setPointerCapture(e.pointerId);svg.classList.add('dragging')});
svg.addEventListener('pointermove',e=>{if(!drag)return;tx=drag.tx+e.clientX-drag.x;ty=drag.ty+e.clientY-drag.y;apply()});
svg.addEventListener('pointerup',()=>{drag=null;svg.classList.remove('dragging')});svg.addEventListener('click',e=>{if(e.target.closest&&e.target.closest('.node,.edge'))return;clearHighlight()});
document.getElementById('fit').onclick=fit;document.getElementById('reset').onclick=()=>{clearHighlight();document.getElementById('search').value=''};
document.getElementById('search').oninput=e=>{clearHighlight();const q=e.target.value.trim().toLowerCase();if(!q)return;Object.entries(nodeEls).forEach(([id,x])=>{if(`${byId[id].label} ${byId[id].summary}`.toLowerCase().includes(q))x.classList.add('match');else x.classList.add('faded')})};
window.atlasUI={selectNode,centerNode,originalAnchor,viewAnchor:anchor};
window.addEventListener('resize',fit);requestAnimationFrame(()=>{fit();if(anchor!==originalAnchor)selectNode(anchor,true)});
</script>
</body></html>'''


STATIC_DEMO_NOTICE = (
    '<div class="hint" id="static-demo-notice" '
    'style="top:auto;left:auto;right:16px;bottom:16px">'
    "정적 데모 · 노드 클릭 후 다시 분석·확장하는 기능은 로컬 서버 모드(README)에서만 제공됩니다"
    "</div>"
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="체크포인트 JSON을 GitHub Pages용 정적 데모 HTML로 변환")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--title")
    parser.add_argument("--author")
    parser.add_argument("--no-demo-note", action="store_true",
                        help="정적 데모 전용 안내 문구를 넣지 않는다")
    args = parser.parse_args()

    data = json.loads(args.input.read_text(encoding="utf-8"))
    if args.title:
        data.setdefault("meta", {})["title"] = args.title
    if args.author:
        data.setdefault("meta", {})["author"] = args.author
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    source = HTML.replace("__DATA__", payload)
    # The offline artifact from src.cli/src.server stays clean; only this
    # publish path labels the page as a static demo without click expansion.
    if not args.no_demo_note:
        source = source.replace("</body>", STATIC_DEMO_NOTICE + "</body>")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(source, encoding="utf-8")
    print(f"written: {args.output} ({len(data['nodes'])} nodes, {len(data['edges'])} edges)")


if __name__ == "__main__":
    main()
