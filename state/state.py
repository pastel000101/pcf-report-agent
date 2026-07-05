"""
state.py — 파이프라인 공유 상태(State) 정의 [그룹 1 / LLM ✗]

그래프의 모든 노드가 주고받는 상태 한 덩어리. 여기가 '계약'.
대부분 필드는 last-write-wins(덮어쓰기)지만, 누적이 필요한 3개만 reducer로 병합한다:
drafts(merge_drafts) · feedback_log/data_gap_log(merge_feedback).
"""

from typing import Annotated, Optional, TypedDict

from .datapack import DataPack
from .models import Outline, WorkerPackage, SectionDraft, Verification, EditorialReview


# ---------------------------------------------------------------------------
# reducer — drafts 누적 규칙
#   worker가 팬아웃되어 각자 {"drafts": [SectionDraft]} 를 반환하면, LangGraph가
#   기존값과 새값을 이 함수로 합친다.
#   · 처음: 섹션들이 하나씩 쌓인다.
#   · 재작성: 같은 section id면 '교체'(append 아님) → 중복이 안 쌓인다.
#   이 규칙 덕에 '재작성 턴 시작 시 비우는 리셋'을 따로 안 해도 된다.
# ---------------------------------------------------------------------------
def merge_drafts(existing: Optional[list[SectionDraft]],
                 new: Optional[list[SectionDraft]]) -> list[SectionDraft]:
    existing = existing or []
    if not new:
        return existing
    by_id = {d.id: d for d in existing}
    for d in new:
        by_id[d.id] = d          # 같은 섹션이면 덮어쓰기, 없으면 추가
    return list(by_id.values())


# ---------------------------------------------------------------------------
# reducer — feedback_log 누적 규칙 (섹션별 지적을 '쌓는다')
#   verify/editorial이 매 라운드 {"feedback_log": {sid: [detail,...]}}를 반환하면 여기서 누적.
#   교체가 아니라 append(중복 detail만 제거) → 재작성 worker가 '이전 라운드 지적까지 전부' 봄.
#   목적: worker가 한 지적을 고치며 이전에 고친 걸 되살리는 '진동'을 억제(전 제약을 동시 인지).
# ---------------------------------------------------------------------------
def merge_feedback(existing: Optional[dict], new: Optional[dict]) -> dict:
    merged = dict(existing or {})
    for sid, items in (new or {}).items():
        prev = merged.get(sid, [])
        merged[sid] = prev + [x for x in (items or []) if x not in prev]
    return merged


# ---------------------------------------------------------------------------
# 공유 상태
#   nodes는 일부 키만 담은 dict를 반환하면 LangGraph가 병합한다.
#   Annotated[..., reducer]가 붙은 필드만 특수 병합, 나머지는 덮어쓰기.
# ---------------------------------------------------------------------------
class ReportState(TypedDict, total=False):
    # --- 입력 ---
    report_id: str                       # 식별자(데이터 조회 키)
    report_name: str                     # 산출 파일명(진입점 main이 지정; 없으면 render가 meta로 폴백)
    audience: str                        # 독자
    output_kind: str                     # "brief" | "evidence_report"
    payload: dict                        # backend가 건넨 도메인 데이터(없으면 collect가 샘플 폴백)

    # --- collect (숫자의 유일한 출처) ---
    data_pack: DataPack                  # 정규화된 데이터 팩(파생값 포함)

    # --- plan ---
    outline: Outline                     # 기획 결과

    # --- retrieve (메인만 호출) ---
    evidence: dict[str, list[str]]       # 주제 키 → 근거 청크들

    # --- dispatch ---
    packages: list[WorkerPackage]        # 서브별 작업 패키지

    # --- worker (★ 병렬 누적) ---
    drafts: Annotated[list[SectionDraft], merge_drafts]

    # --- assemble ---
    draft_md: str                        # 완성된 Markdown 초안
    edited_sections: dict[str, dict[str, str]]  # 섹션별 {"src": 초안 원문, "out": 편집 결과}.
                                         # 재편집(editorial flow 반려) 시 out에서 이어 편집하고,
                                         # src≠현재 초안이면 worker가 재작성한 것 → 새 초안 사용

    # --- verify ---
    verification: Verification           # 검증 결과(실패 섹션 포함)
    rewrite_count: int                   # 재작성 횟수(무한루프 방지 상한 체크)
    rewrite_sections: list[str]          # 이번 턴에 재작성할 섹션 ID들

    # --- editorial (편집장 AI) ---
    editorial: EditorialReview           # 편집장 평가(완결성·흐름·가독성)
    editorial_rounds: int                # 편집장 자기수정 라운드(상한 체크)

    # --- 재작성 피드백 (★ verify+editorial 지적을 섹션별로 '누적') ---
    feedback_log: Annotated[dict[str, list[str]], merge_feedback]

    # --- data_gap 백로그 (★ editorial 라운드 간 '누적') ---
    #   editorial은 라운드마다 다른 지적을 내므로(grader 비결정성) 마지막 라운드만 보면
    #   이전 라운드의 data_gap이 유실된다 → feedback_log와 같은 reducer로 전 라운드 누적.
    data_gap_log: Annotated[dict[str, list[str]], merge_feedback]

    # --- review (얇은 최종 승인) ---
    require_human_approval: bool         # True면 사람 결재 대기, False면 자동 승인
    approved: Optional[bool]             # 승인/반려 (None=미결)
    review_comment: str                  # 반려 시 코멘트

    # --- render ---
    output_path: str                     # 최종 산출물 파일 경로(.md)
    output_pdf_path: str                 # PDF 산출물 경로(.pdf, 생성 실패 시 "")
    data_gaps_path: str                  # 데이터 갭 백로그 경로(.md, data_gap 없으면 "")
