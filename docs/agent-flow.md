# 11. AI 에이전트 전체 흐름 (파일·함수 단위)

> **목적**: "실행이 어디서 시작해서(어느 파일의 어느 함수) → 어디로 가는지(어느 파일의 어느 함수)"를
> 끝까지 추적할 수 있게 만든 지도. 코드를 처음 보는 사람이 이 문서 하나로 전체 파이프라인을 따라갈 수 있어야 한다.
> 작성: 2026-07-04 (route_after_assemble·data_gap_log 반영 시점 기준)

---

## 0. 한눈에 보는 전체 흐름

```
[진입점] main.py run()  ──(state 초기화)──▶  graph.py build_graph().invoke(state)
                                                    │
        ┌───────────────────────────────────────────┘
        ▼
  collect ──▶ plan ──▶ retrieve ──▶ dispatch ──(fan_out_workers: Send ×6)──▶ worker ×6 (병렬)
 (payload→      (코드 목차)   (RAG 검색)   (섹션별 팩트시트)                    (섹션 서술 LLM)
  DataPack)                                                                        │
        ┌──────────────────────────────────────────────────────────────────────────┘
        ▼
     verify ──(route_after_verify)──┬─ 실패(상한 내) ─▶ worker 재작성(실패 섹션만) ─▶ verify 재진입 …[루프A]
 (숫자대조 코드                      │
  + grader LLM)                     └─ 통과 or 상한 초과 ─▶ assemble ──(route_after_assemble)──┐
                                                     (편집 LLM + 슬롯 코드)                     │
        ┌───────────────────────────────────────────────────────────────────────────────────────┤
        │                                          라운드 소진 시 ─▶ review 직행                 │
        ▼                                                                                       │
    editorial ──(route_after_editorial)──┬─ content ─▶ worker 재작성 ─▶ verify ─▶ assemble …[루프B]
 (편집장 LLM: 완결성·흐름)                │─ flow    ─▶ assemble 재편집 ──▶ (route_after_assemble)
                                         └─ 통과/상한/data_gap만 ─▶ review ──▶ render ──▶ END
                                                                    (승인 게이트)  (.md/.pdf/백로그 저장)
```

- **루프 A (숫자·충실성)**: worker ⇄ verify — 상한 `MAX_REWRITES=1` ([support/routes.py](../support/routes.py))
- **루프 B (편집 자기수정)**: editorial → worker/assemble → … — 상한 `MAX_EDITORIAL=1` ([support/routes.py](../support/routes.py))
- LLM을 쓰는 노드는 **worker / verify(grader) / assemble(편집) / editorial** 4곳뿐. 나머지는 전부 결정적 코드.
- 설계 원칙: **숫자는 코드만 만든다**(collect가 유일한 출처, LLM은 인용만) + **LLM 평가자의 출력도 코드가 재검증**한다.

---

## 1. 진입점

### 1-1. 정식 진입점 — [main.py](../main.py) `run()`
- 외부(API/CLI)에 노출되는 유일한 함수. `report_id, payload, output_kind, audience, require_human_approval, report_name`을 받는다.
- 하는 일: `report_name` 미지정 시 `{report_id}_{타임스탬프}` 생성 → 초기 state(dict) 구성 → **[graph.py](../graph.py) `build_graph()`** 호출 후 `.invoke(state)` 로 그래프 실행 → 최종 state(dict) 반환.
- CLI: 같은 파일의 `_cli()` (`python main.py --report-id 101 …`)가 `run()`을 호출.
- `.env` 로드는 [llm/llm_model.py](../llm/llm_model.py) 최상단 `load_dotenv()`가 import 시점에 처리.

### 1-2. 디버깅 진입점 — [trace_run.py](../trace_run.py) `main()`
- `run()` 대신 `graph.stream(…, stream_mode="updates", callbacks=[Trace()])`으로 실행하며,
  `Trace(BaseCallbackHandler)`가 모든 LLM 호출의 SYSTEM/HUMAN 입력·AI 응답·token usage를 가로채
  `output/run_trace_YYYYmmdd_HHMMSS.md` 타임라인으로 저장. 회귀분석은 전부 이 파일로 한다.

### 1-3. 그래프 조립 — [graph.py](../graph.py) `build_graph()`
- `StateGraph(ReportState)`에 노드 10개를 등록하고 엣지를 배선한 뒤 `compile()`.
- 고정 엣지: `START→collect→plan→retrieve→dispatch`, `worker→verify`, `review→render→END`.
- 조건부 엣지 4곳(라우팅 함수는 전부 [support/routes.py](../support/routes.py)):

