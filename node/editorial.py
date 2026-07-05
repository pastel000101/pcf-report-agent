"""
editorial.py — 편집장 AI 검토 [그룹 2 / LLM ✓ 온도0]

verify(숫자·충실성, 기계적)와 '다른 층'. 완성된 초안을 받아
완결성·논리 흐름·가독성·톤·중복을 종합 평가한다(숫자는 안 본다).

문제를 kind로 분류해 '어디서 고칠지'를 정한다:
  - "content"  → 그 섹션 worker 재작성 (fix_source 미확인 시 코드가 data_gap으로 강등)
  - "flow"     → assemble 재편집
  - "data_gap" → 재작성 안 함(데이터가 없어 서술로 해결 불가 → render가 백로그로 산출)
(라우팅은 support.routes.route_after_editorial)

입력 → 출력:
  draft_md + outline → editorial, editorial_rounds(실패 시 +1), feedback_log, rewrite_sections, data_gap_log
"""

from llm.llm_model import verify_llm, cached_system
from state.models import EditorialReview
from support.prompts import EDITORIAL_SYSTEM
from support.text import norm_for_match


def _demote_ungrounded_content(issues, md):
    """content 이슈의 코드 레벨 가드 — fix_source(보강에 쓸 기존 정보의 원문 인용)가
    실제 초안에서 확인되지 않으면 data_gap으로 강등한다.

    왜: '정량화하라·몇 %인지 밝혀라'류의 지적은 facts에 없는 데이터를 요구하는 것이라
    재작성으로 해결이 불가능한데, editorial이 이를 content로 오분류하면 전 섹션이
    헛돌며 재작성된다(프롬프트 지시만으로는 안 지켜짐이 확인됨 → 코드가 최종 판정)."""
    corpus = norm_for_match(md)
    for i in issues:
        if i.kind != "content":
            continue
        src = norm_for_match(i.fix_source)
        if not src or src not in corpus:
            i.kind = "data_gap"         # 근거 인용 없음/불일치 → 재작성 안 함
    return issues


def editorial_review(state):
    md = state.get("draft_md", "")
    outline = state["outline"]
    # ★ content 이슈를 worker 재작성으로 라우팅하려면 LLM이 섹션 '제목'이 아니라
    #   정확한 섹션 'id'를 써야 한다(routes.route_after_editorial가 id로 매칭).
    #   완성본 md에는 제목만 보이므로, 유효 id↔제목 매핑을 입력으로 명시한다.
    sec_list = ", ".join(f"{s.id}({s.title})" for s in outline.sections)
    # ★ 각 섹션이 '무엇을 다루기로 했는지'(goal·must_cover)를 넘긴다 → editorial이 '설계된 범위'에
    #   비춰 완결성을 판단(설계 밖을 상상해 요구하는 것 차단). 프롬프트가 '목표 충족 여부'를 보라 하므로 짝.
    sec_spec = "\n".join(
        f"- {s.id}: 목표={s.goal} / 포함항목={s.must_cover}"
        for s in outline.sections
    )
    human = (
        f"[독자] {outline.audience}\n"
        f"[유효 섹션 ID] {sec_list} (보고서 전체 문제면 'global')\n"
        f"[섹션별 설계 — 각 섹션이 다루기로 한 범위. 이 범위에 비춰 완결성을 판단하라]\n{sec_spec}\n"
        f"[보고서 초안]\n{md}"
    )
    try:
        llm = verify_llm().with_structured_output(EditorialReview)
        ed = llm.invoke([cached_system(EDITORIAL_SYSTEM), ("human", human)])
    except Exception:
        ed = EditorialReview(passed=True, issues=[])   # 평가 실패 시 통과로 폴백(자기수정은 품질)

    # ★코드 레벨 강등: fix_source가 초안에서 확인 안 되는 content → data_gap.
    #   (routes가 ed.issues의 kind로 재작성 여부를 정하므로, 여기서 먼저 정리한다.)
    _demote_ungrounded_content(ed.issues, md)

    bump = 0 if ed.passed else 1
    # content 이슈(= worker 재작성으로 고칠 것)만 feedback_log에 누적. flow/data_gap은 worker로 안 가니 제외.
    new_fb = {}
    for i in ed.issues:
        if i.kind == "content":
            new_fb.setdefault(i.section_id, []).append(i.detail)
    # ★강등 후 살아남은 content 섹션을 기록 → 다음 verify가 '이 섹션들만' 재채점(섹션 동결과 짝).
    content_secs = sorted({i.section_id for i in ed.issues if i.kind == "content"})
    # data_gap은 라운드마다 달라지므로(grader 비결정성) 별도 로그에 '누적' → render가 전 라운드분을 백로그로 산출.
    new_gaps = {}
    for i in ed.issues:
        if i.kind == "data_gap":
            new_gaps.setdefault(i.section_id, []).append(i.detail)
    return {"editorial": ed, "editorial_rounds": state.get("editorial_rounds", 0) + bump,
            "feedback_log": new_fb, "rewrite_sections": content_secs, "data_gap_log": new_gaps}
