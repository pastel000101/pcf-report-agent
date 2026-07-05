"""
main.py — 진입점(service) [그룹 5 / LLM ✗ 오케스트레이션]

역할:
  외부(API/CLI 등)에서 호출하는 단일 진입점.
  "이 식별자로, 이 종류의 리포트를 생성하라"를 받아 그래프를 실행하고 결과를 돌려준다.

입력 → 출력:
  식별자 + 산출물 종류 → 최종 산출물(경로/텍스트)

의존: graph.build_graph

주의:
  - 여기만 외부에 노출한다. 내부 노드 구조가 바뀌어도 이 시그니처는 안정적으로 유지.
  - .env 로드는 llm/llm_model.py 최상단의 load_dotenv()가 모듈 import 시 처리한다.
    (LLM 함수를 쓰려면 그 모듈을 import해야 하므로 별도 배선 불필요.)
"""

import argparse
import datetime

from graph import build_graph


def run(report_id, payload=None, output_kind="evidence_report",
        audience="제3자 검증기관", require_human_approval=False, report_name=None):
    """리포트 1건을 생성한다.

    report_id  : 식별자(데이터 조회 키)
    payload    : backend 도메인 데이터(dict). None이면 collect가 샘플 픽스처로 폴백.
    output_kind: "evidence_report" | "brief"
    audience   : 독자 (예: 제3자 검증기관 | 경영진)
    require_human_approval: True면 review에서 사람 결재 대기(HITL 배선 후).
    report_name: 산출 파일명(확장자 제외). None이면 report_id+타임스탬프로 생성한다.
                 → 이름을 여기서 확정하므로 render는 고정본/아카이브 없이 이 이름 1벌만 저장.

    반환: 최종 상태 dict (output_path, verification, editorial 등 포함).
    """
    if not report_name:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_name = f"{report_id}_{ts}"

    state = {
        "report_id": report_id,
        "report_name": report_name,
        "output_kind": output_kind,
        "audience": audience,
        "require_human_approval": require_human_approval,
    }
    if payload is not None:
        state["payload"] = payload

    return build_graph().invoke(state)


def _cli():
    p = argparse.ArgumentParser(description="ISO 14067 PCF 리포트 생성")
    p.add_argument("--report-id", type=int, default=101)
    p.add_argument("--report-name", default=None,
                   help="산출 파일명(확장자 제외). 생략 시 report_id+타임스탬프로 생성")
    p.add_argument("--output-kind", default="evidence_report",
                   choices=["evidence_report", "brief"])
    p.add_argument("--audience", default="제3자 검증기관")
    p.add_argument("--human", action="store_true", help="사람 결재 모드(HITL)")
    args = p.parse_args()

    result = run(args.report_id, output_kind=args.output_kind,
                 audience=args.audience, require_human_approval=args.human,
                 report_name=args.report_name)

    v, ed = result.get("verification"), result.get("editorial")
    print(f"verify   : passed={getattr(v, 'passed', None)} failed={getattr(v, 'failed_sections', None)}")
    print(f"editorial: passed={getattr(ed, 'passed', None)}")
    print(f"approved : {result.get('approved')}")
    print(f"output   : {result.get('output_path')}")


if __name__ == "__main__":
    _cli()