| 분기점 | 라우팅 함수 | 가능한 행선지 |
|---|---|---|
| dispatch 뒤 | `fan_out_workers` | `worker` ×N (Send 병렬) |
| verify 뒤 | `route_after_verify` | `worker`(재작성) / `assemble` |
| assemble 뒤 | `route_after_assemble` | `editorial` / `review`(라운드 소진 시 직행) |
| editorial 뒤 | `route_after_editorial` | `worker`(content) / `assemble`(flow) / `review` |

### 1-4. 실행 전제조건
- **Ollama 서버 가동**(retrieve의 임베딩) — 안 떠 있으면 retrieve에서 `ConnectionError`.
- `.env`: `ANTHROPIC_API_KEY`, (선택) `LLM_{EDIT|VERIFY|WORKER}_MODEL/_TEMP`.
- PDF: WeasyPrint + GTK 런타임(Windows). 없으면 .md만 산출(치명적 아님).

---

## 2. 노드별 상세 — "이 노드는 무엇을 받아, 무엇을 하고, 어디로 가는가"

### ① collect — [node/collect.py](../node/collect.py) `collect(state)` — LLM ✗
- **입력**: `state["payload"]`(backend 도메인 dict). 없으면 `load_sample_payload()`가
  [domi_data/sample_payload.json](../domi_data/sample_payload.json)으로 폴백.
- **하는 일**: payload를 `DataPack`([state/datapack.py](../state/datapack.py))으로 정규화하고,
  `_derive(dp)`가 파생값(Scope 비율·질량수지·breakdown 기여%·핫스팟·PCF 단위)을 **코드로** 계산.
  여기가 **모든 숫자의 유일한 출처** — 이후 어떤 LLM도 숫자를 만들지 않는다.
- **출력**: `{"data_pack": DataPack}` → **plan**으로.

### ② plan — [node/plan.py](../node/plan.py) `plan(state)` — LLM ✗
- **입력**: `output_kind`, `audience`.
- **하는 일**: `OUTLINES[output_kind]`(코드 상수 `EVIDENCE_REPORT_OUTLINE`, 6섹션: summary·lci·lcia·interpretation·governance·conclusion)를 `Outline`으로 변환. **plan LLM은 2026-07에 폐기** — LLM이 must_cover에 구체 항목을 지어내던 환각의 뿌리였고, 규제 문서는 구조가 일정해야 하므로 목차를 코드로 고정.
- **출력**: `{"outline": Outline}` → **retrieve**로.

### ③ retrieve — [node/retrieve.py](../node/retrieve.py) `retrieve(state)` — LLM ✗ (임베딩만)
- **입력**: `outline`.
- **하는 일**: `RAG_SECTIONS`(lci·lcia·interpretation·governance — summary·conclusion은 준수단정 유발로 구조적 제외)에 대해:
  `_queries(sp)`가 "목표 1건 + must_cover 항목별 1건"의 짧은 질의로 분해 →
  [rag/retriever.py](../rag/retriever.py) `search(query, k)`(Chroma 벡터스토어 + Ollama bge-m3 임베딩, ISO 14067/14044 청크) →
  `_interleave()` rank 인터리브 → `_select()` 선별 가드(정의 조항 ≤2 `MAX_DEFINITIONS`, 같은 조항 ≤2 `MAX_PER_CLAUSE`, 앞 섹션 중복 배제 + `MIN_PER_SECTION` 보충).
- **출력**: `{"evidence": {섹션id: [청크,…]}}` → **dispatch**로.

### ④ dispatch — [node/dispatch.py](../node/dispatch.py) `dispatch(state)` — LLM ✗
- **입력**: `data_pack`, `outline`, `evidence`.
- **하는 일**: 섹션별 팩트 빌더 `FACT_BUILDERS`(`_facts_summary`/`_facts_lci`/`_facts_lcia`/`_facts_interp`/`_facts_governance`/`_facts_conclusion`)가 DataPack에서 **라벨된 사실 문장(facts)**을 코드로 포맷(숫자 포맷은 표 렌더와 동일한 [support/slots.py](../support/slots.py) `_num` 재사용 → 표↔서술 드리프트 방지). `_method_facts()`(산정 경계·GWP·할당)는 전 섹션 공통 주입.
- **출력**: `{"packages": [WorkerPackage ×6]}` (facts + evidence_slice + outline + fewshot 자리) → 분기점으로.

