"""
collect.py — 데이터 수집기 · 숫자의 유일한 출처 [그룹 2 / LLM ✗ 절대금지]

역할:
  backend가 건넨 도메인 payload(JSON dict)를 받아 DataPack으로 정규화하고,
  파생값(Scope 비율·질량수지 오차·breakdown 기여%·핫스팟)을 '코드로' 계산해 채운다.

데이터 흐름:
  [진입점] backend 조회(or 샘플 JSON) → payload(dict)
        → state["payload"] 로 주입
        → collect: payload → DataPack(+파생계산)
  ※ collect는 파일/DB를 직접 읽지 않는다. '받아서 정규화'만 한다.
    backend가 생기면 진입점의 payload 출처만 API 호출로 바꾸면 된다.

입력 → 출력:
  state(payload) → {"data_pack": DataPack}

주의:
  - payload에는 raw 값만 들어온다. 비율·오차 같은 파생값은 여기서만 만든다.
  - LLM에게 산수를 시키지 않는다.
"""

import json
from decimal import Decimal
from pathlib import Path

from state.datapack import DataPack, Hotspot, SensitivityItem


def _join_key(name: str) -> str:
    """자재/운송 이름을 조인 키로 정규화. '... (부연)' 의 앞부분만 취한다.
    예: '양극 집전체 (알루미늄 박)' / '양극 집전체 (박)' → 둘 다 '양극 집전체'."""
    return name.split(" (")[0].strip()

# 샘플 payload(더미 기반) — 진입점이 backend 대신 쓸 수 있는 기본 픽스처
SAMPLE_PAYLOAD = (
    Path(__file__).resolve().parents[1] / "domi_data" / "sample_payload.json"
)


def load_sample_payload() -> dict:
    """backend가 없을 때 쓰는 샘플 payload 로더(진입점/테스트용).
    parse_float=Decimal: 소수 리터럴을 float 왕복 없이 Decimal로 정확히 파싱
    (Decimal 필드는 그대로, float 필드는 pydantic이 Decimal→float 캐스팅)."""
    with open(SAMPLE_PAYLOAD, encoding="utf-8") as f:
        return json.load(f, parse_float=Decimal)


