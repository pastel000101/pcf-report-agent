"""
dispatch.py — 메인: 분배 · 섹션별 '팩트시트' 생성 [그룹 2 / LLM ✗]

역할:
  DataPack에서 각 섹션 서술에 필요한 수치만 골라, '라벨된 사실 문장(facts)'으로
  만들어 각 서브용 WorkerPackage에 담는다. 전체 목차·이전 단락 요약도 동봉한다.

왜 raw dict 덤프가 아니라 '사실 문장'인가:
  - 예전엔 result 등을 raw dict로 통째 넘겨, 비슷한 필드(scope3_upstream 296,969.78 vs
    scope3_total 298,105.20)를 worker가 어느 것을 인용할지 헷갈려 섹션 간 수치가 어긋났다
    (verify가 불일치로 반복 flag). temp로는 못 잡힘 — 둘 다 유효값이라 '선택'의 문제.
  - 코드가 '의미를 박은 문장'으로 떠먹여 주면 worker는 선택할 여지 없이 그대로 인용한다.
    혼동 소거 + 토큰 급감(표 20행 raw 덤프 제거) + verify 통과율↑. 숫자는 여전히 코드가
    DataPack에서 포맷하므로 그라운딩(원칙 D1) 유지.

입력 → 출력:
  data_pack + evidence + Outline → 섹션별 WorkerPackage 묶음(packages)

의존:
  - support.slots._num: 표 렌더와 '동일한' 숫자 포맷을 재사용 → 서술 값과 표 값이
    반올림까지 일치(드리프트 방지). (표는 어차피 코드가 렌더하므로 facts는 서술용 요약만)
"""

from collections import Counter

from support.slots import _num
from state.models import WorkerPackage


# ---------------------------------------------------------------------------
# 표준 정의 상수 — 제품 무관 고정 텍스트(LLM 창작 아님). worker가 facts로 받아 '표 없이'
# 서술로 풀어 쓴다(editorial이 반복 지적한 'DQR 등급 정의·거버넌스 용어 미설명' 대응).
# 표준이 바뀌면 여기만 수정.
# ---------------------------------------------------------------------------
DQR_GRADE_DEFS = (
    "DQR 등급 정의 — 1등급(Primary 실측): 자사 FEMS 및 협력사가 직접 측정한 위변조 없는 실측 데이터(ISO 14067/PACT 표준); "
    "2등급(Hybrid 혼합): 자사 실측값에 외부 공인 DB의 통계적 가중치·보간법을 결합해 유추한 혼합 가공 데이터(Catena-X 대응); "
    "3등급(Global Proxy): 현장 계측 불가·데이터 유실 시 ecoinvent·환경부 등에서 가져오는 보수적 문헌 대안 데이터(글로벌 규제 패널티 계수)."
)

GOVERNANCE_TERMS = (
    "거버넌스 용어·원칙 — Freeze(실적 동결): 당월 실적 검증 완료를 선언하고 데이터를 읽기전용으로 잠가 산정 엔진에 넘기는 행위; "
    "Lock(결과 박제): 다단계 승인이 끝난 최종 배출량 리포트를 무결성 해시로 영구 고정(사후 수정 불가); "
    "마감 불변의 원칙: Locked 처리된 과거 차수는 덮어쓰기 불가, 변경 시 차기 차수(Next Revision)를 생성해 재산정; "
    "HITL(Human in the Loop): 시스템은 Rule·AI로 이상치를 탐지만 하고, 최종 예외 수용·동결은 사람이 직접 수행."
)

# 감사 이벤트 유형 → 한글 라벨(주목 이벤트 요약 서술용). 없는 유형은 event_type 코드 그대로.
_AUDIT_TYPE_KO = {
    "UNMAPPED_DATA": "미매핑",
    "ROUTING_MISMATCH": "라우팅 오류",
    "ANOMALY_DETECT": "이상치",
    "NORMALIZATION": "AI 정규화 검토",
}
# 데이터 파이프라인 정본 상태(Output State) — 감사로그 status가 이 어휘를 따른다.
#   Ready→Submitted→Validating→[Pending_Review/Corrected]→Frozen→Calculated→Approved→…→Locked.
#   예외(주목) 상태 = 소명·검토 대기(Pending_Review). 정상 진행(Submitted/Validating 등)은 예외 아님.
_EXCEPTION_STATES = {"Pending_Review"}
#   최종(동결) 상태 — 이 중 하나면 산정이 확정·잠긴 것으로 본다.
_FINALIZED_STATES = {"Locked", "Frozen", "Revision_Snapshot_Created", "Approved"}


