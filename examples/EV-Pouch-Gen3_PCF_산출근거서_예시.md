# EV-Pouch-Gen3 (Line A) — 제품 탄소발자국(PCF) 산출근거서

| 대상 제품 | 산정 기간 | 사업장 | 할당 근거 | GWP 기준 |
|---|---|---|---|---|
| EV-Pouch-Gen3 (Line A) | 2026-06 | 가온에너지솔루션 청원 1공장 | FEMS 실측 | IPCC AR2 |

| 최종 PCF | 팩당 PCF | 팩당 kWh | 총 생산량 | 총 배출량 |
|---:|---:|---:|---:|---:|
| **1,084.98 kgCO₂eq/kWh** | 81,373.76 kgCO₂eq/팩 | 75 kWh | 50,000 팩 | 4,068,687.82 tCO₂eq |

## 산정 개요 및 목적·범위

본 산정은 배터리 팩 제품의 제품탄소발자국(PCF)을 정량화하기 위해 수행되었다. 산정 대상은 기준 제품단위 1팩(팩당 75 kWh)이며, 총 생산량 50,000팩에 대한 배출량을 산정하였다. 시스템 경계는 Gate-to-Gate 공정(전극 제조, 파우치 조립, 활성화, 팩 조립)에 상류 원부자재 생산과 반입 운송을 포함한다. 기능단위는 1 kWh로 설정되었으며, 헤드라인 PCF는 이 단위 기준으로 표기된다. 할당은 FEMS 실측 데이터를 근거로 수행되었으며, 전극 공정과 파우치 조립은 생산 질량 비례, 활성화 공정은 체류 시간 비례, 팩 조립은 100% 직접 귀속 방식을 적용하였다. 지구온난화지수(GWP) 기준은 IPCC AR2를 사용하였다. 산정 결과 헤드라인 PCF는 1,084.98 kgCO₂eq/kWh이며, 팩당 PCF는 81,373.76 kgCO₂eq/팩이다. 총 배출량은 4,068,687.82 tCO₂eq이고, 이 중 Scope 1+2가 3,770,582.62 tCO₂eq(92.7%), Scope 3이 298,105.20 tCO₂eq(7.3%)을 차지한다. 배출의 주요 핫스팟은 LNG 직접배출 3,645,618.06 tCO₂eq(89.6%)과 핵심 양극재인 NCM811 173,250 tCO₂eq(4.26%)이다.

**산정 목적 및 범위 (Goal & Scope)**

| 항목 | 내용 |
|---|---|
| 산정 목적 | 제3자 검증기관 제출용 PCF 산출근거 제시 |
| 시스템 경계 | Gate-to-Gate + Upstream Material + Inbound Transport |
| 기능단위 (Functional Unit) | 1 kWh |
| 기준 제품단위 (Declared Unit) | 1 팩 (75 kWh/팩) |
| 할당 근거 | FEMS 실측 |
| GWP 기준 | IPCC AR2 |
| 적용 가정·제외 | 사용·폐기 단계 제외(부분 경계); 재활용 회피배출 Cut-off 제외; 일부 3등급 Proxy 계수 포함 |

## 생명주기 인벤토리 (LCI)

본 산정의 시스템 경계는 Gate-to-Gate(제조 공정) + 상류 물질 생산 + 인바운드 운송으로 설정되었으며, 온난화지수(GWP) 기준은 IPCC AR2를 적용하였다.

질량수지 검증 결과, 투입 52,631 ton은 산출 50,000 ton과 폐기 2,631 ton으로 완전히 수지되었으며(손실 0 ton), 수율 95%를 나타냈다. 폐기물은 전극 지정폐기물(소각) 400 ton과 조립 비철금속(재활용) 2,231 ton으로 구성되었다.

공정 할당은 FEMS 실측 데이터를 근거로 수행되었다. 전극 공정과 파우치 조립 공정은 생산 질량 비례로, 활성화 공정은 체류 시간 비례로, 팩 조립 공정은 100% 직접 귀속 방식으로 배분되었다. 여러 라인이 공유하는 공정(전극 공정, 파우치 조립, 활성화 공정)의 경우 FEMS 실측 사용량을 기준으로 Line A에 할당되었다. 구체적으로 전극 전력은 32,000 MWh 중 50%(16,000 MWh), 전극 LNG는 3,338 천m³ 중 50%(1,669 천m³), 조립 전력은 15,000 MWh 중 50%(7,500 MWh), 활성화 전력은 24,591 MWh 중 60%(14,754.60 MWh), 팩조립 전력은 1,200 MWh 중 100%(1,200 MWh)이 Line A에 배분되었다.

원부자재 생산 단계에서는 양극재(NCM811)가 173,250 tCO₂eq으로 가장 큰 배출 기여도를 나타냈으며, 음극 집전체(동박) 24,480 tCO₂eq, 포장재 및 기타 제조 소모품 23,283 tCO₂eq이 뒤를 이었다. 이들 상류 물질의 생산 배출 합계는 296,969.78 tCO₂eq이며, 인바운드 운송 총배출은 915.42 tCO₂eq으로 집계되었다.

### 계산에 필요한 정보 (Methodology)

**자재 인벤토리 (BOM)**

| 구분 | 자재명 | 순중량(ton) | 불량률 | 투입요구량(ton) | EF값 | 배출(tCO₂eq) | EF 출처 |
|---|---|---:|---:|---:|---:|---:|---|
| 원자재 | 양극재 (NCM811) | 11,250 | 0% | 11,250 | 15.4000 | 173,250 | Ecoinvent 3.9 (글로벌 평균) |
| 원자재 | 음극재 (천연/인조 흑연) | 8,250 | 0% | 8,250 | 1.6200 | 13,365 | Ecoinvent 3.9 (글로벌 평균) |
| 부자재 | 알루미늄 팩 하우징 | 6,300 | 0% | 6,300 | 1.9566 | 12,326.58 | 환경부 국가 LCI DB |
| 원자재 | 양극 집전체 (알루미늄 박) | 1,296 | 0% | 1,296 | 11.2000 | 14,515.20 | 환경부 국가 LCI DB |
| 원자재 | 음극 집전체 (동박) | 3,600 | 0% | 3,600 | 6.8000 | 24,480 | Ecoinvent 3.9 |
| 부자재 | 전해액 (Electrolyte) | 5,000 | 0% | 5,000 | 3.2000 | 16,000 | 협력사 제공 EPD 프록시 |
| 부자재 | 분리막 (Separator) | 2,500 | 0% | 2,500 | 2.8000 | 7,000 | Ecoinvent 3.9 |
| 부자재 | 바인더 및 도전재 | 1,500 | 0% | 1,500 | 8.5000 | 12,750 | 글로벌 화학 자재 인벤토리 |
| 부자재 | 포장재 및 기타 제조 소모품 | 12,935 | 0% | 12,935 | 1.8000 | 23,283 | 환경부 폐기물 포장 인벤토리 |
| **합계** | | | | | | **296,969.78** | |

