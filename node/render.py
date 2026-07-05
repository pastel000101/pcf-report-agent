"""
render.py — 출력 [그룹 2 / LLM ✗]

역할:
  최종 초안을 파일로 저장. Markdown(.md)과 PDF(.pdf)를 '병행' 산출한다.
  - .md  : 기존 그대로(항상 저장).
  - .pdf : pdf 패키지(md_to_pdf)로 변환. 실패해도 .md는 남는다(병행 산출의 안전망).

  저장 전략(명명): 리포트 이름(report_name) 1벌만 산출 — latest 고정본/archive 이중 산출 폐지.
  - output/{report_name}.{md,pdf}
  - report_name은 진입점(main)이 정한다: 외부가 넘긴 이름을 쓰거나, 없으면 main이 생성.
    → 생성 시 타임스탬프가 붙어 이름이 겹치지 않으므로 별도 아카이브가 불필요.
    ※ 안전망: report_name이 상태에 없으면 여기서 meta 기반 stem으로 폴백.

입력 → 출력:
  draft_md(Markdown) → output_path(.md) + output_pdf_path(.pdf)

의존: pdf.md_to_pdf (격리된 PDF 엔진 — 교체 시 그 패키지만 수정)

주의:
  - PDF는 WeasyPrint + 동봉 폰트(Pretendard). Windows는 GTK 런타임 필요(pdf/to_pdf.py 참고).
  - PDF 생성 실패는 치명적이지 않다 → 경고만 남기고 .md 경로는 정상 반환.
"""

import datetime
import re
from pathlib import Path

from pdf import embed_datapack, md_to_pdf

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"


def _slug(s):
    """파일명에 쓸 수 있게 정리(공백→_, 금지문자 제거)."""
    s = re.sub(r"[\\/:*?\"<>|]", "", str(s)).strip()
    return re.sub(r"\s+", "_", s) or "report"


def _write_data_gaps(state, stem):
    """편집장(editorial)이 data_gap으로 분류한 지적을 백로그 파일로 산출한다.

    data_gap = '보고서에 없는 데이터가 있어야 고쳐지는 문제' → 서술 재작성으로는 해결 불가.
    이 목록은 다음 차수에서 collect/dispatch의 facts를 확장할 '후보'다.
    ※ LLM이 만든 지적이라 품질이 들쭉날쭉하다 — 자동 반영하지 말고 사람이 취사선택한다.
    ※ data_gap_log = editorial '전 라운드' 지적의 누적(2026-07-04). 라운드마다 지적이 달라
      마지막 라운드만 기록하면 이전 라운드분이 유실됐다 → reducer로 누적해 전부 남긴다.
      (로그가 없는 구버전 상태면 마지막 라운드(state.editorial)로 폴백.)
    """
    by_sec = dict(state.get("data_gap_log") or {})
    if not by_sec:
        ed = state.get("editorial")
        for i in (ed.issues if ed else []):
            if i.kind == "data_gap":
                by_sec.setdefault(i.section_id, []).append(i.detail)
    if not by_sec:
        return ""

    lines = [
        "# 데이터 갭 백로그 (editorial data_gap)",
        "",
        f"> 생성: {datetime.datetime.now():%Y-%m-%d %H:%M:%S} · report_id={state['data_pack'].meta.report_id}"
        f" · editorial_rounds={state.get('editorial_rounds', 0)} (전 라운드 누적)",
        "> 아래는 편집장 AI가 '데이터가 없어 서술로 해결 불가'로 분류한 지적이다.",
        "> 다음 차수에서 collect/dispatch(facts) 확장 후보 — 자동 반영 금지, 사람이 취사선택할 것.",
        "",
    ]
    for sid, details in by_sec.items():
        lines.append(f"## [{sid}]")
        lines += [f"- [ ] {d}" for d in details]
        lines.append("")

    path = OUTPUT_DIR / f"{stem}_data_gaps.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def _report_stem(state):
    """산출 파일명(확장자 제외)을 정한다.
    진입점(main)이 넣어준 report_name을 최우선으로 쓰고, 없으면 meta 기반으로 폴백한다.
    (정상 경로에선 main이 항상 report_name을 채우므로 폴백은 안전망일 뿐이다.)"""
    m = state["data_pack"].meta
    name = state.get("report_name")
    if name:
        # 진입점이 준 report_name(타임스탬프 포함)을 'r' 뒤에 붙여 서술형 파일명 + 겹침 방지.
        return f"{_slug(m.product_name)}_{_slug(m.reporting_period)}_PCF_r{_slug(name)}"
    return f"{_slug(m.product_name)}_{_slug(m.reporting_period)}_PCF_r{m.report_id}"


def render(state):
    md = state.get("draft_md", "")
    m = state["data_pack"].meta

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = _report_stem(state)   # report_name(main 지정) 우선, 없으면 meta 폴백

    # (1) Markdown — report_name 1벌만 저장(고정본/아카이브 이중 산출 폐지).
    #     저장본 끝에 DataPack(JSON)을 HTML 주석으로 임베드 → 이 .md 파일 하나로 PDF+차트를 재현.
    md_out = embed_datapack(md, state["data_pack"])
    md_path = OUTPUT_DIR / f"{stem}.md"
    md_path.write_text(md_out, encoding="utf-8")   # 한글 보존 위해 utf-8

    # (2) 데이터 갭 백로그 — editorial data_gap을 다음 차수 facts 확장 후보로 산출(없으면 생략)
    gaps_path = _write_data_gaps(state, stem)

    # (3) PDF — 병행 산출(실패해도 md는 유지). 차트는 md 임베드 DataPack에서 자동 생성돼
    #     '해당 표 바로 위'에 주입된다(md_to_pdf가 table_charts 미지정 시 자동 재생성).
    pdf_path = OUTPUT_DIR / f"{stem}.pdf"
    title = f"{m.product_name} — 제품 탄소발자국(PCF) 산출근거서"
    out = {"output_path": str(md_path), "data_gaps_path": gaps_path}
    try:
        md_to_pdf(md_out, pdf_path, title=title)
        out["output_pdf_path"] = str(pdf_path)
    except Exception as e:
        out["output_pdf_path"] = ""
        print(f"[render] PDF 생성 실패(.md는 정상 저장됨): {e}")

    return out