# ---------------------------------------------------------------------------
# 섹션별 팩트 빌더 — 그 섹션 worker가 '서술'하는 데 필요한 수치만 라벨 문장으로.
#   표(자재 9행·활동 20행 등)는 slots가 렌더하므로 여기엔 담지 않는다(상위 기여만).
# ---------------------------------------------------------------------------
def _facts_summary(dp):
    r = dp.result
    pu, fu = dp.meta.product_unit, dp.meta.functional_unit
    facts = [
        # FU/DU를 명시 제공 — 없으면 worker가 must_cover('기능단위(FU)·기준 단위')에
        # 맞추려 지어냄(run_trace 20260703: "기능단위는 팩당 75 kWh" 오서술 — 표의 FU=1 kWh와 모순).
        f"기능단위(Functional Unit): 1 {fu} — 헤드라인 PCF는 이 단위 기준({r.pcf_unit})으로 표기된다",
        f"기준 제품단위(Declared Unit): 1 {pu} ({pu}당 {_num(r.fu_per_unit)} {fu})",
        f"최종 PCF(헤드라인): {_num(r.final_pcf)} {r.pcf_unit}",
        f"{pu}당 PCF: {_num(r.pcf_per_unit)} kgCO₂eq/{pu} · {pu}당 {fu} {_num(r.fu_per_unit)} {fu} · 총 생산량 {_num(r.total_units)} {pu}",
        # 반복 지적된 '두 지표 환산 관계'를 facts로 명시 → worker가 계산 없이 근거 있게 서술(editorial data_gap 해소)
        f"단위 환산 관계: {pu}당 PCF({_num(r.pcf_per_unit)} kgCO₂eq/{pu})는 헤드라인 PCF({_num(r.final_pcf)} {r.pcf_unit})에 "
        f"{pu}당 {fu} 수({_num(r.fu_per_unit)} {fu})를 곱한 값이다",
        f"총 배출량: {_num(r.total_tco2eq)} tCO₂eq",
        f"Scope 1+2 합계: {_num(r.scope12_tco2eq)} tCO₂eq (전체의 {r.scope12_ratio}%)",
        f"Scope 3 전체: {_num(r.scope3_tco2eq)} tCO₂eq (전체의 {r.scope3_ratio}%)",
    ]
    facts += [f"핫스팟 {i+1}위: {h.label} {_num(h.value)} tCO₂eq ({h.share_percent}%)"
              for i, h in enumerate(dp.hotspots)]
    # 할당 방식 한 줄 요약(editorial data_gap: summary에 할당 근거 서술 부족) — processes에서 코드가 집계.
    if dp.processes:
        by_basis = {}
        for p in dp.processes:
            by_basis.setdefault(p.allocation_basis, []).append(p.process_name)
        basis_str = "; ".join(f"{', '.join(names)} — {basis}" for basis, names in by_basis.items())
        facts.append(f"할당 방식 요약(근거: {dp.meta.allocation_basis}): {basis_str}")
    return facts