**공정 라우팅·할당**

| 공정 | 공정명 | 할당 기준 | Line A | Line C |
|---|---|---|:---:|:---:|
| PROC-1 | 전극 공정 | 생산 질량 비례 | O | O |
| PROC-2 | 파우치 조립 | 생산 질량 비례 | O | O |
| PROC-3 | 활성화 공정 | 체류 시간 비례 | O | O |
| PROC-4 | 팩 조립 | 100% 직접 귀속 | O | X |

**업스트림 운송** — 배출 = 투입(t·km) × EF(0.0001924, 톤 단위 정규화)

| 자재 | 경로 | 수단 | 투입(t) | 거리(km) | t·km | 배출(tCO₂eq) |
|---|---|---|---:|---:|---:|---:|
| 양극재 (NCM811) | 평택항 물류 기지 → 청원 1공장 | 25t 디젤 트럭 | 11,250 | 150 | 1,687,500 | 324.68 |
| 음극재 (천연/인조 흑연) | 국내 포항 공장 → 청원 1공장 | 25t 디젤 트럭 | 8,250 | 180 | 1,485,000 | 285.71 |
| 알루미늄 팩 하우징 | 천안 압출 공장 → 청원 1공장 | 25t 디젤 트럭 | 6,300 | 60 | 378,000 | 72.73 |
| 양극 집전체 (알루미늄 박) | 사내 인근 허브 → 청원 1공장 | 5t 중형 트럭 | 1,296 | 45 | 58,320 | 11.22 |
| 음극 집전체 (동박) | 사내 인근 허브 → 청원 1공장 | 5t 중형 트럭 | 3,600 | 45 | 162,000 | 31.17 |
| 전해액 (Electrolyte) | 사내 인근 허브 → 청원 1공장 | 5t 중형 트럭 | 5,000 | 45 | 225,000 | 43.29 |
| 분리막 (Separator) | 사내 인근 허브 → 청원 1공장 | 5t 중형 트럭 | 2,500 | 45 | 112,500 | 21.64 |
| 바인더 및 도전재 | 사내 인근 허브 → 청원 1공장 | 5t 중형 트럭 | 1,500 | 45 | 67,500 | 12.99 |
| 포장재 및 기타 제조 소모품 | 사내 인근 허브 → 청원 1공장 | 5t 중형 트럭 | 12,935 | 45 | 582,075 | 111.99 |
| **합계** | | | | | | **915.42** |

**배출계수 (EF DB)**

| EF 코드 | 활동 | 출처 | 단위 | 통합계수 |
|---|---|---|---|---:|
| EF_ELEC | 전력 (Scope 2) | 국가 온실가스 인벤토리 | MWh | 3.1673 |
| EF_LNG | LNG (Scope 1) | 배출권거래제(K-ETS) 지침 | 천m3 | 2.1843 |
| EF_NCM | 양극재 (NCM811) | Ecoinvent 3.9 (글로벌 평균) | ton | 15.4000 |
| EF_ANODE | 음극재 (흑연) | Ecoinvent 3.9 (글로벌 평균) | ton | 1.6200 |
| EF_AL_PLATE | 알루미늄 팩 하우징 | 환경부 국가 LCI DB | ton | 1.9566 |
| EF_AL_FOIL | 양극 집전체 (알루미늄 박) | 환경부 국가 LCI DB | ton | 11.2000 |
| EF_COPPER_FOIL | 음극 집전체 (동박) | Ecoinvent 3.9 | ton | 6.8000 |
| EF_ELECTROLYTE | 전해액 (Electrolyte) | 협력사 제공 EPD 프록시 | ton | 3.2000 |
| EF_SEPARATOR | 분리막 (Separator) | Ecoinvent 3.9 | ton | 2.8000 |
| EF_BINDER | 바인더 및 도전재 | 글로벌 화학 자재 인벤토리 | ton | 8.5000 |
| EF_PACKAGING | 포장재 및 기타 제조 소모품 | 환경부 폐기물 포장 인벤토리 | ton | 1.8000 |
| EF_WST_1 | 지정폐기물 소각 | 환경부 국가 LCI DB | ton | 1.1000 |
| EF_WST_2 | 폐비철 재활용 | ISO 14067 Cut-off Rule | ton | 0 |
| EF_TRUCK | 트럭 운송 (t-km) | 환경부 국가 LCI DB | t·km | 0.0001924 |

### 데이터 검증 (Validation)

**질량수지 검증** — 투입 = 산출 + 폐기 정합성(LCI 데이터 유효성)

| 투입(ton) | 산출(ton) | 폐기(ton) | 손실(ton) | 수율 | 검증 |
|---:|---:|---:|---:|---:|:---:|
| 52,631 | 50,000 | 2,631 | 0 | 95% | PASS |

## 생명주기 영향평가 (LCIA) 결과

본 산정의 총 배출량은 4,068,687.82 tCO₂eq이며, Scope별 구성은 다음과 같다. Scope 1(직접배출)과 Scope 2(전력)의 합계는 3,770,582.62 tCO₂eq으로 전체의 92.7%를 차지하고, Scope 3(상류 및 운송)은 298,105.20 tCO₂eq으로 7.3%를 구성한다. 배출 구조에서 Scope 1이 지배적 역할을 하며, 그 중 LNG 직접배출이 3,645,618.06 tCO₂eq으로 전체의 89.60%를 차지한다. Scope 2 제조 전력(전극/조립/활성/팩)은 124,964.55 tCO₂eq으로 3.07%를 기여한다. Scope 3 내에서는 핵심 양극재인 NCM811이 173,250 tCO₂eq(4.26%)으로 가장 큰 기여를 하고, 기타 원부자재 그룹(음극재, 알루미늄 팩 하우징, 집전체, 전해액, 분리막, 바인더 및 도전재, 포장재 등)이 123,719.78 tCO₂eq(3.04%)를 차지한다. Inbound 운송 및 공정 폐기물은 1,135.42 tCO₂eq(0.03%)로 미미한 수준이다. 산정 경계는 Gate-to-Gate 공정에 상류 원부자재 생산과 인바운드 운송을 포함하며, GWP 기준은 IPCC AR2를 적용했다. 할당은 FEMS 실측 데이터에 기반하여 공유 라인(Line A, Line C)의 배출을 각 제품에 배분했다. 조립 공정에서 발생한 비철금속 재활용 반출물 2,231ton은 ISO 14067의 재활용 Cut-off 규칙에 따라 배출량 0 tCO₂eq으로 처리하였으며, 재활용 공정의 부담과 편익은 본 산정 경계 밖이다.

