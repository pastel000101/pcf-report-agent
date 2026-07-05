"""
assemble.py — 메인: 조립 & 편집(편집장) [그룹 2 / LLM △ 편집만 저온]

역할(두 가지를 합침):
  ① 편집 — 서브 6인의 서술을 모아 문단 간 연결을 다듬고 톤을 통일, 잔여 중복 제거.
  ② 조립 — 표/수치 슬롯을 '코드가' data_pack으로 치환.
  결과는 완성된 Markdown 초안.

입력 → 출력:
  drafts + data_pack + 템플릿 → draft_md(Markdown)

LLM: edit_llm() — 편집 부분만(저온). 슬롯 치환은 코드(support.slots).
의존: llm.llm_model.edit_llm, support.slots, support.prompts(편집 프롬프트)

주의:
  - 편집 단계에서 새 사실/숫자를 추가하지 않는다. 문장 연결·중복 정리만.
  - 숫자는 끝까지 코드가 박는다.
"""

import re

from llm.llm_model import edit_llm, cached_system
from state.models import EditedReport
from support.prompts import EDIT_SYSTEM
from support.slots import render_report
from support.text import strip_emojis

_NUM_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def _numbers_in(text: str) -> set:
    return {t.replace(",", "") for t in _NUM_RE.findall(text or "")}


def _reject_new_numbers(edited: dict, inputs) -> dict:
    """편집 출력에 '입력 어디에도 없던 숫자'가 생긴 섹션은 편집 전 원본으로 폴백한다.
    편집(assemble)은 verify '뒤' 단계라 출력이 재검증되지 않는다 — 편집장이 숫자를
    만들거나 재계산하면 그대로 최종본이 되므로 여기가 마지막 코드 방어선이다.
    기준을 '전체 입력의 숫자 합집합'으로 두는 이유: 중복 제거·문장 이동(규칙 2·6)은
    다른 섹션의 숫자를 옮겨올 수 있어 섹션 단위 비교는 정당한 편집을 오탐한다."""
    allowed = set()
    for d in inputs:
        allowed |= _numbers_in(d.narrative)
    originals = {d.id: d.narrative for d in inputs}
    out = {}
    for sid, narr in edited.items():
        if _numbers_in(narr) - allowed:
            out[sid] = originals.get(sid, narr)   # 신규 숫자 → 그 섹션 편집 폐기
        else:
            out[sid] = narr
    return out


def _edit_narratives(drafts, outline, flow_feedback=None) -> dict:
    """(a) 편집 — 6개 서술을 매끄럽게(전환·톤·중복). 숫자는 안 바꾼다.
    실패해도 원본 서술로 폴백한다(편집은 품질, 숫자가 아니므로).
    flow_feedback: 편집장(editorial)이 flow로 반려한 지적 — 재편집이면 동봉한다.
    (없이 돌리면 같은 입력→같은 출력의 무의미한 재편집이 된다)"""
    originals = {d.id: d.narrative for d in drafts}
    payload = [{"id": d.id, "title": d.title, "narrative": d.narrative} for d in drafts]
    human = (
        f"[전체 목차] {[s.id for s in outline.sections]}\n"
        f"[섹션 서술들] {payload}"
    )
    if flow_feedback:
        human += (
            "\n[재편집 지적 — 직전 편집본에 대한 편집장 반려 사유] "
            "아래 흐름·중복 문제를 이번 편집에서 반드시 해소하라. "
            "단, 반드시 기존 문장의 삭제·이동·순서 조정만으로 풀어라 — "
            "'연결·전환 부족' 지적이라도 새 해석·평가·인과 문장을 만들어 붙이지 마라. "
            "기존 문장만으로 해소가 안 되면 그대로 두어라:\n"
            + "\n".join(f"- {fb}" for fb in flow_feedback)
        )
    try:
        llm = edit_llm().with_structured_output(EditedReport)
        edited = llm.invoke([cached_system(EDIT_SYSTEM), ("human", human)])
        result = {s.id: strip_emojis(s.narrative) for s in edited.sections}
        # 누락된 섹션은 원본으로 보충
        for sid, narr in originals.items():
            result.setdefault(sid, strip_emojis(narr))
        return result
    except Exception:
        return {sid: strip_emojis(n) for sid, n in originals.items()}


def assemble(state):
    dp = state["data_pack"]
    outline = state["outline"]
    drafts = state.get("drafts", [])

    # 재편집(editorial flow 반려)이면 '직전 편집 결과'에서 시작한다 — 앞 라운드가 이미
    # 정리한 중복·전환을 원본 초안으로 되돌리지 않기 위해. 단, 그 사이 worker가 재작성한
    # 섹션은 초안 원문이 src와 달라져 비교가 어긋나므로 자동으로 새 초안을 쓴다.
    prev = state.get("edited_sections") or {}
    inputs = [
        d.model_copy(update={"narrative": prev[d.id]["out"]})
        if d.id in prev and prev[d.id]["src"] == d.narrative else d
        for d in drafts
    ]

    # 편집장이 flow로 반려한 지적을 편집 LLM에 동봉(재편집 라우팅의 이유를 전달).
    ed = state.get("editorial")
    flow_fb = [i.detail for i in ed.issues if i.kind == "flow"] \
        if (ed is not None and not ed.passed) else []

    edited = _edit_narratives(inputs, outline, flow_fb)   # (a) 편집(LLM, 텍스트만)
    edited = _reject_new_numbers(edited, inputs)          # (a') 편집이 만든 신규 숫자 차단(코드)
    md = render_report(dp, outline, edited)               # (b) 슬롯 치환(코드) + 서술 끼우기
    # src=이번 초안 원문(변경 감지 기준), out=편집 결과(다음 재편집의 시작점).
    cache = {d.id: {"src": d.narrative, "out": edited.get(d.id, d.narrative)}
             for d in drafts}
    return {"draft_md": md, "edited_sections": cache}