def _facts_lci(dp):
    r, mb = dp.result, dp.mass_balance
    facts = [
        # 경계·할당은 _method_facts가 공통 주입 → 여기선 질량수지부터
        f"질량수지: 투입 {_num(mb.input)}{mb.unit} = 산출 {_num(mb.output)}{mb.unit} + 폐기 {_num(mb.waste)}{mb.unit}"
        f" (손실 {_num(mb.loss)}{mb.unit}), 수율 {_num(mb.yield_ratio * 100, 1)}%, 검증 {'통과' if mb.is_valid else '실패'}",
        f"원부자재(상류 물질) 생산 배출 합계: {_num(r.scope3_upstream_tco2eq)} tCO₂eq (운송·폐기물 제외)",
        f"인바운드 운송 총배출: {_num(r.logistics_total_tco2eq)} tCO₂eq",
    ]
    # 자재 표는 slots가 전부 렌더 → 서술용으로 '배출 상위 3개'만
    top_mats = sorted(dp.materials, key=lambda m: m.emission_tco2eq, reverse=True)[:3]
    facts += [f"주요 자재 배출: {m.material_name} {_num(m.emission_tco2eq)} tCO₂eq" for m in top_mats]
    # 공정 할당 기준(worker가 '왜 이렇게 할당했나'를 설명할 근거)
    facts += [f"공정 할당: {p.process_name} — {p.allocation_basis}" for p in dp.processes]
    # 할당 3층 연결(근거→방식→라인) — '할당' 단어가 근거/방식/라인 세 뜻으로 겉돌던 editorial '개념 혼용' 지적의 근원.
    shared = [p.process_name for p in dp.processes if len(p.lines) > 1]
    facts.append(
        f"할당 체계 정리: (근거) FEMS 실측 데이터를 기준으로, (방식) 각 공정을 위 공정별 방식으로 배분하고, "
        f"(라인) 여러 라인 공유 공정({', '.join(shared)})은 {dp.meta.line_name} 몫으로 분배한다"
    )
    # 라인 할당 '비율'(editorial data_gap 반복 지적: O/X만으론 실제 배분량 추적 불가) —
    #   활동별 배출 라인의 할당 전→후 수량에서 코드가 비율을 계산해 명시(worker 역산 금지, D1).
    #   에너지 활동(MWh/천m3)이 공정 할당의 대상이다(ton=자재·폐기물, t-km=운송).
    ln = dp.meta.line_name
    alloc_parts = []
    for e in dp.emission_lines:
        if e.unit in ("MWh", "천m3") and e.pre_alloc_qty:
            pct = float(e.alloc_qty) / float(e.pre_alloc_qty) * 100
            alloc_parts.append(
                f"{e.activity} {_num(e.pre_alloc_qty)} {e.unit} 중 {ln} {_num(e.alloc_qty)} {e.unit}({_num(pct, 1)}%)"
            )
    if alloc_parts:
        facts.append(f"라인 할당 비율(FEMS 실측 사용량 기준): {'; '.join(alloc_parts)}")
    # 폐기물 구성(editorial data_gap: 폐기 총량이 어디서 왔고 어떻게 처리되는지) — 질량수지 폐기량의 분해.
    waste_lines = [e for e in dp.emission_lines
                   if e.unit == "ton" and ("폐기물" in e.activity or "재활용" in e.activity)]
    if waste_lines:
        comp = " + ".join(f"{e.activity} {_num(e.pre_alloc_qty)}ton" for e in waste_lines)
        facts.append(f"폐기물 구성: 폐기 {_num(mb.waste)}{mb.unit} = {comp} (처리·배출 반영은 LCIA 섹션 담당)")
    return facts


