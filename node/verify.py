"""
verify.py — 검증 [그룹 2 / LLM △ grader만 온도0]

역할(두 방식으로 점검):
  (a) 서술의 숫자(worker가 numbers_used로 신고)를 data_pack 값과 '결정론적으로' 대조(허용 집합 밖이면 실패) — 순수 코드.
  (b) 서술이 데이터·근거에 충실한지 grader로 판정 — verify_llm()(온도0).

입력 → 출력:
  drafts + data_pack → {"verification": Verification}

주의:
  - (a)에 화이트리스트(표준번호·조항·연도·100% 등)를 둬 오탐 방지.
  - 실패 섹션이 있으면 '그 섹션만' 재작성하도록 라우팅(support.routes)에 넘긴다.
"""

import re
from decimal import Decimal

from llm.llm_model import verify_llm, cached_system
from state.models import Verification, SectionIssue, GraderOutput
from support.prompts import VERIFY_SYSTEM
from support.text import norm_for_match

# 데이터가 아니어도 자연스럽게 등장하는 숫자(오탐 방지)
# ISO 표준번호 계열(14064=GHG 정량·검증 등)은 본문에 정당히 인용되므로 허용.
WHITELIST = {14067, 14064, 14040, 14044, 14025, 100, 1, 2, 0}
REL_TOL = 0.01   # 1% — 반올림 표기 허용


def _num(s):
    if isinstance(s, (int, float)):
        return float(s)
    m = re.search(r"-?\d[\d,]*(\.\d+)?", str(s))
    return float(m.group().replace(",", "")) if m else None


