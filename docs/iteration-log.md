# 반복 개선 기록

이 문서는 완성 결과만 보여주기보다, 실패를 어떤 검증 계약과 코드 변경으로 바꿨는지 추적하기 위한 기록이다. 문학 관계의 사실성 자체는 별도 원문 검토가 필요하다.

| 발견한 문제 | 진단 | 변경 | 회귀 방지 증거 |
|---|---|---|---|
| 구조화 출력 스키마가 Codex에서 거부됨 | 일부 속성에 JSON Schema `type`이 없었음 | 모든 응답 필드의 타입·필수값·열거형을 명시 | `schema/research-result.schema.json` |
| 유효한 학술 출처까지 제거됨 | 발행 주체가 아니라 미분류 도메인이라는 이유로 탈락 | 명시적 도메인 정책과 최대 등급, 발행 주체 정규화 추가 | `test_explicit_allowlist_rejects_unknown_personal_search_and_spoofing` |
| 앵커와 무관한 작은 섬이 남음 | 고아 노드만 검사하고 앵커 연결성은 검사하지 않음 | 앵커의 무방향 연결 성분만 보존 | `test_builder_removes_disconnected_non_orphan_island` |
| 결과가 중심 책 주변의 별 모양에 머묾 | 전체 그래프를 한 번에 재요약해 frontier를 건너뜀 | frontier 노드마다 독립 Codex 호출 | `test_engine_makes_one_dedicated_call_per_selected_frontier` |
| 니체에 푸코 연결이 있으면 니체 조사를 완료로 간주 | 차수 0 여부를 완료 조건으로 사용 | 노드별 전용 조사 이력과 FIFO 큐로 완료 여부 분리 | `test_nietzsche_remains_expansion_candidate_after_foucault_child_exists` |
| 선택 노드 확장 후 화면이 최초 입력 책으로 복귀 | 데이터 앵커와 화면 중심을 같은 필드로 사용 | 영구 `anchor_id`와 임시 `view_anchor_id` 분리 | `test_expansion_persists_clicked_node_as_view_anchor` |
| 클릭 확장이 한 단계에서 중단 | 선택 노드만 조사하고 새 노드를 큐에 넣지 않음 | 새 노드만 방향별 FIFO BFS 큐에 추가 | `test_click_expansion_recurses_into_new_nodes_only` |
| 새 노드 선택 강조가 불명확 | 배경 클릭 해제와 노드 이벤트의 경계가 약함 | 명시적 `selected` 상태·ARIA 상태·배경 가드 추가 | `test_html_is_single_file_and_interactive` |
| 조사 실패 시 결과 전체를 잃음 | 성공 경로만 최종 파일을 저장 | `partial`·`timed_out` 체크포인트와 HTML 보존 | `test_all_research_failures_save_valid_partial_checkpoint` |
| 오프라인 결과가 런타임 서버에 의존할 위험 | 로컬 확장 기능이 정적 HTML에 섞일 수 있음 | 확장 스크립트는 로컬 서버 응답에만 주입 | `test_local_mode_injects_runtime_without_polluting_offline_html` |
| 정적 데모만 본 사용자가 클릭 확장 기능이 없다고 오해할 수 있음 | 데모와 로컬 서버 모드의 기능 차이가 페이지 안에 없음 | 데모 발행 CLI가 로컬 전용 안내 문구를 주입, 오프라인 산출물은 미포함 | `test_pages_demo_publish_injects_local_only_notice` |

## 현재 검증 경계

- 자동 검증: 구조, 고아·분리 노드, 크기 상한, 출처 도메인 정책, 해석 관계의 독립 발행 주체, 비밀정보 패턴, 오프라인 자산.
- 자동 검증이 보장하지 않는 것: 문학적 영향 관계의 완전성, 모든 근거 문장의 의미적 타당성, LLM 생성 내용의 객관적 정답성.
- 사람 원문 검토는 수행한 경우에만 별도 입력으로 집계하며, AI 보조 검토를 사람 검토로 표시하지 않는다.
