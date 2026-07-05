"""
to_pdf.py — Markdown → PDF 변환 엔진 [pdf 패키지 / LLM ✗ 순수 포맷]

★ 이 파일이 '엔진 교체 지점'이다. PDF 라이브러리를 바꾸려면 여기(+report.css)만 손대면 된다.
   외부(node/render.py)는 md_to_pdf()라는 안정적 시그니처만 호출한다.

흐름:
  draft_md(Markdown) ──markdown 라이브러리(tables)──> HTML 본문
                      ──report.css(@page·표·@font-face 동봉폰트)──> WeasyPrint ──> PDF

Windows 주의:
  WeasyPrint는 GTK 네이티브 DLL(libgobject/libpango/libcairo)이 필요하다. pip로는 안 들어온다.
  GTK3 런타임을 설치하고, 그 bin 경로를 os.add_dll_directory로 등록한다(PATH 의존 회피).
  탐색 순서: 환경변수 WEASYPRINT_GTK_BIN → ~/gtk3-runtime/bin → C:\Program Files\GTK3-Runtime Win64\bin.
  (리눅스/맥은 네이티브 라이브러리가 시스템에 있으므로 이 처리는 건너뛴다.)
"""

import os
import re
import sys
from pathlib import Path

import markdown

PKG_DIR = Path(__file__).resolve().parent
CSS_PATH = PKG_DIR / "report.css"

# markdown → HTML: 표(정렬 포함)·속성·리스트 처리
_MD_EXTENSIONS = ["tables", "attr_list", "sane_lists"]

# ── md 자립용 DataPack 임베드 ───────────────────────────────────────────────
# 차트는 숫자(DataPack)에서만 그려진다. .md에는 표(텍스트)만 있어 그대로는 차트를 못 만든다.
# 그래서 render가 저장할 .md 끝에 DataPack(JSON)을 HTML 주석으로 박아둔다(md 뷰어는 주석을 숨김).
# md_to_pdf는 table_charts를 안 받으면 이 블록을 꺼내 차트를 '자동 재생성'한다 → md 파일만으로 PDF+차트.
# 렌더 직전엔 이 블록을 제거하므로 본문 PDF에는 나타나지 않는다.
_DATA_BEGIN = "<!-- PCF-DATAPACK v1 "
_DATA_END = " -->"
# 주석 시작~첫 ' -->'까지(1줄 compact JSON). DOTALL은 혹시 모를 개행 대비.
_DATA_RE = re.compile(re.escape(_DATA_BEGIN) + r"(.*?)" + re.escape(_DATA_END), re.DOTALL)


def embed_datapack(md_text: str, dp) -> str:
    """차트 재생성용 DataPack(JSON)을 md 끝에 HTML 주석으로 박는다(md 뷰어에선 숨겨짐).
    render가 .md 저장 직전에 호출 → 저장된 .md 파일 하나로 PDF+차트를 재현할 수 있게 한다."""
    payload = dp.model_dump_json()   # pydantic v2: 개행 없는 compact JSON(1줄)
    return f"{md_text.rstrip()}\n\n{_DATA_BEGIN}{payload}{_DATA_END}\n"


def _extract_datapack_json(md_text: str):
    """md에 임베드된 DataPack JSON 문자열을 꺼낸다(없으면 None)."""
    m = _DATA_RE.search(md_text)
    return m.group(1) if m else None


def _strip_datapack(md_text: str) -> str:
    """임베드 블록을 제거한 본문(HTML 렌더용). 주석이라 렌더엔 안 나오지만 확실히 걷어낸다."""
    return _DATA_RE.sub("", md_text).rstrip() + "\n"


def _charts_from_md(md_text: str) -> dict:
    """md에 임베드된 DataPack에서 표별 차트({캡션→[SVG]})를 재생성한다.
    임베드가 없거나 파싱/차트 생성이 실패하면 빈 dict(차트 없이 PDF는 정상 산출)."""
    raw = _extract_datapack_json(md_text)
    if not raw:
        return {}
    try:
        from state.datapack import DataPack        # 지연 import(무거운 의존 회피)
        from pdf.charts import build_table_charts   # matplotlib 로드도 여기서
        return build_table_charts(DataPack.model_validate_json(raw))
    except Exception as e:
        print(f"[to_pdf] 임베드 DataPack→차트 재생성 실패(차트 생략): {e}")
        return {}