**Scope별 배출 기여**

| Scope | 배출활동 | 배출량(tCO₂eq) | 기여 비율 |
|---|---|---:|---:|
| Scope 1 | LNG (직접배출) | 3,645,618.06 | 89.60% |
| Scope 2 | 제조 전력 (전극/조립/활성/팩) | 124,964.55 | 3.07% |
| Scope 3 | 핵심 양극재 (NCM811) | 173,250 | 4.26% |
| Scope 3 | 기타 원부자재 그룹 (Full-BOM) | 123,719.78 | 3.04% |
| Scope 3 | Inbound 운송 및 공정 폐기물 | 1,135.42 | 0.03% |
| **합계** | | **4,068,687.82** | 100.00% |

**활동별 배출 산정 (LCI → LCIA)**

| 배출활동 | 할당 전 | Line A 할당 | 단위 | 배출(tCO₂eq) | DQR 등급 |
|---|---:|---:|---|---:|---|
| 전극 전력 (질량비례) | 32,000 | 16,000 | MWh | 50,676.80 | 1등급 (FEMS 실측) |
| 전극 LNG (질량비례) | 3,338 | 1,669 | 천m3 | 3,645,618.06 | 1등급 (FEMS 실측) |
| 조립 전력 (질량비례) | 15,000 | 7,500 | MWh | 23,754.75 | 1등급 (FEMS 실측) |
| 활성화 전력 (체류시간) | 24,591 | 14,754.60 | MWh | 46,732.24 | 1등급 (FEMS 실측) |
| 팩조립 전력 (전용 100%) | 1,200 | 1,200 | MWh | 3,800.76 | 1등급 (FEMS 실측) |
| 원자재-양극재 (NCM811) | 11,250 | 11,250 | ton | 173,250 | 3등급 (글로벌 Proxy) |
| 원자재-음극재 (흑연) | 8,250 | 8,250 | ton | 13,365 | 3등급 (글로벌 Proxy) |
| 부자재-알루미늄 팩 하우징 | 6,300 | 6,300 | ton | 12,326.58 | 3등급 (국가 LCI) |
| 원자재-양극 집전체 (박) | 1,296 | 1,296 | ton | 14,515.20 | 3등급 (국가 LCI) |
| 원자재-음극 집전체 (동박) | 3,600 | 3,600 | ton | 24,480 | 3등급 (글로벌 Proxy) |
| 부자재-전해액 (Electrolyte) | 5,000 | 5,000 | ton | 16,000 | 3등급 (협력사 프록시) |
| 부자재-분리막 (Separator) | 2,500 | 2,500 | ton | 7,000 | 3등급 (글로벌 Proxy) |
| 부자재-바인더 및 도전재 | 1,500 | 1,500 | ton | 12,750 | 3등급 (글로벌 Proxy) |
| 부자재-포장재 및 기타 제조 소모품 | 12,935 | 12,935 | ton | 23,283 | 3등급 (국가 LCI) |
| 전극 지정폐기물 (소각) | 400 | 200 | ton | 220 | 2등급 (하이브리드) |
| 조립 비철금속 (재활용) | 2,231 | 0 | ton | 0 | 2등급 (하이브리드) |
| 양극재 수송 물류 (t-km) | 1,687,500 | 1,687,500 | t-km | 324.68 | 2등급 (거리추산) |
| 음극재 수송 물류 (t-km) | 1,485,000 | 1,485,000 | t-km | 285.71 | 2등급 (거리추산) |
| 하우징 수송 물류 (t-km) | 378,000 | 378,000 | t-km | 72.73 | 2등급 (거리추산) |
| 기타 자재 수송 물류 (t-km) | 1,207,395 | 1,207,395 | t-km | 232.30 | 2등급 (거리추산) |
| **합계** | | | | **4,068,687.82** | |

## 결과 해석

최종 PCF는 LNG 직접배출과 핵심 양극재 두 입력에 의해 지배된다. LNG 직접배출은 전체 배출의 89.6%를 차지하며 Scope 1에서 최대 기여원이고, 핵심 양극재(NCM811)는 4.26%를 차지하며 Scope 3에서 최대 기여원이다. 민감도 분석 결과는 이 두 입력이 최종 결과의 불확실성 구조를 결정함을 보여준다. LNG 직접배출을 ±20% 변동시킬 때 최종 PCF는 890.55~1,279.42 kgCO₂eq/kWh 범위에서 기준 대비 약 ±17.92%의 변동폭을 나타낸다. 반면 핵심 양극재(NCM811)를 ±20% 변동시킬 때 최종 PCF는 1,075.74~1,094.22 kgCO₂eq/kWh 범위에서 기준 대비 약 ±0.85%의 변동폭만 나타낸다. 따라서 최종 PCF의 불확실성은 주로 LNG 직접배출 데이터의 정확성과 대표성에 의존하며, 핵심 양극재 데이터의 불확실성은 최종 결과에 미치는 영향이 상대적으로 작다.

**핵심 배출 기여원 (핫스팟)**

| 배출원 | 배출량(tCO₂eq) | 기여 비율 | 비고 |
|---|---:|---:|---|
| LNG (직접배출) | 3,645,618.06 | 89.60% | Scope 1 최대 기여 |
| 핵심 양극재 (NCM811) | 173,250 | 4.26% | Scope 3 최대 기여 |

**민감도 분석** — 기여 상위 배출원 ±10/20% 변동 → 최종 PCF (ISO 14067 §6.6)

| 시나리오 | 변동 후 총배출(tCO₂eq) | 최종 PCF(kgCO₂eq/kWh) |
|---|---:|---:|
| LNG (직접배출) -20% | 3,339,564.20 | 890.55 |
| LNG (직접배출) -10% | 3,704,126.01 | 987.77 |
| LNG (직접배출) 기준 | 4,068,687.82 | 1,084.98 |
| LNG (직접배출) +10% | 4,433,249.62 | 1,182.20 |
| LNG (직접배출) +20% | 4,797,811.43 | 1,279.42 |
| 핵심 양극재 (NCM811) -20% | 4,034,037.82 | 1,075.74 |
| 핵심 양극재 (NCM811) -10% | 4,051,362.82 | 1,080.36 |
| 핵심 양극재 (NCM811) 기준 | 4,068,687.82 | 1,084.98 |
| 핵심 양극재 (NCM811) +10% | 4,086,012.82 | 1,089.60 |
| 핵심 양극재 (NCM811) +20% | 4,103,337.82 | 1,094.22 |

