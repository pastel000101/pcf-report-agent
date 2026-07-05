# PCF Report Agent

ISO 14067 제품 탄소발자국(PCF) 산정 결과를 **제3자 검증기관 제출용 산출근거서(Markdown + PDF)로 자동 생성**하는 LangGraph 기반 멀티 에이전트 파이프라인입니다.

LLM 보고서 생성의 가장 큰 리스크는 수치 할루시네이션입니다. 이 프로젝트는 그 문제를 프롬프트가 아니라 **구조로** 풉니다 — 숫자는 코드만 만들고, LLM은 서술만 쓰며, LLM 평가자의 판정조차 코드가 재검증합니다.

📄 예시 산출물: [examples/](examples/) (더미 데이터 기반 — 등장하는 기업·수치는 모두 가상입니다)

## 핵심 설계

- **숫자는 코드만 만든다** — `DataPack`(단일 진실 공급원) → 섹션별 '라벨된 팩트시트' 분배 → 표·수치는 Jinja2 슬롯 렌더링. LLM은 "왜 이런 결과인가"의 서술만 담당.
- **목차도 코드가 확정** — 기획 단계의 LLM을 제거해 환각의 원천을 차단(규제 문서는 구조가 일정해야 함).
- **LLM 평가자의 출력도 코드가 재검증** — ① 서술 속 숫자를 데이터와 결정론적으로 대조 ② 검증 LLM(grader)의 지적 인용문을 원문과 대조해 환각 지적은 폐기 ③ 편집장 AI의 보강 요구는 근거 인용(fix_source)이 확인될 때만 재작성으로 라우팅 ④ 편집 LLM이 만든 신규 숫자는 폴백으로 차단.
- **자기수정 루프 2개(+상한)** — 검증 실패 섹션만 좁혀 재작성(섹션 동결로 재채점 낭비 차단), 편집장 AI가 완결성·흐름을 2차 평가하고 '데이터가 없어 못 고치는 지적'은 data_gap 백로그로 분리.

## 파이프라인

```
collect → plan(코드 목차) → retrieve(RAG) → dispatch → worker ×6 (병렬)
   → verify(숫자 대조 + grader) ⇄ 섹션 재작성 → assemble(편집 + 슬롯 렌더)
   → editorial(편집장 AI) ⇄ 재편집 → review → render(.md + .pdf + 차트)
```

파일·함수 단위 상세 흐름은 [docs/agent-flow.md](docs/agent-flow.md) 참조.

## 실측 지표

- 보고서 초안(PDF 포함) 1건 생성 약 2분, API 비용 약 $0.2 (Claude Haiku 4.5 기준)
- 실행 트레이스(`trace_run.py`) 회귀 분석으로 LLM 호출 20→12회, 입력 토큰 43% 절감
- 검증 런 기준 수치 환각(데이터에 없는 숫자) 0건

## 실행 방법

**사전 준비**

1. Python 3.11+ / `pip install -r requirements.txt`
2. `.env` 작성 — `.env.example` 참조 (`ANTHROPIC_API_KEY` 필수)
3. [Ollama](https://ollama.com) 실행 + `ollama pull bge-m3` (RAG 임베딩)
4. ISO 표준 문서 배치 및 인덱스 구축 — **저작권상 저장소에 미포함**, [data/README.md](data/README.md) 참조
5. (PDF 출력, Windows) GTK3 런타임 설치 — 없어도 .md는 정상 산출

**실행**

```bash
python main.py --report-id 101            # 샘플 더미 데이터로 보고서 생성 → output/
python trace_run.py 101                   # 전 노드·LLM 호출 타임라인 트레이스 생성
```

## 기술 스택

Python · LangGraph · LangChain(langchain-anthropic) · Claude(Haiku 4.5) · ChromaDB + bge-m3(Ollama) · Pydantic 구조화 출력 · Jinja2 · WeasyPrint

## 데이터에 관한 주의

`domi_data/sample_payload.json`과 예시 산출물의 기업명·사업장·수치는 모두 **가상의 더미 데이터**입니다. ISO 표준 원문·파생 인덱스는 저작권 보호를 위해 저장소에 포함하지 않습니다.
