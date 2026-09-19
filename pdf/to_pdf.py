"""
to_pdf.py — Markdown → PDF 변환 엔진 [pdf 패키지 / LLM ✗ 순수 포맷]

★ 이 파일이 '엔진 교체 지점'이다. 외부(node/render.py)는 md_to_pdf()라는
   안정적 시그니처만 호출한다.

※ 엔진 교체 이력: 기존 WeasyPrint 버전은 Windows에서 GTK3 네이티브 DLL
  (libgobject-2.0-0 등)이 없으면 'cannot load library libgobject-2.0-0' 에러로
  전혀 동작하지 않았다. 별도 설치 프로그램 없이 순수 Python 패키지만으로 동작하도록
  reportlab 기반으로 교체했다 — Windows/Mac/Linux 어디서든 pip install만으로 끝난다.

흐름:
  draft_md(Markdown) ──직접 파싱(헤더·표·굵게)──> reportlab Flowables ──> PDF
  동봉 Pretendard 폰트(한글) 등록.

차트:
  - reportlab은 SVG를 직접 못 그리므로 charts.py가 PNG(data-URI)로 뽑아준다.
  - table_charts({표 캡션 → [PNG data-URI]}) 미지정 시, md 끝에 임베드된 DataPack에서
    자동 재생성한다(render.py가 embed_datapack으로 박아 둠 → .md 하나로 재현 가능).
  - 배치는 캡션 앵커: 본문에서 '**{캡션}**'으로 시작하는 줄(표 제목) 바로 뒤,
    즉 대응하는 표 '바로 위'에 삽입된다(charts.CHART_ANCHORS와 짝).
"""

import base64
import io
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

PKG_DIR = Path(__file__).resolve().parent
_FONT_REGULAR = PKG_DIR / "fonts" / "Pretendard-Regular.ttf"
_FONT_BOLD = PKG_DIR / "fonts" / "Pretendard-Bold.ttf"

_FONT_NAME = "Pretendard"
_FONT_NAME_BOLD = "Pretendard-Bold"


def _register_fonts() -> None:
    """동봉 Pretendard(한글 지원) TTF를 reportlab에 등록한다. 이미 등록됐으면 건너뛴다."""
    if _FONT_NAME in pdfmetrics.getRegisteredFontNames():
        return
    if _FONT_REGULAR.exists():
        pdfmetrics.registerFont(TTFont(_FONT_NAME, str(_FONT_REGULAR)))
    if _FONT_BOLD.exists():
        pdfmetrics.registerFont(TTFont(_FONT_NAME_BOLD, str(_FONT_BOLD)))
        pdfmetrics.registerFontFamily(_FONT_NAME, normal=_FONT_NAME, bold=_FONT_NAME_BOLD)


# ── md 자립용 DataPack 임베드 (기존과 동일한 포맷 유지 — render.py가 그대로 사용) ──────────
_DATA_BEGIN = "<!-- PCF-DATAPACK v1 "
_DATA_END = " -->"
_DATA_RE = re.compile(re.escape(_DATA_BEGIN) + r"(.*?)" + re.escape(_DATA_END), re.DOTALL)


def embed_datapack(md_text: str, dp) -> str:
    """차트 재생성용 DataPack(JSON)을 md 끝에 HTML 주석으로 박는다(md 뷰어에선 숨겨짐)."""
    payload = dp.model_dump_json()
    return f"{md_text.rstrip()}\n\n{_DATA_BEGIN}{payload}{_DATA_END}\n"


def _strip_datapack(md_text: str) -> str:
    """임베드 블록을 제거한 본문(PDF 렌더용)."""
    return _DATA_RE.sub("", md_text).rstrip() + "\n"


# ── 차트(PNG) 재생성·삽입 ─────────────────────────────────────────────────────
_USABLE_WIDTH = A4[0] - 32 * mm     # 본문 폭(A4 - 좌우 여백 16mm씩) — 차트 최대 폭