## 시스템 거버넌스·신뢰성 증빙

산정 결과의 데이터 품질 관리와 감사 추적 체계는 다음과 같다. 본 산정에서 1차 데이터(자사 FEMS 및 협력사 직접 측정)의 비중은 85%로, 설정된 목표 80%를 초과했으며 미매핑 대기 항목은 0건이다. 데이터는 ISO 14067 6.3.5에서 요구하는 기술 범위, 정밀도, 완전성, 대표성, 일관성, 재현성, 출처, 불확실성 등의 품질 요건에 따라 평가되었다. 데이터 처리 과정에서 AI 정규화 검토, 미매핑, 라우팅 오류, 이상치 탐지 등 총 4건의 예외 이벤트가 감지되었으나, ISO 14067 6.4.3의 데이터 유효성 검증 절차에 따라 담당자의 수동 승인 및 수정을 거쳐 동결(Locked) 전 모두 해소되었다. 감사 로그는 WORM(Write Once Read Many) 방식으로 기록되어 과거 데이터의 사후 수정을 원천적으로 차단하며, 모든 변경 이력은 타임스탬프와 함께 추적 가능하다. 현재 미해결 또는 진행 중인 데이터 품질 항목은 없다.

**데이터 품질(DQR)**

| 1차 데이터 비중 | 목표 | 미매핑 대기 |
|---:|---:|---:|
| 85% | 80% | 0 |

**추적성 (WORM 감사로그)**

| 시각 | 주체 | 이벤트 | 내용 | 상태 |
|---|---|---|---|---|
| 2026-07-01 01:00 | System (API) | DATA_SYNC | 6월 MES 생산 실적 및 FEMS 에너지 실적 원본 수집 완료 | Submitted |
| 2026-07-01 01:05 | System (AI) | NORMALIZATION | [AI Agent] 알미늄 쪼가리 폐비철금속 재활용 (신뢰도 61% / 임계치 미달) | Pending_Review |
| 2026-07-01 01:06 | System (AI) | UNMAPPED_DATA | 신규 자재 코드(MAT-NEW-001) 감지. 기준정보 미존재로 매핑 실패. ESG 담당자 검토 요청 | Pending_Review |
| 2026-07-01 08:30 | User (EHS팀) | MANUAL_APPROVAL | 수동 확인: 폐알루미늄 재활용 및 MAT-NEW-001(신규 접착제) 매핑 확정 완료 | Approved |
| 2026-07-01 09:10 | System (Rule) | ROUTING_MISMATCH | [오류] EV 파우치 팩이 원통형 조립 라인(Line C) 실적으로 기입됨. 라우팅 테이블(BOP) 불일치 | Pending_Review |
| 2026-07-01 09:12 | User (생산팀) | MANUAL_CORRECTION | 실적 기입 오타 수정 완료 (Line C Line A). 라우팅 검증 통과 | Corrected |
| 2026-07-01 09:15 | System (Rule) | MASS_BALANCE | Line A 생산물질수지 52,631t = 50,000t + 2,631t 정합성 검증 성공 | Validating |
| 2026-07-01 09:16 | System (Rule) | ANOMALY_DETECT | 활성화 공정 전력 사용량 전월대비 +48% 과다 검출. 담당자 소명 요청 발송 | Pending_Review |
| 2026-07-01 11:20 | User (생산팀) | AUDIT_MEMO | 이상치 소명 기입: 냉각기 고장으로 인한 공회전 발생 인정 및 해당 전력 실적 동결 | Frozen |
| 2026-07-03 14:30 | User (ESG총괄) | FINAL_LOCK | 모든 할당 및 산출 완료. 최종 PCF 인증기관 제출용 스냅샷 영구 동결 | Locked |

## 종합 및 데이터 한계

본 산정은 Gate-to-Gate와 Upstream Material, Inbound Transport를 포함한 경계에서 IPCC AR2 기준 GWP로 수행되었으며, FEMS 실측값을 할당 근거로 적용했다. 최종 PCF는 1,084.98 kgCO₂eq/kWh이고, 총 배출량 4,068,687.82 tCO₂eq 중 Scope 1과 2가 92.7%를 차지하며 Scope 3는 7.3%를 차지한다. 주요 배출원은 LNG 직접배출로 3,645,618.06 tCO₂eq(89.6%)이다. 데이터 한계는 다음과 같다. 1차 데이터 확보율은 85%이나, 원부자재 배출계수에서 3등급 글로벌 Proxy 데이터가 적용되어 있다. 구체적으로 활동별 배출 중 3등급 계열 9개 항목의 합계가 296,969.78 tCO₂eq이며, 이는 Scope 3 전체 298,105.20 tCO₂eq의 99.6%에 해당한다. 따라서 Scope 3의 상대 불확실성이 크다.

## 고지

- [AI 생성] 서술 문장은 AI가 작성했으며, 수치는 시스템이 산정·삽입했습니다(에이전트는 수치를 생성·변경하지 않습니다).
- [부분 경계] 본 산정은 Gate-to-Gate + Upstream Material + Inbound Transport 범위이며, Cradle-to-Grave가 아닙니다.
- [데이터 성숙도] 원부자재 배출계수는 글로벌 Proxy(3등급)를 포함하며, 정식 검증 시 1차 데이터로 대체됩니다.
- [Cut-off] 재활용 회피 배출은 ISO 14067 Cut-off 규칙으로 제외했습니다.
- [GWP 기준] IPCC AR2.

