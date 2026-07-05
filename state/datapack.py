"""
datapack.py — collect의 출력 계약(DataPack) [그룹 1 / LLM ✗ 숫자 흐름]

이 파일은 '숫자의 단일 진실 공급원(single source of truth)'의 형태를 정의한다.
  · collect(node)가 backend나 xlsx 더미에서 긁어모아 이 DataPack 하나로 정규화한다.
    (파생값·비율은 collect가 코드로 미리 계산. LLM 산수 금지.)
  · dispatch가 섹션별로 필요한 수치만 골라 '라벨된 사실 문장(facts)'으로 각 서브에 넘긴다.
  · slots(렌더러)가 표/수치 슬롯을 이 값으로 치환한다.

필드는 실제 더미(LCA 프로젝트 더미데이터_respack.xlsx) 구조에 맞춰 확정했다.
출처 매핑(시트 → 키):
  meta            ← 표지 / 1단계_사업장정보
  result          ← 완료_최종PCF대시보드 (이미 산정된 최종값)
  mass_balance    ← 3단계_활동자료입력(생산실적) / 6단계_감사로그
  materials       ← 2단계_기준정보설정(BOM 마스터)        [단위: ton]
  processes       ← 2단계_기준정보설정(공정 라우팅 BOP)
  emission_factors← 매개변수(EF/GWP/발열량 DB)
  emission_lines  ← 4단계_배출량산정 (활동별 할당·배출 결과)
  logistics       ← 2단계_기준정보설정(물류/운송 마스터)  [거리: km]
  breakdown       ← 완료_최종PCF대시보드(Scope별 drill-down)
  hotspots        ← 4단계(활성화 공회전 등) / is_hotspot
  dqr             ← 4단계 DQR 등급 + 대시보드 KPI(1차데이터 비중)
  audit_log       ← 6단계_감사로그(WORM)
  flags           ← 방어적 고지문용 플래그(04 §5)

주의(더미 현실):
  - 중량은 kg가 아니라 ton, 에너지는 MWh/천m3 단위다. 필드명·unit으로 명시한다.
  - 4단계·대시보드에 이미 다 계산돼 있다 → collect는 '읽기' 중심, 비율만 코드로 채운다.
"""

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

# 숫자 타입 정책(2026-06-26): backend(domi_data/schemas.py) 미러링.
#   Decimal = 배출량(tCO₂eq)·배출계수·계수에 곱해지는 중량 — 감사·재현성 대상.
#   float   = 비율(%)·점수·LCA 결과 PCF·질량수지 — backend도 float.
# (Decimal↔float 혼합 연산은 TypeError → collect._derive에서 ratio/PCF는 float()로 캐스팅.)


# ---------------------------------------------------------------------------
# 메타 (식별·범위·고지)
# ---------------------------------------------------------------------------
class ReportMeta(BaseModel):
    report_id: int
    product_name: str = ""                  # 예: EV-Pouch-Gen3 (Line A)
    line_name: str = ""                     # 본 제품의 생산 라인 (예: Line A) — 할당 결과 칼럼의 주체
    # 공정을 공유하는 '전체' 생산 라인 목록 — 공정 라우팅·할당 표의 열을 만든다.
    #   N개 라인 지원(반복문). 보통 line_name을 포함한다. 예: ["Line A", "Line B", "Line C"].
    #   각 ProcessItem.lines가 '그 공정이 도는 라인'을 담아 O/X를 결정한다.
    lines: list[str] = Field(default_factory=list)
    company_name: str = ""                  # 예: 가온에너지솔루션
    site_name: str = ""                     # 예: 청원 1공장
    reporting_period: str = ""              # 예: "2026-06"
    status: str = ""                        # 파이프라인 정본 상태(Output State). 최종=Locked/Frozen/Approved
    allocation_basis: str = "FEMS 실측"     # 기본 할당 근거
    gwp_basis: str = "IPCC AR2"             # GWP 기준(고지용)
    # 산정 경계 — 단일 정본. 슬롯 고지문·worker 서술이 모두 이 값을 써서 용어 통일.
    system_boundary: str = "Gate-to-Gate + Upstream Material + Inbound Transport"
    # 기능단위(FU) — 제품군에 따라 달라지는 표현을 '데이터'로 분리(배터리 전용 하드코딩 제거).
    #   functional_unit = PCF 분모 단위(kWh/kg/m² 등), product_unit = 물리 생산단위(팩/본/개 등).
    #   배터리 예: FU='kWh', 제품단위='팩', 제품단위당 FU=용량(result.fu_per_unit=75).
    #   다른 제품이면 이 두 라벨 + result.fu_per_unit만 바꾸면 템플릿·서술이 따라간다.
    functional_unit: str = "kWh"
    product_unit: str = "팩"