### ⑤ 팬아웃 — [support/routes.py](../support/routes.py) `fan_out_workers(state)`
- packages를 `Send("worker", pkg.model_dump())` ×N으로 변환 → **worker 6개가 병렬 실행**.
  각 Send의 payload가 그 worker 인스턴스의 입력 state가 된다(전체 state가 아님!).

### ⑥ worker — [node/worker.py](../node/worker.py) `worker(state)` — **LLM ✓** (Haiku, temp 0.4)
- **입력**: WorkerPackage dump(`section_id`, `facts`, `evidence_slice`, `outline`, `prev_summaries`, `fewshot`, `feedback`).
- **하는 일**: `_find_section()`으로 담당 섹션 기획을 찾고, human 메시지([담당 섹션]/[전체 목차]/[핵심 사실]/[참고 문서]/[지시]…) 구성. **재작성 호출이면** `feedback`(누적 지적)을 `[수정 요청]`+`[우선순위]`(facts에 없는 수치 요구는 무시하라) 블록으로 동봉.
  LLM: [llm/llm_model.py](../llm/llm_model.py) `worker_llm()` + `cached_system(WORKER_SYSTEM)`([support/prompts.py](../support/prompts.py)) + `with_structured_output(SectionDraft)`.
  후처리(코드): `draft.id/title` 강제 확정(reducer 병합 보호), [support/text.py](../support/text.py) `strip_emojis` 3필드.
- **출력**: `{"drafts": [SectionDraft]}` — state의 `drafts`는 `merge_drafts` reducer([state/state.py](../state/state.py))로 병합: 같은 id면 **교체**(재작성이 중복으로 안 쌓임). → 고정 엣지로 **verify**.

### ⑦ verify — [node/verify.py](../node/verify.py) `verify(state)` — **LLM △** (grader만, temp 0)
- **입력**: `data_pack`, `drafts`, `packages`(→`_facts_by_section()`으로 섹션별 채점 기준), `rewrite_sections`.
- **하는 일** (2단 검증, **섹션 동결**: 재진입이면 `rewrite_sections`의 섹션만 재채점 — 래칫 방지):
  - (a) `_check_numbers()` — **순수 코드**: draft의 `numbers_used` 각 숫자가 DataPack 전체(`_collect_numbers` 재귀 수집)+facts 표시값 허용집합에 있는지 대조. `WHITELIST`(ISO 표준번호·연도 등)·`REL_TOL=1%`로 오탐 방지.
  - (b) `_grade()` — grader LLM: `verify_llm()` + `cached_system(VERIFY_SYSTEM)` + `GraderOutput`. 출력 이슈의 `quote`를 코드가 `norm_for_match`로 실제 서술과 대조 — **원문에 없는 인용(환각 지적)은 폐기**.
- **출력**: `{"verification", "rewrite_count"(실패 시 +1), "feedback_log"(reducer 누적), "rewrite_sections"(실패 섹션)}`.
- **행선지**: `route_after_verify` — 통과 or `rewrite_count > MAX_REWRITES(1)` → **assemble** / 실패(상한 내) → `_send_workers()`가 실패 섹션 패키지에 feedback을 실어 **worker** 재작성(→ 다시 verify) **[루프 A]**.