def _charts_from_embedded(md_text: str) -> dict:
    """md에 임베드된 DataPack(JSON)으로 {표 캡션 → [PNG data-URI]}를 재생성한다.
    임베드가 없거나 실패하면 빈 dict(차트 없이 본문만 렌더 — PDF 산출 자체는 막지 않는다)."""
    m = _DATA_RE.search(md_text)
    if not m:
        return {}
    try:
        # 지연 import: matplotlib(charts) 로딩 비용을 차트가 실제 필요할 때로 미룬다
        from state.datapack import DataPack
        from pdf.charts import build_table_charts
        dp = DataPack.model_validate_json(m.group(1))
        return build_table_charts(dp, fmt="png")
    except Exception as e:
        print(f"[to_pdf] 차트 재생성 실패(차트 없이 진행): {e}")
        return {}


CHART_SCALE = 0.8   # 차트 표시 배율 — 덩어리를 줄여 페이지 하단 공백을 완화(200dpi PNG라 축소해도 선명)


def _data_uri_to_image(uri: str, max_width: float) -> Image:
    """PNG data-URI → reportlab Image. charts.PNG_DPI 기준 실측 크기로 환산하고
    본문 폭을 넘으면 비율 유지 축소. CHART_SCALE로 일괄 축소해 조판 여유를 확보."""
    from pdf.charts import PNG_DPI
    raw = base64.b64decode(uri.split(",", 1)[1])
    buf = io.BytesIO(raw)
    iw, ih = ImageReader(buf).getSize()
    buf.seek(0)
    width = min(iw * 72.0 / PNG_DPI, max_width) * CHART_SCALE
    height = width * ih / iw
    return Image(buf, width=width, height=height)


def _pop_caption_charts(stripped: str, table_charts: dict):
    """이 줄이 차트 앵커(**캡션** 으로 시작하는 표 제목)면 해당 차트 목록을 꺼내 반환.
    pop이므로 같은 캡션이 본문에 재등장해도 중복 삽입되지 않는다."""
    for cap in list(table_charts):
        if stripped.startswith(f"**{cap}**"):
            return table_charts.pop(cap)
    return None