def _collect_numbers(obj, acc):
    """data_pack(dict)에서 모든 수치를 재귀로 모은다 → 허용 집합.
    문자열 필드(감사로그·소명 등) 안에 박힌 숫자도 데이터로 인정한다
    (예: '신뢰도 61%'의 61). 안 그러면 worker가 정당히 인용한 값이 오탐됨."""
    if isinstance(obj, bool):
        return
    if isinstance(obj, Decimal):                 # DataPack의 배출량·계수 등은 Decimal
        acc.add(float(obj))
    elif isinstance(obj, (int, float)):
        acc.add(float(obj))
    elif isinstance(obj, str):
        for tok in re.findall(r"-?\d[\d,]*(?:\.\d+)?", obj):
            try:
                acc.add(float(tok.replace(",", "")))
            except ValueError:
                pass
    elif isinstance(obj, dict):
        for v in obj.values():
            _collect_numbers(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _collect_numbers(v, acc)


def _is_allowed(used, allowed):
    if used in WHITELIST:
        return True
    if 1900 <= used <= 2100 and float(used).is_integer():   # 연도
        return True
    if 14000 <= used <= 14099 and float(used).is_integer(): # ISO 14000 계열 표준번호(14067/14064/14040/14044/14025/14071 등)
        return True
    for a in allowed:
        if abs(used - a) <= max(abs(a) * REL_TOL, 0.01):     # 반올림 허용
            return True
    return False


def _facts_by_section(state):
    """state.packages에서 section_id → facts(list[str]) 맵을 만든다.
    worker가 받은 그 facts가 곧 '코드가 보증한 근거'다 → verify가 같은 기준으로 채점한다."""
    out = {}
    for p in state.get("packages") or []:
        sid = getattr(p, "section_id", None) or (p.get("section_id") if isinstance(p, dict) else None)
        facts = getattr(p, "facts", None)
        if facts is None and isinstance(p, dict):
            facts = p.get("facts")
        if sid:
            out[sid] = facts or []
    return out


def _check_numbers(drafts, dp, facts_by_sec):
    """(a) 결정론적 숫자 대조. numbers_used의 각 숫자가 데이터에 있는지."""
    allowed = set()
    _collect_numbers(dp.model_dump(), allowed)
    # ×100은 '비율로 인용되는' 헤드라인 필드에만 좁게 허용(0.85 → 85%).
    # blanket ×100은 불량률 0.08 → 8.0 같은 오허용을 만들어 파생/환각을 놓친다.
    allowed.add(dp.dqr.primary_data_ratio * 100)
    allowed.add(dp.dqr.target_ratio * 100)
    # 각 섹션 facts에 '코드가' 넣은 표시값(예: 수율 95%)도 허용 — facts는 DataPack에서
    # 코드가 포맷한 값이라 환각 위험 0. ×100 표기·반올림 두더지잡기를 일반적으로 해소한다.
    for facts in facts_by_sec.values():
        for f in facts:
            _collect_numbers(f, allowed)

    issues = []
    for d in drafts:
        for token in d.numbers_used:
            n = _num(token)
            if n is None:
                continue
            if not _is_allowed(n, allowed):
                issues.append(SectionIssue(
                    section_id=d.id, kind="number_mismatch",
                    detail=f"서술의 '{token}'이(가) 데이터에 없음(파생·환각 의심)",
                ))
    return issues


def _grade(drafts, facts_by_sec):
    """(b) 충실성 grader(LLM, 온도0). 실패 시 [] 폴백(코드 검사가 1차 안전망).
    채점 기준 = worker가 받은 그 섹션의 [근거 사실](facts). worker·grader가 같은 기준을
    보므로, worker가 facts를 정당히 서술한 것을 '데이터에 없음'으로 오탐하지 않는다.
    ★grader 이슈는 코드가 quote를 대조해 '실제 서술에 있는 문구'만 통과시킨다
      (근거 사실 목록의 문구를 서술의 문제로 착각하거나, 없는 문장을 지어내는 환각 지적 차단)."""
    payload = [
        {"id": d.id, "근거_사실": facts_by_sec.get(d.id, []), "narrative": d.narrative}
        for d in drafts
    ]
    human = f"[섹션별 근거 사실과 서술]\n{payload}"
    try:
        llm = verify_llm().with_structured_output(GraderOutput)
        out = llm.invoke([cached_system(VERIFY_SYSTEM), ("human", human)])
        issues = list(out.issues)
    except Exception:
        return []

    # 코드 레벨 인용 검증 — quote가 그 섹션 narrative의 부분 문자열(공백 무시)이어야 채택.
    narratives = {d.id: d.narrative for d in drafts}
    kept = []
    for i in issues:
        body = narratives.get(i.section_id)
        if body is None:
            continue                    # 채점 대상에 없는 섹션 지적 → 폐기
        q = norm_for_match(i.quote)
        if not q or q not in norm_for_match(body):
            continue                    # 인용이 서술 원문에 없음(환각 지적) → 폐기
        kept.append(i)
    return kept


def verify(state):
    dp = state["data_pack"]
    drafts = state.get("drafts", [])
    facts_by_sec = _facts_by_section(state)

    # ★섹션 동결: 재진입(재작성 후)이면 '이번에 재작성된 섹션'만 재채점한다.
    #   통과한 섹션을 매 라운드 재채점하면 안 바뀐 텍스트에서 새 지적이 계속 나오는
    #   '래칫' 현상이 생기고(grader 비결정성), 토큰도 낭비된다.
    #   rewrite_sections는 직전 verify(실패 섹션) 또는 editorial(content 섹션)이 기록한다.
    targets = set(state.get("rewrite_sections") or [])
    graded = [d for d in drafts if d.id in targets] if targets else drafts

    issues = _check_numbers(graded, dp, facts_by_sec) + _grade(graded, facts_by_sec)
    failed = sorted({i.section_id for i in issues})
    v = Verification(passed=(len(issues) == 0), failed_sections=failed, issues=issues)
    # 실패할 때마다 카운터 +1 (routes의 상한 판정 기준). 통과면 유지.
    bump = 0 if v.passed else 1
    # 섹션별 지적을 feedback_log에 '누적'(state reducer가 이전 라운드와 합침) → 재작성 worker가
    # 이전 라운드 지적까지 전부 보고 '진동'(고쳤다 재발)을 막는다.
    # quote(코드가 검증한 문제 문장)를 동봉해 worker가 '어느 문장'인지 정확히 알게 한다.
    new_fb = {}
    for i in issues:
        detail = i.detail + (f' (문제 문장: "{i.quote}")' if i.quote else "")
        new_fb.setdefault(i.section_id, []).append(detail)
    return {"verification": v, "rewrite_count": state.get("rewrite_count", 0) + bump,
            "feedback_log": new_fb, "rewrite_sections": failed}