# ===========================================================================
# 파생 계산 — payload의 raw 값에서 코드가 채우는 부분(LLM 금지)
# ===========================================================================
def _derive(dp: DataPack) -> None:
    # 타입 정책: 배출량(tCO₂eq)·계수·중량은 Decimal로 계산, 비율(%)·PCF는 float()로 캐스팅.
    #   Decimal↔float 직접 연산은 TypeError → ratio/PCF 산출 시점에만 float()로 변환한다.
    r = dp.result

    # 0) PCF 단위는 기능단위(FU)에서 파생 — meta.functional_unit이 단일 출처(라벨 드리프트 방지)
    r.pcf_unit = f"kgCO₂eq/{dp.meta.functional_unit}"

    # 1) Scope 집계(Decimal) + 비율(float)
    total = r.total_tco2eq or (      # Decimal
        r.scope1_tco2eq + r.scope2_tco2eq + r.scope3_upstream_tco2eq + r.scope3_other_tco2eq
    )
    s12 = r.scope1_tco2eq + r.scope2_tco2eq                 # Decimal
    s3 = r.scope3_upstream_tco2eq + r.scope3_other_tco2eq   # Decimal
    r.scope12_tco2eq = round(s12, 4)        # 절대 집계(서술이 인용 → LLM 산수 금지)
    r.scope3_tco2eq = round(s3, 4)
    if total:
        r.scope12_ratio = round(float(s12) / float(total) * 100, 1)   # 비율 → float
        r.scope3_ratio = round(float(s3) / float(total) * 100, 1)

    # 2) 질량수지 오차 + 수율 (float — backend MassBalanceSchema도 float)
    mb = dp.mass_balance
    mb.loss = round(mb.input - mb.output - mb.waste, 6)
    mb.gap_ratio = round(mb.loss / mb.input * 100, 2) if mb.input else 0.0
    mb.is_valid = abs(mb.gap_ratio) <= 5.0
    mb.yield_ratio = round(mb.output / mb.input, 4) if mb.input else 0.0

    # 3) breakdown 기여 비율(%) — float (total은 Decimal이라 float() 캐스팅)
    for b in dp.breakdown:
        b.share_percent = round(float(b.total_tco2eq) / float(total) * 100, 2) if total else 0.0

    # 4) 핫스팟 = 기여 상위 배출원(파생). value는 Decimal(배출량) 인용
    top = sorted(dp.breakdown, key=lambda b: b.total_tco2eq, reverse=True)[:2]
    dp.hotspots = [
        Hotspot(label=b.activity, value=b.total_tco2eq,
                share_percent=b.share_percent, note=f"{b.scope} 최대 기여")
        for b in top
    ]

    # 5) 자재 배출 (EF 조인) — emission = 투입요구량 × 통합EF (Decimal × Decimal). 기본값도 Decimal.
    ef_map = {e.ef_code: e.integrated_factor for e in dp.emission_factors}   # Decimal
    ef_src = {e.ef_code: e.source for e in dp.emission_factors}
    for m in dp.materials:
        m.ef_value = ef_map.get(m.ef_code, Decimal("0"))
        m.ef_source = ef_src.get(m.ef_code, "")
        m.emission_tco2eq = round(m.input_required_ton * m.ef_value, 4)

    # 6) 운송 t·km·배출 (materials 조인으로 투입ton 확보) — 전부 Decimal
    ton_by_mat = {_join_key(m.material_name): m.input_required_ton for m in dp.materials}
    for lg in dp.logistics:
        lg.input_ton = ton_by_mat.get(_join_key(lg.material_name), Decimal("0"))
        lg.t_km = round(lg.input_ton * lg.distance_km, 4)
        ef = ef_map.get(lg.ef_code, Decimal("0"))
        lg.emission_tco2eq = round(lg.t_km * ef, 4)   # EF_TRUCK은 톤 단위로 정규화(0.0001924)됨
    r.logistics_total_tco2eq = round(sum((lg.emission_tco2eq for lg in dp.logistics), Decimal("0")), 4)

    # 7) 민감도 — '기여 상위 배출원(hotspots)'을 ±10/20% 변동 → 총배출(Decimal)·PCF(float) 재계산
    #    ISO 14067 §6.6: 'significant inputs'의 민감도를 본다 → 최대 기여원(예: LNG 89.6%)부터.
    #    드라이버는 데이터 주도(hotspots) → 제품이 바뀌면 그 제품의 상위 배출원이 자동 선택됨.
    #    (이전엔 원부자재 7.3%만 변동 → 89.6% LNG 누락이라 검증 관점 결함. hotspots로 교정.)
    denom = r.total_units * r.fu_per_unit   # 총 기능단위 수 (PCF 분모, float) [배터리: 총 kWh]
    if denom:
        items = []
        for drv in dp.hotspots:              # 상위 기여원(LNG·NCM811 등) — value=그 배출원의 배출량
            for d in (-20, -10, 0, 10, 20):
                new_total = round(total + drv.value * (Decimal(d) / Decimal(100)), 4)   # Decimal
                new_pcf = round(float(new_total) * 1000 / denom, 4)                     # PCF → float
                items.append(SensitivityItem(
                    parameter=drv.label,
                    delta_percent=float(d),
                    new_total_tco2eq=new_total,
                    new_pcf=new_pcf,
                ))
        dp.sensitivity = items


# ===========================================================================
# 어댑터 + 노드
# ===========================================================================
def collect_from_payload(payload: dict) -> DataPack:
    """도메인 payload(dict) → DataPack(파생값 채움). collect의 핵심.

    [Numeric 경계 주의] payload의 Decimal 필드(배출량·계수·중량)는
    Decimal 또는 '문자열'로 오면 정밀도가 그대로 보존된다. float로 와도
    pydantic v2가 str(float) 경유로 변환해 통상값(≤~15자리)은 정확하지만,
    15~17자리를 넘는 고정밀 NUMERIC은 float에서 끝자리가 잘린다.
    → backend가 JSON으로 줄 때는 collect_from_json()(또는 parse_float=Decimal)을 쓸 것.
    """
    dp = DataPack.model_validate(payload)
    _derive(dp)
    return dp


def collect_from_json(json_text: str) -> DataPack:
    """backend가 JSON 문자열(HTTP 응답 본문 등)로 줄 때의 진입 어댑터.
    parse_float=Decimal로 역직렬화해 NUMERIC 정밀도를 보존한다.
    ※ requests의 resp.json()은 소수를 float로 파싱한다 → 고정밀 값 끝자리 손실.
      반드시 이 함수(또는 json.loads(text, parse_float=Decimal))를 경유할 것.
    ※ backend를 같은 프로세스에서 호출해 Pydantic 모델/Decimal dict를 직접 받는다면
      JSON을 거치지 않으므로 collect_from_payload(model.model_dump())로 충분하다."""
    return collect_from_payload(json.loads(json_text, parse_float=Decimal))


def collect(state):
    """LangGraph 노드: state['payload']를 DataPack으로 정규화해 싣는다.
    payload가 없으면 샘플 픽스처로 폴백(backend 연동 전 단계)."""
    payload = state.get("payload") or load_sample_payload()
    return {"data_pack": collect_from_payload(payload)}


if __name__ == "__main__":
    dp = collect_from_payload(load_sample_payload())
    print(dp.model_dump_json(indent=2))