def _facts_lcia(dp):
    r = dp.result
    facts = [
        f"총 배출량: {_num(r.total_tco2eq)} tCO₂eq",
        f"Scope 1(직접배출): {_num(r.scope1_tco2eq)} tCO₂eq",
        f"Scope 2(전력): {_num(r.scope2_tco2eq)} tCO₂eq",
        f"Scope 1+2 합계: {_num(r.scope12_tco2eq)} tCO₂eq (전체의 {r.scope12_ratio}%)",
        f"Scope 3 전체: {_num(r.scope3_tco2eq)} tCO₂eq (전체의 {r.scope3_ratio}%)"
        f" = 원부자재 {_num(r.scope3_upstream_tco2eq)} + 운송·폐기물 {_num(r.scope3_other_tco2eq)}",
    ]
    # Scope별 기여(breakdown 표가 정본) — 서술용으로 활동·배출·비율
    facts += [f"Scope 기여: [{b.scope}] {b.activity} {_num(b.total_tco2eq)} tCO₂eq ({_num(b.share_percent)}%)"
              for b in dp.breakdown]
    # 라인 분배(③) — 활동별 배출 표의 '할당 전 → {line} 할당' 열을 서술할 근거(lcia엔 할당 fact가 없었음).
    ln = dp.meta.line_name
    facts.append(
        f"라인 분배: 활동별 배출 표의 '할당 전'은 라인 배분 전(공유 라인 {', '.join(dp.meta.lines)} 합산) 값, "
        f"'{ln} 할당'은 FEMS 실측 기준 {ln} 몫이다"
    )
    # Full-BOM 그룹 구성(editorial data_gap: '기타 원부자재 그룹'이 뭘 포함하는지 표 대조 없인 모름) —
    #   최대 배출 자재(별도 행으로 분리 표기되는 핵심 자재)를 뺀 나머지 자재 목록을 코드가 나열.
    if dp.materials:
        top = max(dp.materials, key=lambda m: m.emission_tco2eq)
        others = [m.material_name for m in dp.materials if m is not top]
        if others:
            facts.append(
                f"'기타 원부자재 그룹 (Full-BOM)'의 구성: {top.material_name}을(를) 제외한 전 자재 — "
                f"{', '.join(others)} (자재별 배출량은 자재 인벤토리 표가 정본)"
            )
    # 운송·폐기물 분해(editorial data_gap: 1,135.42가 어떻게 구성되는지) — 코드가 집계값으로 분해.
    waste_em = r.scope3_other_tco2eq - r.logistics_total_tco2eq
    facts.append(
        f"'Inbound 운송 및 공정 폐기물' 분해: 인바운드 운송 {_num(r.logistics_total_tco2eq)}"
        f" + 공정 폐기물 {_num(waste_em)} = {_num(r.scope3_other_tco2eq)} tCO₂eq"
    )
    # 재활용 반출 0 처리 근거(editorial data_gap: 왜 재활용 비철금속이 배출 0인지) — Cut-off 규칙.
    if dp.flags.cutoff_applied:
        recycled = [e for e in dp.emission_lines if e.unit == "ton" and "재활용" in e.activity]
        for e in recycled:
            facts.append(
                f"재활용 반출 처리: {e.activity} {_num(e.pre_alloc_qty)}ton은 재활용 Cut-off 규칙(ISO 14067)에 따라 "
                f"배출 {_num(e.total_tco2eq)} tCO₂eq으로 처리 — 재활용 공정의 부담·편익은 본 산정 경계 밖"
            )
    return facts


def _facts_interp(dp):
    """해석(why 1) — 민감도·핫스팟·데이터 기반 분석만. DQR·감사·거버넌스는 governance로 분리."""
    r = dp.result
    facts = []
    if dp.sensitivity:
        # 드라이버(상위 배출원)별로 묶어 요약 — 변동폭도 '코드가' 계산(worker 역산 금지, D1)
        groups = {}
        for s in dp.sensitivity:
            groups.setdefault(s.parameter, []).append(s)
        for param, rows in groups.items():
            rows = sorted(rows, key=lambda s: s.delta_percent)
            lo, hi = rows[0], rows[-1]
            base = next((s for s in rows if s.delta_percent == 0), None)
            facts.append(
                f"민감도({param} {int(lo.delta_percent)}%~{int(hi.delta_percent):+d}%): "
                f"최종 PCF {_num(lo.new_pcf)} ~ {_num(hi.new_pcf)} {r.pcf_unit}"
                + (f" (기준 {_num(base.new_pcf)})" if base else "")
            )
            if base and base.new_pcf:
                dev = max(abs(hi.new_pcf - base.new_pcf), abs(base.new_pcf - lo.new_pcf)) / base.new_pcf * 100
                facts.append(f"민감도 변동폭({param}): 최종 PCF 기준 대비 약 ±{_num(dev, 2)}%")
        # 산출 방식·대상 선정 기준(editorial data_gap: 왜 이 항목만, 변동폭이 어떻게 계산됐는지) —
        #   둘 다 코드/설계가 정한 사실이므로 facts로 명시(worker 추측 차단).
        facts.append(
            "민감도 변동폭 산출 방식: ±20% 변동 시나리오의 상·하한 PCF와 기준 PCF의 최대 편차 비율로 시스템이 계산"
        )
        facts.append(
            "민감도 분석 대상 선정 기준: Scope별 최대 기여 배출원(기여도 상위 항목) — "
            + ", ".join(f"{h.label}({h.share_percent}%)" for h in dp.hotspots)
        )
    facts += [f"핫스팟: {h.label} {h.share_percent}% — {h.note}" for h in dp.hotspots]
    return facts