# ---------------------------------------------------------------------------
# 핵심 결과 (대시보드 — 이미 산정된 최종값) / 파생 비율만 collect가 채움
# ---------------------------------------------------------------------------
class ResultBlock(BaseModel):
    # LCA 결과 PCF·용량·생산량 — backend도 float (결과/카운트)
    # ※ 단위 표현은 meta.functional_unit / meta.product_unit가 정함(배터리: kWh / 팩).
    final_pcf: float = 0.0                  # 기능단위(FU)당 PCF (kgCO₂eq/FU)  ★헤드라인 [배터리: /kWh]
    pcf_per_unit: float = 0.0               # 제품단위당 PCF (kgCO₂eq/제품단위)  [배터리: 팩당]
    fu_per_unit: float = 0.0                # 제품단위당 기능단위 수            [배터리: 팩 용량(kWh)]
    target_pcf: float = 0.0                 # 목표 PCF
    total_units: float = 0.0                # 총 생산량(제품단위 수)            [배터리: Packs]

    # 절대 배출량(tCO₂eq) — 감사 대상 → Decimal (backend total_tco2eq=Decimal)
    total_tco2eq: Decimal = Decimal("0")
    scope1_tco2eq: Decimal = Decimal("0")   # 직접배출(LNG 등)
    scope2_tco2eq: Decimal = Decimal("0")   # 전력
    scope3_upstream_tco2eq: Decimal = Decimal("0")  # 원부자재
    scope3_other_tco2eq: Decimal = Decimal("0")     # 운송·폐기물

    # 파생 집계(절대값, tCO₂eq) — collect가 계산 (LLM 산수 금지) → Decimal
    scope12_tco2eq: Decimal = Decimal("0")  # scope1 + scope2
    scope3_tco2eq: Decimal = Decimal("0")   # scope3_upstream + scope3_other
    logistics_total_tco2eq: Decimal = Decimal("0")  # 운송 배출 합계(서술이 인용 → 직접 더하지 말 것)

    # 파생 비율(%) — collect가 계산 (LLM 산수 금지) → float (비율)
    scope12_ratio: float = 0.0
    scope3_ratio: float = 0.0

    pcf_unit: str = "kgCO₂eq/kWh"


# ---------------------------------------------------------------------------
# 질량수지 (LCI)
# ---------------------------------------------------------------------------
class MassBalance(BaseModel):
    input: float = 0.0                      # 총 투입량
    output: float = 0.0                     # 정상 산출량
    waste: float = 0.0                      # 폐기물량
    loss: float = 0.0                       # 손실(투입-산출-폐기)
    gap_ratio: float = 0.0                  # 오차율(%)
    is_valid: bool = True
    gap_reason: str = ""                    # 오차 소명(있으면)
    yield_ratio: float = 0.0                # 수율 = output / input (파생, collect가 채움)
    unit: str = "ton"


# ---------------------------------------------------------------------------
# 자재 인벤토리 (LCI) — 더미 BOM 마스터, 단위 ton
# ---------------------------------------------------------------------------
class MaterialItem(BaseModel):
    category: str = ""                      # 원자재 / 부자재
    material_name: str = ""                 # 예: 양극재 (NCM811)
    ef_code: str = ""                       # 배출계수 코드(EF_NCM 등)
    net_weight_ton: Decimal = Decimal("0")  # 기준 순중량(ton) — 계수에 곱해짐 → Decimal
    defect_rate: float = 0.0                # 공정 불량률(비율) → float
    input_required_ton: Decimal = Decimal("0")  # 총 투입요구량(ton, 불량률 반영) → Decimal
    recycled_ratio: Optional[float] = None  # 비율 → float
    # 파생(collect가 채움): EF 조인 + 배출 → Decimal
    ef_value: Decimal = Decimal("0")        # EF[ef_code].integrated_factor
    ef_source: str = ""                     # EF[ef_code].source (배출계수 출처)
    emission_tco2eq: Decimal = Decimal("0")  # input_required_ton × ef_value