### ⑧ assemble — [node/assemble.py](../node/assemble.py) `assemble(state)` — **LLM △** (편집만, temp 0.2)
- **입력**: `data_pack`, `outline`, `drafts`, `edited_sections`(직전 편집 캐시), `editorial`(flow 반려 시).
- **하는 일**:
  - 재편집이면 직전 편집 결과(`edited_sections[sid]["out"]`)에서 이어 편집(단 `src`≠현재 초안이면 그 섹션은 재작성된 것 → 새 초안 사용).
  - (a) `_edit_narratives()` — 편집 LLM: `edit_llm()` + `cached_system(EDIT_SYSTEM)` + `EditedReport`. editorial의 **flow 지적만** `[재편집 지적]`으로 동봉. 실패 시 원본 폴백.
  - (a') `_reject_new_numbers()` — **코드 가드**: 편집 출력에 '전체 입력 어디에도 없던 숫자'가 생긴 섹션은 편집 폐기·원본 폴백(편집은 verify 뒤라 재검증이 없으므로 마지막 방어선).
  - (b) [support/slots.py](../support/slots.py) `render_report(dp, outline, edited)` — 표/수치 슬롯을 **코드가** DataPack으로 치환 + 서술 삽입 → Markdown 완성.
- **출력**: `{"draft_md", "edited_sections"}`.
- **행선지**: `route_after_assemble`(2026-07-04 신설) — `editorial_rounds >= MAX_EDITORIAL(1)`이면 **review 직행**(다음 editorial은 라우팅을 못 바꾸는 죽은 호출이므로 생략), 아니면 **editorial**.

### ⑨ editorial — [node/editorial.py](../node/editorial.py) `editorial_review(state)` — **LLM ✓** (temp 0)
- **입력**: `draft_md`, `outline`(유효 섹션 id↔제목 매핑 + 섹션별 설계 goal/must_cover를 human에 명시).
- **하는 일**: `verify_llm()` + `cached_system(EDITORIAL_SYSTEM)` + `EditorialReview`. 완결성(설계 범위 기준)·흐름·톤·중복 평가, 이슈를 kind로 분류: `content`(재작성으로 해결, fix_source 필수) / `flow`(재편집으로 해결 — 삭제·이동·순서 조정만으로 해소 가능한 것만) / `data_gap`(데이터 없어 해결 불가).
  후처리(코드): `_demote_ungrounded_content()` — fix_source가 초안 원문에서 확인 안 되는 content를 **data_gap으로 강등**(전면 재작성 폭주 차단).
- **출력**: `{"editorial", "editorial_rounds"(실패 시 +1), "feedback_log"(content만 누적), "rewrite_sections"(content 섹션), "data_gap_log"(라운드 간 누적 — 2026-07-04 신설)}`.
- **행선지**: `route_after_editorial` — 통과 or `editorial_rounds > MAX_EDITORIAL` → **review** / content 있음 → **worker** 재작성(Send, 이후 verify→assemble 경유) / flow만 → **assemble** 재편집 / data_gap뿐 → **review**(헛도는 재작성 차단) **[루프 B]**.

### ⑩ review — [node/review.py](../node/review.py) `review(state)` — LLM ✗
- `require_human_approval=False`(기본)면 `{"approved": True}` 자동 승인. True면 HITL interrupt 예정(TODO, checkpointer 필요). → 고정 엣지로 **render**.

### ⑪ render — [node/render.py](../node/render.py) `render(state)` — LLM ✗
- **하는 일**:
  1. [pdf](../pdf/__init__.py) `embed_datapack(md, dp)` — .md 끝에 DataPack(JSON)을 HTML 주석으로 임베드 → `output/{stem}.md` 저장(`_report_stem()`이 파일명 확정).
  2. `_write_data_gaps()` — `data_gap_log`(editorial 전 라운드 누적)를 `{stem}_data_gaps.md` 백로그로 산출(사람이 취사선택; 자동 반영 금지).
  3. [pdf/to_pdf.py](../pdf/to_pdf.py) `md_to_pdf(md, path, title)` — WeasyPrint(+GTK)로 PDF 병행 산출. 차트는 임베드된 DataPack에서 [pdf/charts.py](../pdf/charts.py)가 재생성해 표 위에 주입. 실패해도 .md는 유지.
- **출력**: `{"output_path", "output_pdf_path", "data_gaps_path"}` → **END**. `run()`이 최종 state를 반환.

---

## 3. 상태(state) 계약 — 누가 쓰고 누가 읽나

정의: [state/state.py](../state/state.py) `ReportState`(TypedDict). 대부분 last-write-wins, reducer 2종만 특수 병합.

| 키 | 쓰는 곳 | 읽는 곳 | 비고 |
|---|---|---|---|
| `payload` | 진입점(main) | collect | 없으면 샘플 폴백 |
| `data_pack` | collect | dispatch, verify, assemble, render | 숫자의 유일한 출처 |
| `outline` | plan | retrieve, dispatch, assemble, editorial | 코드 고정 목차 |
| `evidence` | retrieve | dispatch | 섹션별 RAG 청크 |
| `packages` | dispatch | routes(fan-out/재작성), verify(채점 기준) | 섹션별 팩트시트 |
| `drafts` | worker ×N | verify, assemble | ★reducer `merge_drafts`: 같은 id 교체 |
| `verification` / `rewrite_count` / `rewrite_sections` | verify (rewrite_sections는 editorial도) | routes, verify(섹션 동결) | 루프 A 제어 |
| `draft_md` / `edited_sections` | assemble | editorial, render / assemble(재편집 이어가기) | |
| `editorial` / `editorial_rounds` | editorial | routes, assemble(flow 지적 동봉) | 루프 B 제어 |
| `feedback_log` | verify, editorial | routes→worker(재작성 지적 동봉) | ★reducer `merge_feedback`: 라운드 누적 |
| `data_gap_log` | editorial | render(백로그) | ★reducer `merge_feedback`: 라운드 누적 |
| `approved` | review | (최종 상태) | |
| `output_path` / `output_pdf_path` / `data_gaps_path` | render | (최종 상태) | |

---

## 4. LLM 구성 — [llm/llm_model.py](../llm/llm_model.py)

| 역할 함수 | 쓰는 노드 | .env 키 | 기본 모델 | 기본 온도 |
|---|---|---|---|---|
| `worker_llm()` | worker | `LLM_WORKER_MODEL/_TEMP` | claude-haiku-4-5-20251001 | 0.4 (서술 자연스러움) |
| `edit_llm()` | assemble | `LLM_EDIT_MODEL/_TEMP` | 〃 | 0.2 (저온 편집) |
| `verify_llm()` | verify(grader), editorial | `LLM_VERIFY_MODEL/_TEMP` | 〃 | 0.0 (결정적 판정) |

- 공통: `_build(role, default_temp)`가 .env에서 모델·온도를 읽어 `ChatAnthropic` 생성. 모든 호출부는 `cached_system(텍스트)`로 시스템 프롬프트에 `cache_control: ephemeral`을 건다.
- ⚠️ **캐시 실측(2026-07-04)**: 4개 시스템 프롬프트 전부 Haiku 4.5 최소 캐시 프리픽스(4,096tok) 미만(WORKER≈2.5K)이라 **현재 캐시는 전 역할 미적용**(조용히 무시, 에러 없음). 활성화 경로: 섹션별 Few-shot을 시스템 프롬프트 뒤에 붙여 4,096 초과 or Sonnet 계열 전환.
- 프롬프트 원문: [support/prompts.py](../support/prompts.py) — `WORKER_SYSTEM`/`EDIT_SYSTEM`/`VERIFY_SYSTEM`/`EDITORIAL_SYSTEM`(+공통 `DOC_CONTEXT` '제시' 자세). 구조화 출력 스키마: [state/models.py](../state/models.py).

---

## 5. 자기수정 루프와 상한 (무한루프 방지)

| 루프 | 트리거 | 재작업 단위 | 상한(위치) | 상한 도달 시 |
|---|---|---|---|---|
| A: 숫자·충실성 | verify 실패 | 실패 섹션 worker만 (feedback 동봉) | `MAX_REWRITES=1` ([routes.py](../support/routes.py)) | assemble로 진행(이슈는 트레이스·최종 상태에 잔존) |
| B: 편집 자기수정 | editorial 실패 | content→해당 섹션 worker / flow→assemble 재편집 | `MAX_EDITORIAL=1` ([routes.py](../support/routes.py)) | review로 진행. **마지막 재수정 결과는 재평가하지 않음**(`route_after_assemble`이 editorial 생략) |

- 루프가 '진동'(고쳤다 재발)하지 않게 하는 장치: `feedback_log` 누적(worker가 전 라운드 지적을 동시 인지), verify **섹션 동결**(재작성 섹션만 재채점), editorial **fix_source 코드 대조**(못 고치는 지적을 재작성으로 안 보냄).

---

## 6. 대표 실행 시나리오 (run_trace_20260704_145308 실측)

```
main.run(101) → build_graph().invoke
 ├─ collect(0s) → plan(0s) → retrieve(3.8s) → dispatch
 ├─ worker ×6 병렬(3.8→15.8s)                          … LLM 6콜
 ├─ verify #1: conclusion 1건 실패(15.8→18.5s)          … LLM 1콜
 │   └─ route_after_verify → worker(conclusion 재작성, 18.5→24.3s)   … LLM 1콜
 │       └─ verify #2: 재작성 섹션만 재채점 → 통과(25.0s)  … LLM 1콜
 ├─ assemble #1: 편집+슬롯(25.0→53.5s)                  … LLM 1콜
 │   └─ route_after_assemble: rounds=0 < 1 → editorial
 ├─ editorial #1: 실패(flow 2·data_gap 5, 53.5→82.2s)   … LLM 1콜
 │   └─ route_after_editorial: content 없음·flow 있음 → assemble
 ├─ assemble #2: 재편집(flow 지적 동봉, 82.2→113.2s)     … LLM 1콜
 │   └─ route_after_assemble: rounds=1 >= 1 → review 직행 (editorial #2 생략)
 └─ review(자동 승인) → render(.md+.pdf+data_gaps, 113.2→115.6s) → END
                                          합계: 115.6s · LLM 12콜 · 입력 76.9K/출력 16.6K 토큰
```
