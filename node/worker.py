"""
worker.py — 서브: 단락 1개 작성 [그룹 2 / LLM ✓ 중온]

역할:
  메인이 넘긴 WorkerPackage '하나만' 읽고, 담당 섹션의 서술 단락 1개를
  Few-shot 포맷에 맞춰 작성. 표/수치는 건드리지 않고 '왜 이런 결과인가'만 설명.

입력 → 출력:
  WorkerPackage → SectionDraft(서술 + 한 줄 요약 + 출처 + 사용 숫자)

LLM: worker_llm() 사용(중온).
의존: llm.llm_model.worker_llm, support.prompts(서브 공통 + 섹션별 Few-shot)

주의:
  - 받은 패키지 '밖의' 데이터·근거를 끌어오지 않는다(RAG 직접 호출 금지).
  - 데이터에 없는 숫자를 만들지 않는다.
  - 6개 섹션이 같은 함수를 공유하되, 섹션 ID에 따라 입력(facts·Few-shot)만 갈아끼운다.
  - 결과는 state.drafts에 누적(merge)된다 → state.py의 reducer 규칙과 짝.
"""

from llm.llm_model import worker_llm, cached_system
from state.models import SectionDraft
from support.prompts import WORKER_SYSTEM
from support.text import strip_emojis


def _find_section(outline: dict, sid: str) -> dict:
    """패키지에 동봉된 outline(dict)에서 담당 섹션의 기획(goal·must_cover 등)을 찾는다."""
    for s in outline.get("sections", []):
        if s.get("id") == sid:
            return s
    return {"id": sid, "title": sid, "goal": "", "must_cover": [], "tone": ""}


def worker(state):
    """Send로 받은 1인분 패키지(state=WorkerPackage dump)를 읽고 단락 1개를 쓴다."""
    sid = state["section_id"]
    outline = state.get("outline", {})
    sec = _find_section(outline, sid)

    facts = state.get("facts", [])
    facts_text = "\n".join(f"- {f}" for f in facts) if facts else "(없음)"
    human = (
        f"[담당 섹션] {sec.get('title', sid)} (id={sid}) / 톤: {sec.get('tone', '')}\n"
        f"[전체 목차] {[s.get('id') for s in outline.get('sections', [])]}\n"
        f"[앞 단락 요약] {state.get('prev_summaries', [])}\n"
        f"[핵심 사실]\n{facts_text}\n"
        f"[참고 문서] (ISO 조항 — 요구사항 '설명용'이며, 본 보고서가 이를 충족한다는 근거가 아니다)"
        f" {state.get('evidence_slice', [])}\n"
        f"[예시 포맷] {state.get('fewshot', '')}\n"
        f"[지시] 이번에 쓸 단락 목표: {sec.get('goal', '')} / 반드시 포함: {sec.get('must_cover', [])}"
    )
    # 재작성 호출이면 무엇을 고칠지 명시 — blind rewrite 방지 + '진동'(고쳤다 재발) 억제.
    # feedback은 이번 라운드만이 아니라 '이전 라운드들에서 누적된' 지적 전부다(state.feedback_log).
    feedback = state.get("feedback") or []
    if feedback:
        fb_text = "\n".join(f"- {f}" for f in feedback)
        human += (
            f"\n[수정 요청 — 이전 라운드들에서 '누적'된 지적] 아래는 네 이전 초안(들)에서 반복·누적 지적된 것이다."
            f" 한 개를 고치며 '다른 것을 되살리지 말고', 아래 전부를 '동시에' 반영해 다시 써라"
            f"(특히 근거 없는 단정·검증 권고·미래계획은 완전히 삭제):\n{fb_text}"
            # ★피드백 우선순위 — 편집장 지적이 [지켜야 할 규칙]과 충돌하면 규칙이 이긴다.
            #   (편집장의 '정량화·설명 보강' 요구에 답하려다 worker가 '~는 평가되지 않았다',
            #    '향후 ~ 여지가 있다' 같은 문장을 새로 써서 verify에 걸리는 악순환 차단.)
            f"\n[우선순위] 위 지적 중 [핵심 사실]에 없는 수치·개수·비율·범위·분해·산정기준을 새로 쓰라는"
            f" 요구가 있으면 '그 부분은 따르지 마라' — 없는 데이터는 쓰지 않는 것이 최우선 규칙이다."
            f" 그런 요구에 답하기 위해 '~는 평가되지 않았다', '~가 제시되지 않았다' 같은 자기 언급이나"
            f" '향후 ~할 여지가 있다' 같은 미래 전망 문장을 추가하지도 마라(그것도 규칙 위반이다)."
        )

    llm = worker_llm().with_structured_output(SectionDraft)
    draft = llm.invoke([cached_system(WORKER_SYSTEM), ("human", human)])

    # id/title은 코드가 확정한다(LLM이 틀리면 drafts reducer 병합이 깨지므로 ★중요).
    draft.id = sid
    draft.title = sec.get("title", sid)

    # 이모지 최종 제거(코드가 보증) — 데이터에 섞인 이모지가 새어나오는 것까지 차단.
    draft.narrative = strip_emojis(draft.narrative)
    draft.summary = strip_emojis(draft.summary)
    draft.citations = [strip_emojis(c) for c in draft.citations]
    return {"drafts": [draft]}
