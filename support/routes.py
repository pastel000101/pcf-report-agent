"""
routes.py — 분기·팬아웃 규칙 [그룹 3 / LLM ✗]

역할(그래프 흐름 제어):
  ① 분배 결과를 서브 N인에게 팬아웃(병렬 분기).
  ② 검증 후: 통과/상한 초과 → assemble / 실패 → 해당 섹션만 worker 재작성.
  ③ 편집장 평가 후: content → worker 재작성 / flow → assemble 재편집 / 통과·상한·data_gap만 → review.
  ④ 조립 후: 평가 라운드가 남았으면 editorial / 소진이면 review 직행.

의존: state(상태), state.models.Verification

주의:
  - 재작성 무한루프 방지를 위해 횟수 상한을 여기서 강제한다.
"""

from langgraph.types import Send


def fan_out_workers(state):
    """dispatch가 만든 packages를 worker N개로 '병렬 분기'한다.
    각 Send의 payload가 그 worker 인스턴스의 입력 상태가 된다.
    빈 리스트면 분기 없음(주의: dispatch가 반드시 packages를 채워야 함)."""
    packages = state.get("packages") or []
    # WorkerPackage(model)면 dict로 풀어서 보낸다 → worker가 키로 접근
    return [
        Send("worker", pkg.model_dump() if hasattr(pkg, "model_dump") else pkg)
        for pkg in packages
    ]


MAX_REWRITES = 1   # 재작성 무한루프 방지 상한


def _sid(pkg):
    return getattr(pkg, "section_id", None) or (pkg.get("section_id") if isinstance(pkg, dict) else None)


def _send_workers(packages, sids, feedback_by_sec):
    """대상 섹션 패키지를 worker로 Send하되, '그 섹션의 지적(feedback)'을 실어 보낸다.
    → worker가 '무엇을 왜 고쳐야 하는지' 알고 재작성한다(detail을 안 넘기던 blind rewrite 방지)."""
    sends = []
    for p in packages:
        sid = _sid(p)
        if sid not in sids:
            continue
        dump = p.model_dump() if hasattr(p, "model_dump") else dict(p)
        dump["feedback"] = feedback_by_sec.get(sid, [])
        sends.append(Send("worker", dump))
    return sends


def route_after_verify(state):
    """검증 후 다음 행선지 결정 (assemble '전에' 돈다 — 가볍게 숫자부터 맞춤).
      - 통과            → assemble(조립 1회)
      - 실패 & 상한 내    → 실패 섹션 worker만 재작성(Send, 지적 동봉) → verify 재진입
      - 상한 초과/대상없음 → assemble(숫자 자동수정 한계 → 일단 조립해 편집장에게 넘김)
    """
    v = state.get("verification")
    if v is None or v.passed:
        return "assemble"           # 숫자 OK → 조립으로
    if state.get("rewrite_count", 0) > MAX_REWRITES:
        return "assemble"           # 숫자 자동수정 한계 → 조립 후 편집장 평가(이슈는 트레이스에 남음)

    failed = set(v.failed_sections)
    fb = state.get("feedback_log", {})       # 이전 라운드까지 '누적'된 지적(verify가 방금 emit → reducer가 합침)
    sends = _send_workers(state.get("packages") or [], failed, fb)
    return sends or "assemble"


MAX_EDITORIAL = 1   # 편집장 자기수정 라운드 상한
# 2→1(2026-06-30): editorial은 어차피 통과 못 해 자동승인되므로 라운드 수는 최종 결과를
#   안 바꾸고 worker 재작성 비용만 늘린다. data_gap 분류(헛도는 재작성 차단)+feedback(재작성이
#   실제 반응)로 1라운드가 예전 2라운드만큼 효과적 → 1로 충분. 콜 ~28%↓.


def route_after_assemble(state):
    """조립(편집) 후 다음 행선지 — '죽은 editorial 호출' 제거(2026-07-04).

    editorial_rounds가 상한에 달했으면 다음 editorial은 통과든 실패든
    route_after_editorial에서 review로 갈 수밖에 없다(어떤 재수정도 못 일으킴).
    → 마지막 자기수정(재편집·재작성) 결과는 재평가 없이 review로 직행한다.
      실측(run_trace 2026-07-04): 이 스킵으로 런당 ~21s / 입력 14K·출력 2.5K토큰 절약.
    첫 조립(rounds=0)은 그대로 editorial로 간다."""
    if state.get("editorial_rounds", 0) >= MAX_EDITORIAL:
        return "review"
    return "editorial"


def route_after_editorial(state):
    """편집장 평가 후 자기수정 — '고칠 수 있는 것'에만 재작성을 쓴다.
      - 통과/상한 초과 → review(얇은 최종 승인)
      - content 이슈   → 그 섹션 worker 재작성(서술로 고침)
      - flow 이슈만     → assemble 재편집(흐름·톤)
      - data_gap뿐     → review(데이터가 없어 worker/assemble로 못 고침 → 헛도는 재작성 차단)
    """
    ed = state.get("editorial")
    if ed is None or ed.passed:
        return "review"
    if state.get("editorial_rounds", 0) > MAX_EDITORIAL:
        return "review"

    # content(서술 보강으로 고침) → 그 섹션 worker 재작성(누적 지적을 feedback으로 동봉)
    content_secs = {i.section_id for i in ed.issues if i.kind == "content"}
    fb = state.get("feedback_log", {})       # 누적 지적(editorial이 방금 content 이슈 emit → reducer가 합침)
    sends = _send_workers(state.get("packages") or [], content_secs, fb)
    if sends:
        return sends
    # flow(흐름·톤·중복) → 전체 재편집
    if any(i.kind == "flow" for i in ed.issues):
        return "assemble"
    # 남은 게 data_gap뿐 → 서술/편집으로 못 고침 → 재작성 없이 통과(헛도는 재작성 차단)
    return "review"