# ---------------------------------------------------------------------------
# 공정 라우팅·할당 (LCI) — 더미 BOP 마스터
# ---------------------------------------------------------------------------
class ProcessItem(BaseModel):
    process_code: str = ""                  # PROC-1 ...
    process_name: str = ""                  # 전극 공정 ...
    allocation_basis: str = ""              # 생산 질량 비례 / 체류 시간 비례 / 100% 직접 귀속
    energy_source: str = ""                 # 공정 특성 설명(FEMS 실측 전력 연동 ...)
    lines: list[str] = Field(default_factory=list)  # 이 공정이 도는 라인 목록(예: ["Line A","Line C"])


# ---------------------------------------------------------------------------
# 배출계수 DB (매개변수 시트)
# ---------------------------------------------------------------------------
class EmissionFactor(BaseModel):
    ef_code: str = ""                       # EF_ELEC ...
    activity_name: str = ""                 # 전력 (Scope 2) ...
    source: str = ""                        # 국가 온실가스 인벤토리 ...
    unit: str = ""                          # MWh / 천m3 / ton / t·km
    co2_factor: Optional[Decimal] = None    # 배출계수 → Decimal
    ch4_factor: Optional[Decimal] = None
    n2o_factor: Optional[Decimal] = None
    integrated_factor: Decimal = Decimal("0")  # 통합 tCO₂eq 계수 → Decimal(정밀도 보존)
    logic: str = ""                         # 계산 로직 설명


# ---------------------------------------------------------------------------
# 배출량 산정 결과 (4단계) — LCIA의 알맹이, 활동별 한 줄
# ---------------------------------------------------------------------------
class EmissionLine(BaseModel):
    activity: str = ""                      # 배출활동명(할당 룰)
    scope: str = ""                         # Scope 1 | Scope 2 | Scope 3 (있으면)
    pre_alloc_qty: Decimal = Decimal("0")   # 할당 전 총 사용량 → Decimal
    alloc_qty: Decimal = Decimal("0")       # Line A 귀속 할당량 → Decimal
    unit: str = ""                          # MWh / 천m3 / ton / t-km
    ef_code: str = ""
    co2_t: Optional[Decimal] = None
    ch4_t: Optional[Decimal] = None
    n2o_t: Optional[Decimal] = None
    total_tco2eq: Decimal = Decimal("0")    # 총 배출량(tCO₂eq) → Decimal
    dqr_grade: str = ""                     # 1등급(FEMS 실측) / 2등급 / 3등급(글로벌 Proxy)
    alloc_logic: str = ""                   # 할당 로직 설명


# ---------------------------------------------------------------------------
# 운송 (LCI)
# ---------------------------------------------------------------------------
class LogisticsItem(BaseModel):
    material_name: str = ""
    origin: str = ""
    destination: str = ""
    transport_mode: str = ""                # 해운+트럭 / 25t 디젤 트럭 ...
    distance_km: Decimal = Decimal("0")     # 편도 거리(km) → Decimal (backend transport_distance_km=Decimal)
    ef_code: str = ""
    # 파생(collect가 채움): materials 조인(투입ton) + t·km + 배출 → Decimal
    input_ton: Decimal = Decimal("0")       # 조인된 투입요구량(ton)
    t_km: Decimal = Decimal("0")            # input_ton × distance_km
    emission_tco2eq: Decimal = Decimal("0")  # t_km × ef (EF_TRUCK은 톤 단위 정규화계수 0.0001924)


