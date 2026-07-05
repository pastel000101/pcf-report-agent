"""
slots.py — 슬롯 치환 렌더러 (Jinja2) [그룹 3 / LLM ✗ 숫자 정확성의 마지막 보루]

리포트 레이아웃은 templates/report.md.j2 에 있고, 여기는 'DataPack + narratives → 렌더'만 한다.
표/수치는 전적으로 코드(템플릿의 {{ }}·{% for %})가 DataPack 값으로 박는다. LLM은 서술만.

render_report(dp, outline, narratives) → 완성 Markdown
  - 헤더: 제목 + 메타 + 핵심 결과 표
  - 섹션별(outline 순): 제목 + 서술 + 해당 섹션 표(들)
  - 고지문: flags 기반 고정 문구

숫자 포맷은 Jinja2 필터 `num`(천단위 콤마 + 소수 자리, 정수면 정수)으로 통일.
"""

from decimal import Decimal
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from support.text import strip_emojis

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"


def _num(v, nd=2):
    """숫자를 천단위 콤마 + 소수 자리로. 정수면 정수로. None은 '-'.
    Decimal(배출량·중량 등)도 받는다 — 정수값은 정수로, 아니면 nd자리로 정밀 포맷."""
    if v is None:
        return "-"
    if isinstance(v, Decimal):
        if v == v.to_integral_value():
            return f"{int(v):,}"
        return f"{v:,.{nd}f}"          # Decimal 그대로 포맷(정밀)
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if isinstance(v, int):
        return f"{v:,}"
    return f"{v:,.{nd}f}"


def _factor(v):
    """배출계수 전용 포맷 — 크기 편차가 큰 계수(15.4 ~ 0.0001924)를 다룬다.
    소수 4자리로 반올림하면 아주 작은 계수(예: EF_TRUCK 0.0001924 → 0.0002)는
    유효숫자가 사라진다. 통상 계수는 4자리, 0.001 미만은 유효숫자 4개로 보존한다."""
    if v is None:
        return "-"
    v = float(v)
    if v == 0:
        return "0"
    if abs(v) >= 0.001:
        return f"{v:,.4f}"            # 통상 계수: 소수 4자리
    return f"{v:.4g}"                  # 아주 작은 계수: 유효숫자 보존(0.0001924 그대로)


# autoescape는 끈다(마크다운이라 HTML 이스케이프 불필요).
# trim_blocks/lstrip_blocks로 블록 태그 주변 공백을 정리해 표가 깨지지 않게 한다.
_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
)
_env.filters["num"] = _num
_env.filters["factor"] = _factor


def render_report(dp, outline, narratives: dict) -> str:
    """narratives: {section_id: 편집된 서술}. 표/수치는 코드(템플릿)가 박는다."""
    tmpl = _env.get_template("report.md.j2")
    md = tmpl.render(
        meta=dp.meta,
        result=dp.result,
        mass_balance=dp.mass_balance,
        materials=dp.materials,
        processes=dp.processes,
        emission_factors=dp.emission_factors,
        logistics=dp.logistics,
        emission_lines=dp.emission_lines,
        breakdown=dp.breakdown,
        hotspots=dp.hotspots,
        dqr=dp.dqr,
        sensitivity=dp.sensitivity,
        audit_log=dp.audit_log,
        flags=dp.flags,
        sections=outline.sections,
        narratives=narratives or {},
    )
    return strip_emojis(md)