def _facts_governance(dp):
    """시스템 거버넌스·신뢰성 증빙(why 2) — DQR·추적성(감사로그)·거버넌스 원칙.
    LCA 산정 내용(lci/lcia)과 '분리'한다(리뷰: 어떻게 산정→무엇이→왜 신뢰). interpretation에서 이관."""
    facts = [
        f"1차 데이터 비중: {_num(dp.dqr.primary_data_ratio * 100, 0)}%"
        f" (목표 {_num(dp.dqr.target_ratio * 100, 0)}%, 미매핑 대기 {dp.dqr.unmapped_pending}건)",
        DQR_GRADE_DEFS,     # 등급 정의(고정) — 참고용, 상세 나열 말 것(아래 [서술 지침])
        GOVERNANCE_TERMS,   # 거버넌스 용어(고정) — 참고용, 상세 나열 말 것(아래 [서술 지침])
        # 위 두 정의는 '참고용'이다 — worker가 등급·용어를 하나씩 길게 풀지 않도록 명시(간결 우선).
        #   ※ [...] 지시 블록은 worker가 지시로 인식해 본문에 그대로 옮기지 않는다(feedback 블록과 동일).
        "[서술 지침] 위 'DQR 등급 정의'와 '거버넌스 용어·원칙'은 참고용 정의다. 각 등급·용어를 "
        "하나씩 상세히 풀어 나열하지 말고, 본문에 꼭 필요한 용어만 골라 간략히 언급하라(정의 재낭독 금지).",
    ]
    # 감사로그 10건 전부가 아니라 '주목할 예외 이벤트(검토 대기 = Pending_Review)'만.
    #   정본 상태 기준 판별 → 정상 진행(Submitted/Validating/Approved 등)은 자연히 제외.
    notable = [a for a in dp.audit_log if a.status in _EXCEPTION_STATES]
    # ★ WORM 로그의 상태는 '그 시점' 값 → Pending_Review가 '현재 미해결'을 뜻하지 않는다
    #   (후속 수동 승인·수정으로 해소되고 Locked로 동결됨). 산정이 동결(Locked)됐으면
    #   '탐지 후 해소됨'으로 프레이밍해야 worker가 '진행 중'으로 오해하지 않는다.
    finalized = (dp.meta.status in _FINALIZED_STATES
                 or any(a.status == "Locked" or a.event_type == "FINAL_LOCK" for a in dp.audit_log))
    if finalized:
        # 유형별 건수만 요약 문장에 접어넣는다(개별 코드·수치는 WORM 표가 정본 → 여기선 나열 안 함).
        kinds = Counter(_AUDIT_TYPE_KO.get(a.event_type, a.event_type) for a in notable)
        kinds_str = ", ".join(f"{k} {v}건" for k, v in kinds.items())
        # 주목 이벤트 요약 + 집계 기준·WORM 특성을 '하나의 사실'로 합쳐 넘긴다(worker가 한 덩어리로 서술).
        #   (editorial data_gap: 로그 표엔 이벤트가 더 많은데 왜 4건인지, Pending_Review 해소 기록이
        #    어디 있는지 — 판별 규칙 자체를 사실로 제공.)
        facts.append(
            f"감사 이력: 데이터 처리 중 주목 이벤트 총 {len(notable)}건({kinds_str})이 탐지됐으나, "
            f"담당자 수동 승인·수정으로 동결(Locked) 전 모두 해소됨 — 현재 미해결·진행 중 항목이 아니다. "
            f"이 {len(notable)}건은 감사로그 전체 {len(dp.audit_log)}건 중 예외 상태(Pending_Review)로 기록된 "
            f"건만 집계한 것이다(DATA_SYNC 등 정상 진행 이벤트는 제외). WORM 로그의 상태는 '기록 시점' 값이며, "
            f"해소는 별도 행(수동 승인·수정 이벤트)으로 추가 기록된다 — 과거 행의 상태를 덮어쓰지 않는다."
        )
    else:
        # 미동결 상태 — '처리 중'으로 (개수는 코드가 셈, D1)
        by_status = Counter(a.status for a in notable)
        facts.append(
            f"주목 감사 이벤트(처리 중): 총 {len(notable)}건"
            + (" (" + ", ".join(f"{k} {v}" for k, v in by_status.items()) + ")" if notable else "")
        )
        facts += [f"감사 이벤트: [{a.event_type}/{a.status}] {a.detail}" for a in notable]
    return facts