<!-- PCF-DATAPACK v1 {"meta":{"report_id":101,"product_name":"EV-Pouch-Gen3 (Line A)","line_name":"Line A","lines":["Line A","Line C"],"company_name":"가온에너지솔루션","site_name":"청원 1공장","reporting_period":"2026-06","status":"Locked","allocation_basis":"FEMS 실측","gwp_basis":"IPCC AR2","system_boundary":"Gate-to-Gate + Upstream Material + Inbound Transport","functional_unit":"kWh","product_unit":"팩"},"result":{"final_pcf":1084.983418,"pcf_per_unit":81373.75634,"fu_per_unit":75.0,"target_pcf":0.0,"total_units":50000.0,"total_tco2eq":"4068687.817","scope1_tco2eq":"3645618.063","scope2_tco2eq":"124964.5546","scope3_upstream_tco2eq":"296969.78","scope3_other_tco2eq":"1135.418998","scope12_tco2eq":"3770582.6176","scope3_tco2eq":"298105.1990","logistics_total_tco2eq":"915.4190","scope12_ratio":92.7,"scope3_ratio":7.3,"pcf_unit":"kgCO₂eq/kWh"},"mass_balance":{"input":52631.0,"output":50000.0,"waste":2631.0,"loss":0.0,"gap_ratio":0.0,"is_valid":true,"gap_reason":"","yield_ratio":0.95,"unit":"ton"},"materials":[{"category":"원자재","material_name":"양극재 (NCM811)","ef_code":"EF_NCM","net_weight_ton":"11250","defect_rate":0.0,"input_required_ton":"11250","recycled_ratio":null,"ef_value":"15.4","ef_source":"Ecoinvent 3.9 (글로벌 평균)","emission_tco2eq":"173250.0000"},{"category":"원자재","material_name":"음극재 (천연/인조 흑연)","ef_code":"EF_ANODE","net_weight_ton":"8250","defect_rate":0.0,"input_required_ton":"8250","recycled_ratio":null,"ef_value":"1.62","ef_source":"Ecoinvent 3.9 (글로벌 평균)","emission_tco2eq":"13365.0000"},{"category":"부자재","material_name":"알루미늄 팩 하우징","ef_code":"EF_AL_PLATE","net_weight_ton":"6300","defect_rate":0.0,"input_required_ton":"6300","recycled_ratio":null,"ef_value":"1.9566","ef_source":"환경부 국가 LCI DB","emission_tco2eq":"12326.5800"},{"category":"원자재","material_name":"양극 집전체 (알루미늄 박)","ef_code":"EF_AL_FOIL","net_weight_ton":"1296","defect_rate":0.0,"input_required_ton":"1296","recycled_ratio":null,"ef_value":"11.2","ef_source":"환경부 국가 LCI DB","emission_tco2eq":"14515.2000"},{"category":"원자재","material_name":"음극 집전체 (동박)","ef_code":"EF_COPPER_FOIL","net_weight_ton":"3600","defect_rate":0.0,"input_required_ton":"3600","recycled_ratio":null,"ef_value":"6.8","ef_source":"Ecoinvent 3.9","emission_tco2eq":"24480.0000"},{"category":"부자재","material_name":"전해액 (Electrolyte)","ef_code":"EF_ELECTROLYTE","net_weight_ton":"5000","defect_rate":0.0,"input_required_ton":"5000","recycled_ratio":null,"ef_value":"3.2","ef_source":"협력사 제공 EPD 프록시","emission_tco2eq":"16000.0000"},{"category":"부자재","material_name":"분리막 (Separator)","ef_code":"EF_SEPARATOR","net_weight_ton":"2500","defect_rate":0.0,"input_required_ton":"2500","recycled_ratio":null,"ef_value":"2.8","ef_source":"Ecoinvent 3.9","emission_tco2eq":"7000.0000"},{"category":"부자재","material_name":"바인더 및 도전재","ef_code":"EF_BINDER","net_weight_ton":"1500","defect_rate":0.0,"input_required_ton":"1500","recycled_ratio":null,"ef_value":"8.5","ef_source":"글로벌 화학 자재 인벤토리","emission_tco2eq":"12750.0000"},{"category":"부자재","material_name":"포장재 및 기타 제조 소모품","ef_code":"EF_PACKAGING","net_weight_ton":"12935","defect_rate":0.0,"input_required_ton":"12935","recycled_ratio":null,"ef_value":"1.8","ef_source":"환경부 폐기물 포장 인벤토리","emission_tco2eq":"23283.0000"}],"processes":[{"process_code":"PROC-1","process_name":"전극 공정","allocation_basis":"생산 질량 비례","energy_source":"[FEMS 실측 전력 연동] 공통 공정 ➔ 생산량 기반 분배","lines":["Line A","Line C"]},{"process_code":"PROC-2","process_name":"파우치 조립","allocation_basis":"생산 질량 비례","energy_source":"[FEMS 실측 전력 연동] 공통 공정 ➔ 생산량 기반 분배","lines":["Line A","Line C"]},{"process_code":"PROC-3","process_name":"활성화 공정","allocation_basis":"체류 시간 비례","energy_source":"[FEMS 실측 전력 연동] 공통 공정 ➔ 체류시간 기반 분배","lines":["Line A","Line C"]},{"process_code":"PROC-4","process_name":"팩 조립","allocation_basis":"100% 직접 귀속","energy_source":"[FEMS 실측 전력 연동] EV 팩 전용 공정 ➔ 100% 귀속","lines":["Line A"]}],"emission_factors":[{"ef_code":"EF_ELEC","activity_name":"전력 (Scope 2)","source":"국가 온실가스 인벤토리","unit":"MWh","co2_factor":"0.4567","ch4_factor":"0.0036","n2o_factor":"0.0085","integrated_factor":"3.1673","logic":"개별가스 × GWP 합산"},{"ef_code":"EF_LNG","activity_name":"LNG (Scope 1)","source":"배출권거래제(K-ETS) 지침","unit":"천m3","co2_factor":"56100.0","ch4_factor":"1.0","n2o_factor":"0.1","integrated_factor":"2.1843128","logic":"(가스합산) × 순발열량 ÷ 1000"},{"ef_code":"EF_NCM","activity_name":"양극재 (NCM811)","source":"Ecoinvent 3.9 (글로벌 평균)","unit":"ton","co2_factor":"15.4","ch4_factor":null,"n2o_factor":null,"integrated_factor":"15.4","logic":"통합계수 직결산"},{"ef_code":"EF_ANODE","activity_name":"음극재 (흑연)","source":"Ecoinvent 3.9 (글로벌 평균)","unit":"ton","co2_factor":"1.62","ch4_factor":null,"n2o_factor":null,"integrated_factor":"1.62","logic":"통합계수 직결산"},{"ef_code":"EF_AL_PLATE","activity_name":"알루미늄 팩 하우징","source":"환경부 국가 LCI DB","unit":"ton","co2_factor":"1.9566","ch4_factor":null,"n2o_factor":null,"integrated_factor":"1.9566","logic":"통합계수 직결산"},{"ef_code":"EF_AL_FOIL","activity_name":"양극 집전체 (알루미늄 박)","source":"환경부 국가 LCI DB","unit":"ton","co2_factor":"11.2","ch4_factor":null,"n2o_factor":null,"integrated_factor":"11.2","logic":"통합계수 직결산"},{"ef_code":"EF_COPPER_FOIL","activity_name":"음극 집전체 (동박)","source":"Ecoinvent 3.9","unit":"ton","co2_factor":"6.8","ch4_factor":null,"n2o_factor":null,"integrated_factor":"6.8","logic":"통합계수 직결산"},{"ef_code":"EF_ELECTROLYTE","activity_name":"전해액 (Electrolyte)","source":"협력사 제공 EPD 프록시","unit":"ton","co2_factor":"3.2","ch4_factor":null,"n2o_factor":null,"integrated_factor":"3.2","logic":"통합계수 직결산"},{"ef_code":"EF_SEPARATOR","activity_name":"분리막 (Separator)","source":"Ecoinvent 3.9","unit":"ton","co2_factor":"2.8","ch4_factor":null,"n2o_factor":null,"integrated_factor":"2.8","logic":"통합계수 직결산"},{"ef_code":"EF_BINDER","activity_name":"바인더 및 도전재","source":"글로벌 화학 자재 인벤토리","unit":"ton","co2_factor":"8.5","ch4_factor":null,"n2o_factor":null,"integrated_factor":"8.5","logic":"통합계수 직결산"},{"ef_code":"EF_PACKAGING","activity_name":"포장재 및 기타 제조 소모품","source":"환경부 폐기물 포장 인벤토리","unit":"ton","co2_factor":"1.8","ch4_factor":null,"n2o_factor":null,"integrated_factor":"1.8","logic":"통합계수 직결산"},{"ef_code":"EF_WST_1","activity_name":"지정폐기물 소각","source":"환경부 국가 LCI DB","unit":"ton","co2_factor":"1.1","ch4_factor":null,"n2o_factor":null,"integrated_factor":"1.1","logic":"통합계수 직결산"},{"ef_code":"EF_WST_2","activity_name":"폐비철 재활용","source":"ISO 14067 Cut-off Rule","unit":"ton","co2_factor":"0.0","ch4_factor":null,"n2o_factor":null,"integrated_factor":"0","logic":"Cut-off (Zero 처리)"},{"ef_code":"EF_TRUCK","activity_name":"트럭 운송 (t-km)","source":"환경부 국가 LCI DB","unit":"t·km","co2_factor":"0.0001924","ch4_factor":"0","n2o_factor":"0","integrated_factor":"0.0001924","logic":"(0.1924 kg ÷ 1000) 톤 단위 정규화 → 배출량 = t·km × 0.0001924 = tCO2eq"}],"logistics":[{"material_name":"양극재 (NCM811)","origin":"평택항 물류 기지","destination":"청원 1공장","transport_mode":"25t 디젤 트럭","distance_km":"150","ef_code":"EF_TRUCK","input_ton":"11250","t_km":"1687500.0000","emission_tco2eq":"324.6750"},{"material_name":"음극재 (천연/인조 흑연)","origin":"국내 포항 공장","destination":"청원 1공장","transport_mode":"25t 디젤 트럭","distance_km":"180","ef_code":"EF_TRUCK","input_ton":"8250","t_km":"1485000.0000","emission_tco2eq":"285.7140"},{"material_name":"알루미늄 팩 하우징","origin":"천안 압출 공장","destination":"청원 1공장","transport_mode":"25t 디젤 트럭","distance_km":"60","ef_code":"EF_TRUCK","input_ton":"6300","t_km":"378000.0000","emission_tco2eq":"72.7272"},{"material_name":"양극 집전체 (알루미늄 박)","origin":"사내 인근 허브","destination":"청원 1공장","transport_mode":"5t 중형 트럭","distance_km":"45","ef_code":"EF_TRUCK","input_ton":"1296","t_km":"58320.0000","emission_tco2eq":"11.2208"},{"material_name":"음극 집전체 (동박)","origin":"사내 인근 허브","destination":"청원 1공장","transport_mode":"5t 중형 트럭","distance_km":"45","ef_code":"EF_TRUCK","input_ton":"3600","t_km":"162000.0000","emission_tco2eq":"31.1688"},{"material_name":"전해액 (Electrolyte)","origin":"사내 인근 허브","destination":"청원 1공장","transport_mode":"5t 중형 트럭","distance_km":"45","ef_code":"EF_TRUCK","input_ton":"5000","t_km":"225000.0000","emission_tco2eq":"43.2900"},{"material_name":"분리막 (Separator)","origin":"사내 인근 허브","destination":"청원 1공장","transport_mode":"5t 중형 트럭","distance_km":"45","ef_code":"EF_TRUCK","input_ton":"2500","t_km":"112500.0000","emission_tco2eq":"21.6450"},{"material_name":"바인더 및 도전재","origin":"사내 인근 허브","destination":"청원 1공장","transport_mode":"5t 중형 트럭","distance_km":"45","ef_code":"EF_TRUCK","input_ton":"1500","t_km":"67500.0000","emission_tco2eq":"12.9870"},{"material_name":"포장재 및 기타 제조 소모품","origin":"사내 인근 허브","destination":"청원 1공장","transport_mode":"5t 중형 트럭","distance_km":"45","ef_code":"EF_TRUCK","input_ton":"12935","t_km":"582075.0000","emission_tco2eq":"111.9912"}],"emission_lines":[{"activity":"전극 전력 (질량비례)","scope":"","pre_alloc_qty":"32000","alloc_qty":"16000","unit":"MWh","ef_code":"EF_ELEC","co2_t":"7307.2","ch4_t":"57.6","n2o_t":"136","total_tco2eq":"50676.8","dqr_grade":"1등급 (FEMS 실측)","alloc_logic":"FEMS × 생산 질량 비중"},{"activity":"전극 LNG (질량비례)","scope":"","pre_alloc_qty":"3338","alloc_qty":"1669","unit":"천m3","ef_code":"EF_LNG","co2_t":null,"ch4_t":null,"n2o_t":null,"total_tco2eq":"3645618.063","dqr_grade":"1등급 (FEMS 실측)","alloc_logic":"FEMS × 통합계수 1000배 보정"},{"activity":"조립 전력 (질량비례)","scope":"","pre_alloc_qty":"15000","alloc_qty":"7500","unit":"MWh","ef_code":"EF_ELEC","co2_t":"3425.25","ch4_t":"27","n2o_t":"63.75","total_tco2eq":"23754.75","dqr_grade":"1등급 (FEMS 실측)","alloc_logic":"FEMS × 생산 질량 비중"},{"activity":"활성화 전력 (체류시간)","scope":"","pre_alloc_qty":"24591","alloc_qty":"14754.6","unit":"MWh","ef_code":"EF_ELEC","co2_t":"6738.42582","ch4_t":"53.11656","n2o_t":"125.4141","total_tco2eq":"46732.24458","dqr_grade":"1등급 (FEMS 실측)","alloc_logic":"FEMS × 체류 시간 비중"},{"activity":"팩조립 전력 (전용 100%)","scope":"","pre_alloc_qty":"1200","alloc_qty":"1200","unit":"MWh","ef_code":"EF_ELEC","co2_t":"548.04","ch4_t":"4.32","n2o_t":"10.2","total_tco2eq":"3800.76","dqr_grade":"1등급 (FEMS 실측)","alloc_logic":"FEMS × 100% 직접 귀속"},{"activity":"원자재-양극재 (NCM811)","scope":"","pre_alloc_qty":"11250","alloc_qty":"11250","unit":"ton","ef_code":"EF_NCM","co2_t":null,"ch4_t":null,"n2o_t":null,"total_tco2eq":"173250","dqr_grade":"3등급 (글로벌 Proxy)","alloc_logic":"BOM 총 투입요구량 직결산"},{"activity":"원자재-음극재 (흑연)","scope":"","pre_alloc_qty":"8250","alloc_qty":"8250","unit":"ton","ef_code":"EF_ANODE","co2_t":null,"ch4_t":null,"n2o_t":null,"total_tco2eq":"13365","dqr_grade":"3등급 (글로벌 Proxy)","alloc_logic":"BOM 총 투입요구량 직결산"},{"activity":"부자재-알루미늄 팩 하우징","scope":"","pre_alloc_qty":"6300","alloc_qty":"6300","unit":"ton","ef_code":"EF_AL_PLATE","co2_t":null,"ch4_t":null,"n2o_t":null,"total_tco2eq":"12326.58","dqr_grade":"3등급 (국가 LCI)","alloc_logic":"BOM 총 투입요구량 직결산"},{"activity":"원자재-양극 집전체 (박)","scope":"","pre_alloc_qty":"1296","alloc_qty":"1296","unit":"ton","ef_code":"EF_AL_FOIL","co2_t":null,"ch4_t":null,"n2o_t":null,"total_tco2eq":"14515.2","dqr_grade":"3등급 (국가 LCI)","alloc_logic":"BOM 총 투입요구량 직결산"},{"activity":"원자재-음극 집전체 (동박)","scope":"","pre_alloc_qty":"3600","alloc_qty":"3600","unit":"ton","ef_code":"EF_COPPER_FOIL","co2_t":null,"ch4_t":null,"n2o_t":null,"total_tco2eq":"24480","dqr_grade":"3등급 (글로벌 Proxy)","alloc_logic":"BOM 총 투입요구량 직결산"},{"activity":"부자재-전해액 (Electrolyte)","scope":"","pre_alloc_qty":"5000","alloc_qty":"5000","unit":"ton","ef_code":"EF_ELECTROLYTE","co2_t":null,"ch4_t":null,"n2o_t":null,"total_tco2eq":"16000","dqr_grade":"3등급 (협력사 프록시)","alloc_logic":"BOM 총 투입요구량 직결산"},{"activity":"부자재-분리막 (Separator)","scope":"","pre_alloc_qty":"2500","alloc_qty":"2500","unit":"ton","ef_code":"EF_SEPARATOR","co2_t":null,"ch4_t":null,"n2o_t":null,"total_tco2eq":"7000","dqr_grade":"3등급 (글로벌 Proxy)","alloc_logic":"BOM 총 투입요구량 직결산"},{"activity":"부자재-바인더 및 도전재","scope":"","pre_alloc_qty":"1500","alloc_qty":"1500","unit":"ton","ef_code":"EF_BINDER","co2_t":null,"ch4_t":null,"n2o_t":null,"total_tco2eq":"12750","dqr_grade":"3등급 (글로벌 Proxy)","alloc_logic":"BOM 총 투입요구량 직결산"},{"activity":"부자재-포장재 및 기타 제조 소모품","scope":"","pre_alloc_qty":"12935","alloc_qty":"12935","unit":"ton","ef_code":"EF_PACKAGING","co2_t":null,"ch4_t":null,"n2o_t":null,"total_tco2eq":"23283","dqr_grade":"3등급 (국가 LCI)","alloc_logic":"BOM 총 투입요구량 직결산"},{"activity":"전극 지정폐기물 (소각)","scope":"","pre_alloc_qty":"400","alloc_qty":"200","unit":"ton","ef_code":"EF_WST_1","co2_t":null,"ch4_t":null,"n2o_t":null,"total_tco2eq":"220","dqr_grade":"2등급 (하이브리드)","alloc_logic":"발생량 × 생산 질량 비중"},{"activity":"조립 비철금속 (재활용)","scope":"","pre_alloc_qty":"2231","alloc_qty":"0","unit":"ton","ef_code":"EF_WST_2","co2_t":"0","ch4_t":null,"n2o_t":null,"total_tco2eq":"0","dqr_grade":"2등급 (하이브리드)","alloc_logic":"재활용 회피 배출 제외 (Cut-off)"},{"activity":"양극재 수송 물류 (t-km)","scope":"","pre_alloc_qty":"1687500","alloc_qty":"1687500","unit":"t-km","ef_code":"EF_TRUCK","co2_t":"324.675","ch4_t":"0","n2o_t":"0","total_tco2eq":"324.675","dqr_grade":"2등급 (거리추산)","alloc_logic":"투입량 × 물류 대표 거리"},{"activity":"음극재 수송 물류 (t-km)","scope":"","pre_alloc_qty":"1485000","alloc_qty":"1485000","unit":"t-km","ef_code":"EF_TRUCK","co2_t":"285.714","ch4_t":"0","n2o_t":"0","total_tco2eq":"285.714","dqr_grade":"2등급 (거리추산)","alloc_logic":"투입량 × 물류 대표 거리"},{"activity":"하우징 수송 물류 (t-km)","scope":"","pre_alloc_qty":"378000","alloc_qty":"378000","unit":"t-km","ef_code":"EF_TRUCK","co2_t":"72.7272","ch4_t":"0","n2o_t":"0","total_tco2eq":"72.7272","dqr_grade":"2등급 (거리추산)","alloc_logic":"투입량 × 물류 대표 거리"},{"activity":"기타 자재 수송 물류 (t-km)","scope":"","pre_alloc_qty":"1207395","alloc_qty":"1207395","unit":"t-km","ef_code":"EF_TRUCK","co2_t":"232.302798","ch4_t":"0","n2o_t":"0","total_tco2eq":"232.302798","dqr_grade":"2등급 (거리추산)","alloc_logic":"기타 자재합산 × 대표 거리"}],"breakdown":[{"scope":"Scope 1","activity":"LNG (직접배출)","total_tco2eq":"3645618.063","share_percent":89.6,"alloc_logic":"FEMS 실측 × 생산 질량 비중","source":"배출권거래제(K-ETS) 지침"},{"scope":"Scope 2","activity":"제조 전력 (전극/조립/활성/팩)","total_tco2eq":"124964.5546","share_percent":3.07,"alloc_logic":"FEMS 실측 기반 공정별 다중 할당 엔진 가동","source":"국가 온실가스 인벤토리"},{"scope":"Scope 3","activity":"핵심 양극재 (NCM811)","total_tco2eq":"173250","share_percent":4.26,"alloc_logic":"BOM 총 투입요구량 직결산 (무결성 연동)","source":"Ecoinvent 3.9 (글로벌 평균)"},{"scope":"Scope 3","activity":"기타 원부자재 그룹 (Full-BOM)","total_tco2eq":"123719.78","share_percent":3.04,"alloc_logic":"Full-BOM 마스터 기반 연산 파이프라인","source":"국가 LCI DB / 협력사 EPD 프록시"},{"scope":"Scope 3","activity":"Inbound 운송 및 공정 폐기물","total_tco2eq":"1135.418998","share_percent":0.03,"alloc_logic":"물류 대표 거리 추산 및 Cut-off 가동","source":"환경부 LCI DB / ISO 표준 규격"}],"hotspots":[{"label":"LNG (직접배출)","value":"3645618.063","share_percent":89.6,"note":"Scope 1 최대 기여"},{"label":"핵심 양극재 (NCM811)","value":"173250","share_percent":4.26,"note":"Scope 3 최대 기여"}],"dqr":{"primary_data_ratio":0.85,"target_ratio":0.8,"unmapped_pending":0,"ai_mapping_confidence":null,"ocr_confidence":null},"sensitivity":[{"parameter":"LNG (직접배출)","delta_percent":-20.0,"new_total_tco2eq":"3339564.2044","new_pcf":890.5505},{"parameter":"LNG (직접배출)","delta_percent":-10.0,"new_total_tco2eq":"3704126.0107","new_pcf":987.7669},{"parameter":"LNG (직접배출)","delta_percent":0.0,"new_total_tco2eq":"4068687.8170","new_pcf":1084.9834},{"parameter":"LNG (직접배출)","delta_percent":10.0,"new_total_tco2eq":"4433249.6233","new_pcf":1182.1999},{"parameter":"LNG (직접배출)","delta_percent":20.0,"new_total_tco2eq":"4797811.4296","new_pcf":1279.4164},{"parameter":"핵심 양극재 (NCM811)","delta_percent":-20.0,"new_total_tco2eq":"4034037.8170","new_pcf":1075.7434},{"parameter":"핵심 양극재 (NCM811)","delta_percent":-10.0,"new_total_tco2eq":"4051362.8170","new_pcf":1080.3634},{"parameter":"핵심 양극재 (NCM811)","delta_percent":0.0,"new_total_tco2eq":"4068687.8170","new_pcf":1084.9834},{"parameter":"핵심 양극재 (NCM811)","delta_percent":10.0,"new_total_tco2eq":"4086012.8170","new_pcf":1089.6034},{"parameter":"핵심 양극재 (NCM811)","delta_percent":20.0,"new_total_tco2eq":"4103337.8170","new_pcf":1094.2234}],"audit_log":[{"timestamp":"2026-07-01 01:00","actor":"System (API)","event_type":"DATA_SYNC","detail":"6월 MES 생산 실적 및 FEMS 에너지 실적 원본 수집 완료","status":"Submitted"},{"timestamp":"2026-07-01 01:05","actor":"System (AI)","event_type":"NORMALIZATION","detail":"[AI Agent] 알미늄 쪼가리 ➔ 폐비철금속 재활용 (신뢰도 61% / 임계치 미달)","status":"Pending_Review"},{"timestamp":"2026-07-01 01:06","actor":"System (AI)","event_type":"UNMAPPED_DATA","detail":"신규 자재 코드(MAT-NEW-001) 감지. 기준정보 미존재로 매핑 실패. ESG 담당자 검토 요청","status":"Pending_Review"},{"timestamp":"2026-07-01 08:30","actor":"User (EHS팀)","event_type":"MANUAL_APPROVAL","detail":"수동 확인: 폐알루미늄 재활용 및 MAT-NEW-001(신규 접착제) 매핑 확정 완료","status":"Approved"},{"timestamp":"2026-07-01 09:10","actor":"System (Rule)","event_type":"ROUTING_MISMATCH","detail":"[오류] EV 파우치 팩이 원통형 조립 라인(Line C) 실적으로 기입됨. 라우팅 테이블(BOP) 불일치","status":"Pending_Review"},{"timestamp":"2026-07-01 09:12","actor":"User (생산팀)","event_type":"MANUAL_CORRECTION","detail":"실적 기입 오타 수정 완료 (Line C ➔ Line A). 라우팅 검증 통과","status":"Corrected"},{"timestamp":"2026-07-01 09:15","actor":"System (Rule)","event_type":"MASS_BALANCE","detail":"Line A 생산물질수지 52,631t = 50,000t + 2,631t 정합성 검증 성공","status":"Validating"},{"timestamp":"2026-07-01 09:16","actor":"System (Rule)","event_type":"ANOMALY_DETECT","detail":"활성화 공정 전력 사용량 전월대비 +48% 과다 검출. 담당자 소명 요청 발송","status":"Pending_Review"},{"timestamp":"2026-07-01 11:20","actor":"User (생산팀)","event_type":"AUDIT_MEMO","detail":"이상치 소명 기입: 냉각기 고장으로 인한 공회전 발생 인정 및 해당 전력 실적 동결","status":"Frozen"},{"timestamp":"2026-07-03 14:30","actor":"User (ESG총괄)","event_type":"FINAL_LOCK","detail":"모든 할당 및 산출 완료. 최종 PCF 인증기관 제출용 스냅샷 영구 동결","status":"Locked"}],"flags":{"is_ai_generated":true,"boundary_partial":true,"data_maturity_proxy":true,"cutoff_applied":true,"gwp_note":"IPCC AR2"}} -->
