"""
models.py — 구조화 출력 스키마 모음 [그룹 1 / LLM ✗(이 스키마가 LLM 출력 형식이 됨)]

가장 바닥 계층(의존 없음). 파이프라인이 주고받는 '자료의 형태'를 정의한다.
필드 정의는 계획 문서 02(에이전트 명세)·04(산출물 구조)를 따른다.
"""

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 기획(plan)이 만드는 스키마
#   ※ 섹션 구성 상수(SECTION_IDS/OUTPUT_KINDS/EVIDENCE_REPORT_OUTLINE)는 스키마가 아니라
#     plan의 설정 데이터 → node/plan.py로 이관(models는 순수 스키마만).
# ---------------------------------------------------------------------------
class SectionPlan(BaseModel):
    """한 섹션의 기획 단위 — 무엇을, 어떤 톤으로 쓸지."""
    id: str = Field(description="섹션 ID (summary|lci|lcia|interpretation|governance|conclusion — 정본은 node/plan.py SECTION_IDS)")
    title: str = Field(description="섹션 제목")
    goal: str = Field(description="이 단락이 달성할 목표 한 줄")
    must_cover: list[str] = Field(default_factory=list, description="반드시 포함할 포인트(핫스팟 등)")
    tone: str = Field(description='톤. 예: "객관·간결" | "경영진 요약체"')


class Outline(BaseModel):
    """기획 결과 — 산출물 종류 + 독자 + 섹션 목록."""
    output_kind: str = Field(description="brief | evidence_report")
    audience: str = Field(description="독자. 예: 경영진 | 제3자 검증기관")
    sections: list[SectionPlan] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 편집(assemble)이 만드는 스키마
# ---------------------------------------------------------------------------
class EditedSection(BaseModel):
    """편집된 섹션 서술 — 새 사실/숫자 추가 없이 연결·톤·중복만 손본 결과."""
    id: str = Field(description="섹션 ID(입력 그대로 유지)")
    narrative: str = Field(description="편집된 서술. 숫자는 절대 바꾸지 않는다")


class EditedReport(BaseModel):
    """편집장이 다듬은 섹션 묶음."""
    sections: list[EditedSection] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 분배(dispatch)가 만드는 스키마 — 메인이 서브에게 넘기는 1인분 패키지
# (코드가 조립한다. LLM 출력 아님.)
# ---------------------------------------------------------------------------
class WorkerPackage(BaseModel):
    """서브 1명에게 넘기는 작업 패키지. '담당 조각'만 담아 토큰을 아끼고 중복을 막는다."""
    section_id: str = Field(description="담당 섹션 ID")
    facts: list[str] = Field(default_factory=list,
                             description="이 섹션 서술에 필요한 수치를 라벨된 사실 문장으로(코드가 DataPack에서 포맷)")
    evidence_slice: list[str] = Field(default_factory=list, description="RAG 결과 중 이 섹션 주제 청크만")
    outline: Outline = Field(description="전체 목차 — 남이 뭘 맡는지 인지(중복 방지)")
    prev_summaries: list[str] = Field(default_factory=list, description="앞 단락들의 요약(중복 방지)")
    fewshot: str = Field(default="", description="이 섹션의 모범 작성 예시(Few-shot)")
    feedback: list[str] = Field(default_factory=list,
                                description="재작성 시 verify/editorial이 지적한 내용(최초 작성 땐 빈 리스트)")


# ---------------------------------------------------------------------------
# 서브(worker)가 만드는 스키마
# ---------------------------------------------------------------------------
class SectionDraft(BaseModel):
    """서브의 산출 — 서술만(표/수치 슬롯 미포함)."""
    id: str = Field(description="섹션 ID")
    title: str = Field(description="섹션 제목")
    narrative: str = Field(description="서술 문장만. 표/수치 슬롯은 포함하지 않는다")
    summary: str = Field(description="한 줄 요약 ★ 다음 서브에게 prev_summaries로 전달")
    citations: list[str] = Field(default_factory=list, description="인용한 ISO 조항/표준")
    numbers_used: list[str] = Field(default_factory=list, description="서술에서 언급한 모든 숫자(검증용)")


# ---------------------------------------------------------------------------
# 검증(verify)이 만드는 스키마
# ---------------------------------------------------------------------------
class SectionIssue(BaseModel):
    """검증에서 발견한 섹션별 문제 하나."""
    section_id: str = Field(description="문제가 난 섹션 ID")
    kind: str = Field(description='문제 종류. 예: "number_mismatch" | "unfaithful"')
    detail: str = Field(description="구체 설명(어떤 숫자/주장이 문제인지)")
    quote: str = Field(default="",
                       description="문제가 된 문구를 해당 섹션 [서술] 원문에서 '글자 그대로' 복사한 인용. "
                                   'kind="unfaithful"이면 필수 — 코드가 실제 서술과 대조해 없으면 이슈를 폐기한다(환각 지적 차단)')


class Verification(BaseModel):
    """검증 결과 — 통과 여부 + 실패 섹션 + 이슈 목록."""
    passed: bool = Field(description="전체 통과 여부")
    failed_sections: list[str] = Field(default_factory=list, description="재작성이 필요한 섹션 ID들")
    issues: list[SectionIssue] = Field(default_factory=list)


class GraderOutput(BaseModel):
    """충실성 grader(LLM)의 출력 — 데이터에 충실하지 않은 부분만 이슈로."""
    issues: list[SectionIssue] = Field(default_factory=list,
                                       description="서술이 데이터·근거에 어긋나는 부분")


# ---------------------------------------------------------------------------
# 편집장(editorial_review)이 만드는 스키마 — verify와 다른 층(편집 관점)
# ---------------------------------------------------------------------------
class EditorialIssue(BaseModel):
    """편집장이 찾은 문제 하나. kind가 '어디서 고칠지(또는 못 고치는지)'를 정한다."""
    section_id: str = Field(description='문제 섹션 ID. 전체 문제면 "global"')
    kind: str = Field(description='"content"=서술 보강으로 고침(재작성) | "flow"=흐름·톤·중복(재편집) | "data_gap"=데이터가 없어 서술로 못 고침(재작성 안 함)')
    detail: str = Field(description="무엇이 왜 문제인지 — 2문장 이내(장황 금지)")
    fix_source: str = Field(default="",
                            description='kind="content"이면 필수: 작성자가 이 보강에 쓸 정보가 이미 있는 곳'
                                        "(보고서 초안)의 원문을 '글자 그대로' 인용. "
                                        "코드가 초안과 대조해 확인되지 않으면 data_gap으로 강등한다(재작성 안 함)")


class EditorialReview(BaseModel):
    """편집장 평가 결과 — 완결성·흐름·가독성 관점(숫자는 안 봄)."""
    passed: bool = Field(description="보고서로서 내보낼 만한가")
    issues: list[EditorialIssue] = Field(default_factory=list)
