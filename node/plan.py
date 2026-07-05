"""
plan.py — 기획(Outline 확정) [그룹 2 / LLM ✗]

역할:
  산출물 종류(output_kind)에 맞는 '표준 목차'를 코드가 확정한다.

  ★ plan LLM은 폐기됨(2026-07). LLM이 [데이터 요약]만 보고 must_cover에 구체(어느 자재가
    포함/제외인지 등)를 '지어내' worker에게 시키던 것이 환각의 뿌리였다(예: 실제로 포함된
    '포장재'를 제외 항목으로 나열). 규제 문서는 구조가 일정해야 하므로 목차를 코드로 고정하고,
    구체 수치·항목은 worker가 dispatch facts([핵심 사실])에서 가져온다.
    → 결정적(테스트 가능)·일관 구조 + plan API 호출 절약.

입력 → 출력:
  output_kind → Outline (섹션 목록·목표·포함항목·톤)

주의:
  - 여기서 수치를 계산하거나 데이터를 읽지 않는다. 목차는 output_kind만으로 결정된다.
  - 새 산출물 종류(예: 경영진 브리핑)는 목차 상수를 만들어 OUTLINES에 등록하면 된다.
"""

from state.models import Outline, SectionPlan


# 산출근거서 섹션 구성 (설정 데이터). 흐름: 어떻게 산정 → 무엇이 → 왜 신뢰 → 결론
#   summary→개요 / lci→인벤토리 / lcia→결과 / interpretation→해석 / governance→거버넌스·증빙 / conclusion→결론
SECTION_IDS = ["summary", "lci", "lcia", "interpretation", "governance", "conclusion"]
OUTPUT_KINDS = ["brief", "evidence_report"]   # 경영진 브리핑 / 제3자 검증 산출근거서

# 제3자 검증 산출근거서 표준 목차 — 코드가 확정.
#   ★ must_cover는 '다룰 주제'만. 구체 수치·항목(어느 자재가 포함/제외인지 등)은 여기서 지어내지 말고,
#     worker가 [핵심 사실](dispatch facts)에서 가져온다. 순서·id는 SECTION_IDS와 일치.
EVIDENCE_REPORT_OUTLINE = [
    {"id": "summary", "title": "산정 개요 및 목적·범위",
     "goal": "산정 목적·대상·시스템 경계·기능단위를 제시한다",
     "must_cover": ["산정 목적과 대상 제품", "시스템 경계와 기능단위(FU)·기준 단위",
                    "할당 근거와 GWP 기준", "헤드라인 PCF 결과"],
     "tone": "객관·간결"},
    {"id": "lci", "title": "생명주기 인벤토리 (LCI)",
     "goal": "산정에 사용한 인벤토리 구성과 데이터 검증을 제시한다",
     "must_cover": ["주요 투입 자재와 배출계수 근거", "공정 라우팅·할당 방식",
                    "인바운드 운송", "질량수지 검증 결과의 의미"],
     "tone": "객관·간결"},
    {"id": "lcia", "title": "생명주기 영향평가 (LCIA) 결과",
     "goal": "Scope별 배출 구성과 핵심 기여 구조를 제시한다",
     "must_cover": ["Scope 1/2/3 배출 구성", "주요 배출 활동의 기여 구조"],
     "tone": "객관·간결"},
    {"id": "interpretation", "title": "결과 해석",
     "goal": "결과가 무엇에 의해 좌우되는지 데이터 기반으로 해석한다",
     "must_cover": ["결과를 지배하는 핫스팟", "민감도 분석이 보여주는 불확실성 구조"],
     "tone": "객관·해석적"},
    {"id": "governance", "title": "시스템 거버넌스·신뢰성 증빙",
     "goal": "데이터 품질·추적성·인적 검토 체계로 산정 신뢰성을 증빙한다",
     "must_cover": ["데이터 품질(DQR) 1차 데이터 비중", "감사 추적(WORM)과 예외 이벤트 처리 결과"],
     "tone": "객관·사무적"},
    {"id": "conclusion", "title": "종합 및 데이터 한계",
     "goal": "주요 배출원과 데이터 한계를 종합한다(개선 권고는 검증기관 몫이라 제외)",
     "must_cover": ["주요 배출원 요약", "근거 있는 데이터 한계", "산정 경계"],
     "tone": "객관·간결"},
]

# output_kind → 코드 목차. 새 종류는 목차 상수를 만들어 여기 등록만 하면 된다.
OUTLINES = {"evidence_report": EVIDENCE_REPORT_OUTLINE}

# 목차 드리프트 방지 — id·순서가 SECTION_IDS와 어긋나면 import 시점에 바로 잡힌다.
assert [s["id"] for s in EVIDENCE_REPORT_OUTLINE] == SECTION_IDS, "EVIDENCE_REPORT_OUTLINE id/순서가 SECTION_IDS와 불일치"


def plan(state):
    """output_kind에 맞는 표준 목차를 코드로 확정해 Outline을 만든다(LLM 없음)."""
    output_kind = state.get("output_kind", "evidence_report")
    audience = state.get("audience", "제3자 검증기관")
    template = OUTLINES.get(output_kind, EVIDENCE_REPORT_OUTLINE)   # 미정의 종류는 검증 산출근거서로 폴백
    sections = [SectionPlan(**s) for s in template]
    return {"outline": Outline(output_kind=output_kind, audience=audience, sections=sections)}