# ---------------------------------------------------------------------------
# Scope별 집계 (대시보드 drill-down) — LCIA 요약 표
# ---------------------------------------------------------------------------
class BreakdownItem(BaseModel):
    scope: str = ""                         # Scope 1 | Scope 2 | Scope 3 | Total
    activity: str = ""                      # 배출활동명
    total_tco2eq: Decimal = Decimal("0")    # 배출량 → Decimal
    share_percent: float = 0.0              # 기여 비율(%) — collect가 계산 → float
    alloc_logic: str = ""
    source: str = ""                        # 데이터 출처


# ---------------------------------------------------------------------------
# 해석(Interpretation)
# ---------------------------------------------------------------------------
class Hotspot(BaseModel):
    label: str = ""                         # 핫스팟 대상(공정/자재)
    value: Decimal = Decimal("0")           # 배출량(breakdown.total_tco2eq 인용) → Decimal
    share_percent: float = 0.0              # 비율 → float
    note: str = ""                          # 예: "활성화 공정 전력 공회전 반영"


class DQR(BaseModel):
    """데이터 품질(Data Quality Rating) + 대시보드 KPI."""
    primary_data_ratio: float = 0.0         # 1차 데이터(1~2등급) 비중
    target_ratio: float = 0.80              # 목표(80% 이상)
    unmapped_pending: int = 0               # 미매핑/오류 해결 대기 건수
    ai_mapping_confidence: Optional[float] = None
    ocr_confidence: Optional[float] = None


class SensitivityItem(BaseModel):
    parameter: str = ""                     # 변동 변수(예: 원부자재 Upstream 배출)
    delta_percent: float = 0.0              # 변동폭(%), 0=기준 시나리오 → float
    new_total_tco2eq: Decimal = Decimal("0")  # 변동 후 총 배출량 → Decimal
    new_pcf: float = 0.0                    # 변동 후 최종 PCF (kgCO₂eq/kWh) → float(결과)
    # ※ 더미엔 raw 없음 — collect가 ±10/20% 변동으로 파생 계산


class AuditEntry(BaseModel):
    """추적성(WORM) 한 줄 — 6단계 감사로그."""
    timestamp: str = ""
    actor: str = ""                         # 주체(User/System)
    event_type: str = ""                    # DATA_SYNC / NORMALIZATION / MASS_BALANCE ...
    detail: str = ""
    status: str = ""                        # 정본 Output State: Submitted/Validating/Pending_Review/Corrected/Frozen/Approved/Locked ...


# ---------------------------------------------------------------------------
# 방어적 고지문 플래그 (04 §5 — 코드가 고정 문구 삽입)
# ---------------------------------------------------------------------------
class Disclaimers(BaseModel):
    is_ai_generated: bool = True            # 에이전트는 서술만, 수치 미생성
    boundary_partial: bool = True           # Gate-to-Gate + Upstream, Cradle-to-Grave 아님
    data_maturity_proxy: bool = True        # 원부자재 EF 글로벌 Proxy(3등급)
    cutoff_applied: bool = True             # 재활용 Cut-off(ISO 14067) 적용
    gwp_note: str = "IPCC AR2"


# ---------------------------------------------------------------------------
# 최상위 데이터 팩 — collect의 최종 출력
# ---------------------------------------------------------------------------
class DataPack(BaseModel):
    meta: ReportMeta
    result: ResultBlock = Field(default_factory=ResultBlock)

    # LCI
    mass_balance: MassBalance = Field(default_factory=MassBalance)
    materials: list[MaterialItem] = Field(default_factory=list)
    processes: list[ProcessItem] = Field(default_factory=list)
    emission_factors: list[EmissionFactor] = Field(default_factory=list)
    logistics: list[LogisticsItem] = Field(default_factory=list)

    # LCIA
    emission_lines: list[EmissionLine] = Field(default_factory=list)
    breakdown: list[BreakdownItem] = Field(default_factory=list)

    # 해석
    hotspots: list[Hotspot] = Field(default_factory=list)
    dqr: DQR = Field(default_factory=DQR)
    sensitivity: list[SensitivityItem] = Field(default_factory=list)
    audit_log: list[AuditEntry] = Field(default_factory=list)

    # 고지
    flags: Disclaimers = Field(default_factory=Disclaimers)
