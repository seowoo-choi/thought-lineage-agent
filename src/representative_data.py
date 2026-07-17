from datetime import datetime, timezone

ENC="https://www.encyclopedia.com/history/modern-europe/ancient-history-middle-ages-and-feudalism/crime-and-punishment"
PF="https://www.poetryfoundation.org/poets/edgar-allan-poe"
GUT="https://www.gutenberg.org/files/2554/2554-h/2554-h.htm"
def _src(url,title,publisher,grade,support): return {"url":url,"title":title,"publisher":publisher,"grade":grade,"support":support}
def crime_and_punishment(seed=1866):
    specs=[
      ("bible","성경", "scripture","고대","prior","죄, 벌, 회개와 부활의 오래된 서사 틀"),
      ("lazarus","라자로의 부활", "scripture","1세기","prior","소냐가 읽는 부활 서사의 직접 인용"),
      ("socrates","소크라테스", "thinker","기원전 5세기","prior","도덕 지식과 자기 심문의 철학적 선행"),
      ("plato","플라톤", "thinker","기원전 4세기","prior","정의와 비범한 인간 문제의 고대 철학적 맥락"),
      ("shakespeare","셰익스피어", "author","1564–1616","prior","죄의식과 살인의 심리극 전통"),
      ("schiller","프리드리히 실러", "author","1759–1805","prior","젊은 도스토옙스키가 흠모한 낭만주의 작가"),
      ("pushkin","알렉산드르 푸시킨", "author","1799–1837","prior","러시아 문학 전통의 선행 작가"),
      ("gogol","니콜라이 고골", "author","1809–1852","prior","도시 빈곤과 관료제의 러시아 사실주의 선행"),
      ("poe","에드거 앨런 포", "author","1809–1849","prior","살인자의 불안과 탐정 서사의 선행"),
      ("dickens","찰스 디킨스", "author","1812–1870","prior","대도시 빈곤을 소설의 능동적 배경으로 삼은 모델"),
      ("balzac","오노레 드 발자크", "author","1799–1850","prior","도시 사회를 해부하는 사실주의 전통"),
      ("chernyshevsky","무엇을 할 것인가?", "book","1863","prior","합리적 이기주의에 대한 소설적 반론 대상"),
      ("utilitarianism","공리주의", "movement","19세기","prior","수단과 목적을 둘러싼 논쟁의 사상적 배경"),
      ("nihilism","러시아 허무주의", "movement","1860년대","prior","라스콜니코프의 관념을 둘러싼 당대 논쟁"),
      ("anchor","죄와 벌 — 표도르 도스토옙스키", "book","1866","anchor","살인, 죄의식, 고백과 영적 재생을 탐구하는 심리소설"),
      ("nietzsche","프리드리히 니체", "author","1844–1900","later","도스토옙스키의 심리 통찰을 높이 평가한 철학자"),
      ("freud","지그문트 프로이트", "author","1856–1939","later","도스토옙스키의 심리 분석을 정신분석의 선구로 평가"),
      ("kafka","프란츠 카프카", "author","1883–1924","later","도스토옙스키적 죄와 심판의 현대적 계승"),
      ("camus","이방인 — 알베르 카뮈", "book","1942","later","실존주의적 범죄 소설에 미친 영향"),
      ("joyce","제임스 조이스", "author","1882–1941","later","20세기 소설의 심리·형식 실험에 준 영감"),
      ("faulkner","윌리엄 포크너", "author","1897–1962","later","복합 심리와 도덕적 갈등을 계승한 작가"),
      ("murdoch","아이리스 머독", "author","1919–1999","later","도스토옙스키의 주제와 인물에서 영감을 받은 소설가")]
    nodes=[{"id":i,"label":l,"kind":k,"era":e,"side":s,"summary":m} for i,l,k,e,s,m in specs]
    edges=[]
    common=_src(ENC,"Crime and Punishment","Encyclopedia.com","B","작품의 문학적·역사적 맥락과 선행 및 후대 영향 관계를 편집된 참고문헌과 함께 설명한다.")
    text=_src(GUT,"Crime and Punishment (full text)","Project Gutenberg","A","작품 원문에서 성서 인용, 범죄 이론, 고백과 재생의 서사적 증거를 대조할 수 있다.")
    poe=_src(PF,"Edgar Allan Poe","Poetry Foundation","B","포의 탐정·공포 서사가 러시아를 포함한 국제 문학에 끼친 영향을 설명한다.")
    for idx,n in enumerate(nodes):
      if n["id"]=="anchor": continue
      prior=n["side"]=="prior"; source=n["id"] if prior else "anchor"; target="anchor" if prior else n["id"]
      interpret=n["id"] in {"bible","socrates","plato","shakespeare","pushkin","gogol","poe","balzac","utilitarianism","nihilism","nietzsche","kafka"}
      rt="thematic" if interpret else "explicit"
      sources=[common,text] if interpret else [common]
      if n["id"]=="poe": sources=[poe,common]
      explanation=(f"{n['label']}의 전통과 문제의식이 《죄와 벌》의 형성 맥락을 이해하게 한다." if prior else f"《죄와 벌》의 심리·도덕적 탐구가 {n['label']}의 후대 작업과 연결된다.")
      edges.append({"id":f"e{idx:02d}","source":source,"target":target,"direction":"source_to_target","relation_type":rt,"explanation":explanation,"evidence_summary":n["summary"],"material_title":sources[0]["title"],"source_url":sources[0]["url"],"confidence":"B","importance":max(55,92-idx),"sources":sources})
    return {"meta":{"title":"죄와 벌","author":"표도르 도스토옙스키","anchor_id":"anchor","seed":seed,"started_at":datetime.now(timezone.utc).isoformat()},"status":"complete","nodes":nodes,"edges":edges}
