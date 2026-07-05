"""
review.py — 얇은 최종 승인(결재 게이트) [그룹 2 / LLM ✗]

AI가 verify(숫자)·editorial(편집)로 자기수정을 끝낸 '깨끗한 초안'에 대해,
사람이 마지막 한 번 승인/반려만 한다(책임 앵커). 설정으로 끌 수 있다.

  - require_human_approval=False(기본): 자동 승인 → render
  - require_human_approval=True       : interrupt로 사람 결재 대기(checkpointer 필요)

입력 → 출력:
  draft_md → {"approved": bool}  (+반려 시 코멘트)

주의:
  - 반려 시 코멘트와 함께 기획 단계로 되돌리는 분기는 후속(HITL 배선)에서.
"""

def review(state):
    if not state.get("require_human_approval"):
        return {"approved": True}        # 무인 모드: 자동 승인
    # TODO: interrupt(draft_md 제시) → 사람 승인/반려 수집. checkpointer 필요.
    #       지금은 배선 전이라 보류(None) 표시.
    return {"approved": None}