def _register_gtk_dll_dir() -> None:
    """Windows에서 WeasyPrint가 GTK DLL을 찾도록 dll 디렉터리를 등록한다.
    찾지 못하면 조용히 넘어간다(PATH에 있거나 비-Windows일 수 있음)."""
    if sys.platform != "win32" or not hasattr(os, "add_dll_directory"):
        return
    candidates = []
    env = os.getenv("WEASYPRINT_GTK_BIN")
    if env:
        candidates.append(Path(env))
    candidates += [
        Path.home() / "gtk3-runtime" / "bin",
        Path(r"C:\Program Files\GTK3-Runtime Win64\bin"),
    ]
    for d in candidates:
        if (d / "libgobject-2.0-0.dll").exists():
            os.add_dll_directory(str(d))
            return


def _md_to_html_body(md_text: str) -> str:
    return markdown.markdown(md_text, extensions=_MD_EXTENSIONS, output_format="html5")


def _inject_charts(html: str, table_charts: dict) -> str:
    """각 차트를 '대응하는 표 바로 위'에 끼워넣는다.
    table_charts: {표 캡션 → [SVG data-URI, ...]}.
    HTML에서 <strong>{캡션}을 찾아 그 다음 <table> 직전에 차트를 삽입한다.
    .md는 건드리지 않고 PDF용 HTML에만 주입 → .md는 텍스트·표로 깨끗하게 유지."""
    if not table_charts:
        return html
    for caption, uris in table_charts.items():
        figs = "".join(
            f'<figure class="chart"><img src="{uri}" alt="chart"/></figure>'
            for uri in uris
        )
        # 캡션은 표 앞의 굵은 제목(<strong>{캡션}). 서술 본문의 동일 문구 오탐을 피한다.
        cpos = html.find(f"<strong>{caption}")
        if cpos == -1:
            continue
        tpos = html.find("<table", cpos)   # 캡션 다음에 오는 표
        if tpos == -1:
            continue
        html = html[:tpos] + figs + html[tpos:]
    return html


def _wrap_html(body: str, title: str) -> str:
    """본문 HTML을 완전한 문서로 감싼다. 스타일은 report.css(stylesheets 인자)가 별도 주입."""
    safe_title = title or "PCF 산출근거서"
    return (
        "<!DOCTYPE html><html lang='ko'><head><meta charset='utf-8'>"
        f"<title>{safe_title}</title></head><body>{body}</body></html>"
    )


def md_to_pdf(md_text: str, output_path, *, title: str = "", table_charts: dict = None) -> str:
    """Markdown 문자열을 PDF 파일로 렌더한다.

    md_text      : 보고서 Markdown(표/수치는 이미 코드가 박은 상태). embed_datapack로
                   DataPack이 임베드돼 있으면, table_charts 없이도 차트를 자동 재생성한다.
    output_path  : 저장할 .pdf 경로
    title        : 문서 제목(미지정 시 본문 H1을 머리글로 사용)
    table_charts : {표 캡션 → [SVG data-URI]} — 대응 표 바로 위에 차트 주입(PDF 전용).
                   None이면 md에 임베드된 DataPack에서 자동 생성 → md 파일만으로 차트 산출.
    반환         : 저장된 PDF 경로(str)
    """
    # WeasyPrint는 GTK DLL이 필요 → import 전에 dll 경로 등록(지연 import로 앱 전역 크래시 방지)
    _register_gtk_dll_dir()
    from weasyprint import CSS, HTML   # 지연 import

    # table_charts 미지정 → md 임베드 DataPack에서 차트 자동 생성(md 자립).
    if table_charts is None:
        table_charts = _charts_from_md(md_text)
    # 임베드 블록(HTML 주석)은 렌더 대상에서 제거 → 본문 PDF에 안 나오게.
    body = _inject_charts(_md_to_html_body(_strip_datapack(md_text)), table_charts or {})
    html_doc = _wrap_html(body, title)
    # base_url=PKG_DIR: CSS의 url("fonts/..")가 pdf/ 기준으로 해석되게.
    HTML(string=html_doc, base_url=str(PKG_DIR)).write_pdf(
        str(output_path), stylesheets=[CSS(filename=str(CSS_PATH))]
    )
    return str(output_path)