def _inline_md_to_reportlab(text: str) -> str:
    """인라인 **bold**만 reportlab Paragraph의 <b> 태그로 변환. 나머지는 XML 이스케이프."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    return text


def _parse_table(lines: list, start: int):
    """lines[start]부터 이어지는 '| ... |' 표 블록을 파싱해 (rows, 다음 줄 인덱스)를 반환.
    구분선(|---|---|)은 결과에서 제외한다."""
    rows = []
    i = start
    while i < len(lines) and lines[i].strip().startswith("|"):
        row = lines[i].strip()
        if re.match(r"^\|[\s:\-|]+\|$", row):
            i += 1
            continue
        cells = [c.strip() for c in row.strip("|").split("|")]
        rows.append(cells)
        i += 1
    return rows, i


SMALL_TABLE_MAX_ROWS = 12   # 이 행수 이하의 표는 통짜 유지(페이지 경계에서 안 쪼갬)


def _md_to_flowables(md_text: str, styles: dict, table_charts: dict = None) -> list:
    """md 본문 → Flowables. table_charts({캡션→[PNG data-URI]})가 있으면
    '**캡션**'으로 시작하는 줄(표 제목) 바로 뒤 = 표 바로 위에 차트를 삽입한다.

    조판 규칙(페이지 경계 쪼개짐·과도 공백 방지 — 2026-07-12):
      - 캡션(**굵은 줄**)+차트는 KeepTogether 한 덩어리(캡션 고아 방지).
        차트가 '있는' 캡션의 표는 별도 블록으로 둔다 — 통짜(캡션+차트+표 ≈ 700pt급)로 묶으면
        페이지 중간에 못 들어가 통째로 넘어가면서 하단에 큰 공백이 남는다(사용자 제보).
        블록을 절반 크기로 쪼개면 공백이 크게 준다.
      - 차트가 '없는' 캡션 + 작은 표(질량수지·핫스팟·DQR 등)는 기존대로 한 덩어리.
      - 작은 표(≤ SMALL_TABLE_MAX_ROWS)는 단독으로도 통짜 유지(미니 표 분할 방지),
        긴 표는 분할 허용(repeatRows=1로 헤더 반복).
      - 섹션 제목(h1~h3)은 '다음 블록'에 합류시켜 고아를 방지한다.
        ※ ParagraphStyle.keepWithNext는 이 조합(제목 다음이 KeepTogether)에서 무시됨을
          실측으로 확인(2026-07-12) → 코드가 직접 다음 블록 리스트에 제목을 끼워 넣는다."""
    table_charts = dict(table_charts or {})   # pop으로 소모하므로 복사본 사용
    flow = []
    pending = None             # [캡션 문단(+첫 차트)] — 뒤따르는 표와의 결합 후보
    pending_has_chart = False  # pending에 차트 포함 여부(포함이면 표와 결합하지 않음)
    pending_extra = []         # 같은 캡션의 두 번째 이후 차트 — 개별 블록(대형 덩어리 방지)
    pending_heading = None     # 직전 제목(h1~h3) — 다음 블록과 결합 대기(제목 고아 방지)

    def _take_heading() -> list:
        """대기 중인 제목을 꺼낸다(다음 블록의 선두에 끼워 넣기용)."""
        nonlocal pending_heading
        h, pending_heading = pending_heading, None
        return [h] if h is not None else []

    def _flush_pending():
        nonlocal pending, pending_has_chart, pending_extra
        if pending:
            flow.append(KeepTogether(pending))
        flow.extend(pending_extra)
        pending = None
        pending_has_chart = False
        pending_extra = []

    lines = md_text.split("\n")
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        if not stripped:
            # 캡션 덩어리·제목 대기 중엔 스페이서 생략(결합 블록 사이에 끼어들지 않게)
            if pending is None and pending_heading is None:
                flow.append(Spacer(1, 4))
            i += 1
            continue

        if stripped.startswith(("# ", "## ", "### ")):
            _flush_pending()
            if pending_heading is not None:      # 연속 제목이면 앞 제목은 그대로 배치
                flow.append(pending_heading)
            level = len(stripped.split(" ", 1)[0])          # '#' 개수 → h1~h3
            style = styles[f"h{min(level, 3)}"]
            pending_heading = Paragraph(_inline_md_to_reportlab(stripped[level + 1:]), style)
            i += 1
        elif stripped.startswith("|"):
            rows, next_i = _parse_table(lines, i)
            if rows:
                cell_style = ParagraphStyle(
                    "cell", fontName=_FONT_NAME, fontSize=8, leading=10.5,
                )
                header_style = ParagraphStyle(
                    "cell_header", fontName=_FONT_NAME_BOLD, fontSize=8, leading=10.5,
                )
                table_data = [
                    [Paragraph(_inline_md_to_reportlab(c), header_style) for c in rows[0]]
                ] + [
                    [Paragraph(_inline_md_to_reportlab(c), cell_style) for c in r]
                    for r in rows[1:]
                ]
                tbl = Table(table_data, hAlign="LEFT", repeatRows=1)
                tbl.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eaf6f0")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]))
                if len(rows) <= SMALL_TABLE_MAX_ROWS and pending and not pending_has_chart:
                    # 차트 없는 캡션 + 작은 표 → 한 덩어리(질량수지·핫스팟·DQR 등)
                    group = _take_heading() + pending + [tbl]
                    pending, pending_has_chart = None, False
                    flow.append(KeepTogether(group))
                elif len(rows) <= SMALL_TABLE_MAX_ROWS:
                    # 차트 있는 캡션은 [캡션+차트] / [표]를 분리 — 통짜 700pt급 공백 방지
                    _flush_pending()
                    flow.append(KeepTogether(_take_heading() + [tbl]))
                else:
                    # 긴 표는 분할 허용 — 캡션·차트 덩어리만 통짜로 앞세움
                    _flush_pending()
                    flow.extend(_take_heading())
                    flow.append(tbl)
                flow.append(Spacer(1, 8))
            else:
                _flush_pending()
            i = next_i
        else:
            para = Paragraph(_inline_md_to_reportlab(stripped), styles["body"])
            if stripped.startswith("**"):
                # 표 캡션(굵은 줄) — 바로 뒤 차트·표와 묶을 덩어리 시작(대기 제목이 있으면 합류)
                _flush_pending()
                pending = _take_heading() + [para]
                uris = _pop_caption_charts(stripped, table_charts)
                for k, uri in enumerate(uris or []):
                    try:
                        img = _data_uri_to_image(uri, _USABLE_WIDTH)
                        if k == 0:
                            # 첫 차트만 캡션과 결합 — 나머지는 개별 블록으로(공백 완화)
                            pending += [Spacer(1, 4), img, Spacer(1, 6)]
                            pending_has_chart = True
                        else:
                            pending_extra.append(KeepTogether([img, Spacer(1, 6)]))
                    except Exception as e:
                        print(f"[to_pdf] 차트 삽입 실패(건너뜀): {e}")
            else:
                _flush_pending()
                heads = _take_heading()
                if heads:
                    # 섹션 제목 + 첫 문단을 한 덩어리로(제목 고아 방지)
                    flow.append(KeepTogether(heads + [para]))
                else:
                    flow.append(para)
            i += 1
    _flush_pending()
    if pending_heading is not None:   # 문서 끝의 제목(비정상 md) 안전망
        flow.append(pending_heading)
    return flow


def md_to_pdf(md_text: str, output_path, *, title: str = "", table_charts: dict = None) -> str:
    """Markdown 문자열을 PDF 파일로 렌더한다(reportlab 엔진 — OS 네이티브 의존성 없음).

    md_text      : 보고서 Markdown(표/수치는 이미 코드가 박은 상태).
    output_path  : 저장할 .pdf 경로
    title        : PDF 메타데이터 제목
    table_charts : {표 캡션 → [PNG data-URI, ...]} — 미지정(None)이면 md에 임베드된
                   DataPack에서 자동 재생성한다(charts.build_table_charts(fmt="png")).
    반환         : 저장된 PDF 경로(str)
    """
    _register_fonts()

    if table_charts is None:
        table_charts = _charts_from_embedded(md_text)

    # keepWithNext=1: 제목이 페이지 하단에 홀로 남지 않게 다음 블록과 결합(제목 고아 방지)
    styles = {
        "h1": ParagraphStyle(
            "h1", fontName=_FONT_NAME_BOLD, fontSize=16, leading=20,
            spaceBefore=10, spaceAfter=8, textColor=colors.HexColor("#14503a"),
            keepWithNext=1,
        ),
        "h2": ParagraphStyle(
            "h2", fontName=_FONT_NAME_BOLD, fontSize=13, leading=17,
            spaceBefore=10, spaceAfter=6, textColor=colors.HexColor("#1c1c1c"),
            keepWithNext=1,
        ),
        "h3": ParagraphStyle(
            "h3", fontName=_FONT_NAME_BOLD, fontSize=11, leading=15,
            spaceBefore=8, spaceAfter=4, textColor=colors.HexColor("#333333"),
            keepWithNext=1,
        ),
        "body": ParagraphStyle(
            "body", fontName=_FONT_NAME, fontSize=9.5, leading=14,
            spaceAfter=4, alignment=TA_LEFT,
        ),
    }

    body_md = _strip_datapack(md_text)
    flowables = _md_to_flowables(body_md, styles, table_charts)

    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4,
        topMargin=18 * mm, bottomMargin=16 * mm, leftMargin=16 * mm, rightMargin=16 * mm,
        title=title or "PCF 산출근거서",
    )
    doc.build(flowables)
    return str(output_path)