def _facts_conclusion(dp):
    r = dp.result
    facts = [
        f"최종 PCF: {_num(r.final_pcf)} {r.pcf_unit}",
        f"총 배출량: {_num(r.total_tco2eq)} tCO₂eq (Scope 1+2 {r.scope12_ratio}% / Scope 3 {r.scope3_ratio}%)",
        # 경계·GWP는 _method_facts가 공통 주입
        f"산정 상태: {dp.meta.status or '확정'}",
    ]
    if dp.hotspots:
        h = dp.hotspots[0]
        # 개선방향(감축 레버리지)은 검증용 문서라 배제 → '주요 배출원' 사실 제시로
        facts.append(f"주요 배출원(1위): {h.label} {_num(h.value)} tCO₂eq ({h.share_percent}%)")
    # 데이터 한계(근거 있는 한계 — 개선방향·권고 아님, 리뷰 4)
    if getattr(dp.flags, "data_maturity_proxy", False):
        facts.append(
            f"데이터 한계: 1차 데이터 {_num(dp.dqr.primary_data_ratio * 100, 0)}% 확보됐으나 "
            f"원부자재(Scope 3) 배출계수에 3등급 글로벌 Proxy가 포함돼 Scope 3의 상대 불확실성이 크다"
        )
        # 3등급 적용 범위 정량화(editorial data_gap: '일부'가 어느 자재·몇 %인지) —
        #   활동별 배출 라인의 DQR 등급에서 코드가 집계(worker 산수 금지, D1).
        g3 = [e for e in dp.emission_lines if e.dqr_grade.startswith("3")]
        if g3 and r.scope3_tco2eq:
            g3_sum = sum(e.total_tco2eq for e in g3)
            g3_pct = float(g3_sum) / float(r.scope3_tco2eq) * 100
            facts.append(
                f"3등급(Proxy·문헌) 데이터 적용 범위: 활동별 배출 중 3등급 계열 {len(g3)}개 항목 합계 "
                f"{_num(g3_sum)} tCO₂eq — Scope 3 전체({_num(r.scope3_tco2eq)} tCO₂eq)의 {_num(g3_pct, 1)}%"
            )
    return facts


def _facts_default(dp):
    r = dp.result
    return [
        f"최종 PCF: {_num(r.final_pcf)} {r.pcf_unit}",
        f"총 배출량: {_num(r.total_tco2eq)} tCO₂eq",
    ]


def _method_facts(dp):
    """모든 섹션이 공유하는 방법론 선언 — GWP·경계·할당을 '동일 표현'으로 grounding.
    일부 섹션 facts에만 있으면(예: 이전엔 GWP가 conclusion에만) GWP 없는 섹션 워커가
    근거 없이 'ISO 14067 100년 GWP' 식으로 임의 표현 → 섹션 간 불일치 → verify가 flag.
    모든 섹션에 같은 값을 주면 WORKER 규칙3('facts 표현 그대로')이 일관되게 작동한다."""
    m = dp.meta
    return [
        f"산정 경계: {m.system_boundary}",
        f"GWP 기준: {m.gwp_basis}",
        f"할당 근거: {m.allocation_basis}",
    ]


# 섹션 id → 팩트 빌더. 섹션 구성이 바뀌면(SECTION_IDS) 여기만 따라가면 된다.
FACT_BUILDERS = {
    "summary": _facts_summary,
    "lci": _facts_lci,
    "lcia": _facts_lcia,
    "interpretation": _facts_interp,
    "governance": _facts_governance,
    "conclusion": _facts_conclusion,
}


def dispatch(state):
    dp = state["data_pack"]
    outline = state["outline"]
    evidence = state.get("evidence") or {}

    packages = []
    for sp in outline.sections:
        build = FACT_BUILDERS.get(sp.id, _facts_default)
        facts = _method_facts(dp) + build(dp)      # 방법론 선언(경계·GWP·할당)을 모든 섹션 공통 주입
        packages.append(WorkerPackage(
            section_id=sp.id,
            facts=facts,                           # 라벨된 사실 문장(코드가 DataPack에서 포맷)
            evidence_slice=evidence.get(sp.id, []),
            outline=outline,           # 전체 목차(남이 뭘 맡는지 인지 → 중복방지)
            prev_summaries=[],         # 병렬이라 dispatch 시점엔 비움(중복방지는 outline 인지 + assemble이 담당)
            fewshot="",                # TODO: support.prompts.FEWSHOT_BY_SECTION[sp.id]
        ))
    return {"packages": packages}
