"""
charts.py — DataPack → 차트(SVG data-URI) [pdf 패키지 / LLM ✗ 숫자 시각화]

표/수치를 코드가 박는 원칙(slots.py)과 같은 계열. 차트도 DataPack 숫자만으로 '코드가' 그린다.
LLM은 관여하지 않는다 → 환각 위험 없음.

출력: build_charts(dp) → {chart_id: "data:image/svg+xml;base64,..."}
  - SVG(벡터) → PDF에서 선명하고 용량 작음.
  - svg.fonttype='path' → 텍스트를 벡터 path로 렌더 → WeasyPrint가 폰트 의존 없이 한글 출력.

배치는 to_pdf가 CHART_ANCHORS 매핑(차트 id → 표 캡션)으로 결정한다.
각 차트는 '대응하는 표 바로 위'에 주입된다(캡션 <strong> 텍스트를 앵커로 그 표 직전에 삽입).
차트를 빼고 싶으면 CHART_ANCHORS에서 해당 id만 지우면 된다.
"""

import base64
import io
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")                      # 헤드리스(파일·서버)에서 GUI 백엔드 회피
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch

PKG_DIR = Path(__file__).resolve().parent
_FONT_REGULAR = PKG_DIR / "fonts" / "Pretendard-Regular.ttf"
_FONT_BOLD = PKG_DIR / "fonts" / "Pretendard-Bold.ttf"

# 동봉 Pretendard를 matplotlib에 등록(한글 라벨)
for _fp in (_FONT_REGULAR, _FONT_BOLD):
    if _fp.exists():
        font_manager.fontManager.addfont(str(_fp))
_FONT_NAME = (
    font_manager.FontProperties(fname=str(_FONT_REGULAR)).get_name()
    if _FONT_REGULAR.exists() else "sans-serif"
)
plt.rcParams["font.family"] = _FONT_NAME
plt.rcParams["axes.unicode_minus"] = False     # 마이너스 기호 깨짐 방지
plt.rcParams["svg.fonttype"] = "path"          # 텍스트 → 벡터 path(폰트 임베딩 불필요)

# 차트 id → 그 차트를 '바로 위'에 붙일 표의 캡션(templates/report.md.j2의 **굵은 제목**과 일치).
# to_pdf가 HTML에서 <strong>{캡션}을 찾아 그 다음 <table> 직전에 차트를 끼운다.
# 순서(dict 삽입순)대로 같은 표 위에 쌓인다(scope 도넛 → breakdown 막대).
# 차트를 빼려면 여기서 해당 id만 지운다.
CHART_ANCHORS = {
    "boundary":       "공정 라우팅·할당",
    "materials":      "자재 인벤토리 (BOM)",
    "scope":          "Scope별 배출 기여",
    "breakdown":      "Scope별 배출 기여",
    "emission_lines": "활동별 배출 산정 (LCI → LCIA)",
    "sensitivity":    "민감도 분석",
}

# 시스템 경계 흐름도용 — 알려진 생애주기 단계의 표준 순서·라벨(제품 무관).
# system_boundary 문자열에 등장하는 토큰만 '포함'으로 그린다(데이터 주도).
_STAGE_ORDER = [
    ("upstream material", "원부자재 생산\n(Upstream)"),
    ("inbound transport", "자재 운송\n(Inbound)"),
    ("gate-to-gate",      "제조\n(Gate-to-Gate)"),
]

# 색 팔레트(보고서 톤: 녹색 계열 강조)
_GREEN = "#2a9d6f"
_PALETTE = ["#2a9d6f", "#4c9be8", "#e8a14c", "#9b8bd6", "#d96c6c", "#7bbf8a"]


def _fig_to_data_uri(fig) -> str:
    """matplotlib figure → SVG data-URI. figure는 닫는다(메모리 누수 방지)."""
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", transparent=True)
    plt.close(fig)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def _chart_scope(dp):
    """Scope별 배출 구성 도넛."""
    r = dp.result
    pairs = [
        ("Scope 1 직접", r.scope1_tco2eq),
        ("Scope 2 전력", r.scope2_tco2eq),
        ("Scope 3 원부자재", r.scope3_upstream_tco2eq),
        ("Scope 3 운송·기타", r.scope3_other_tco2eq),
    ]
    pairs = [(l, v) for l, v in pairs if v and v > 0]
    if not pairs:
        return None
    labels = [l for l, _ in pairs]
    vals = [float(v) for _, v in pairs]    # Decimal → float (matplotlib)
    total = sum(vals)
    fig, ax = plt.subplots(figsize=(6.0, 3.8))
    # 작은 조각은 라벨이 겹치므로 인라인 라벨 없이 범례로, %는 5% 이상만 조각에 표시
    wedges, _ = ax.pie(
        vals, startangle=90, counterclock=False,
        colors=_PALETTE[:len(vals)], radius=1.0,
        wedgeprops=dict(width=0.42, edgecolor="white", linewidth=1.2),
    )
    for w, v in zip(wedges, vals):
        pct = v / total * 100
        if pct >= 5:
            ang = (w.theta2 + w.theta1) / 2
            x = 0.79 * math.cos(math.radians(ang))
            y = 0.79 * math.sin(math.radians(ang))
            ax.text(x, y, f"{pct:.1f}%", ha="center", va="center",
                    fontsize=9, color="white", fontweight="bold")
    # 범례: 카테고리 + 절대값 + %
    leg_labels = [f"{l}  {v:,.0f} tCO₂eq ({v / total * 100:.1f}%)" for l, v in zip(labels, vals)]
    ax.legend(wedges, leg_labels, loc="center left", bbox_to_anchor=(0.98, 0.5),
              fontsize=8.5, frameon=False)
    ax.set_title("Scope별 배출 구성", fontsize=12, fontweight="bold", pad=12)
    return _fig_to_data_uri(fig)


def _chart_breakdown(dp):
    """활동별 배출 기여(가로 막대, 기여 비율)."""
    items = [b for b in dp.breakdown if (b.scope or "").lower() != "total"]
    items = sorted(items, key=lambda b: b.total_tco2eq)   # 오름차순 → barh가 위로 큰 값
    if not items:
        return None
    labels = [b.activity for b in items]
    vals = [b.share_percent for b in items]
    fig, ax = plt.subplots(figsize=(6.2, 0.55 * len(items) + 1.2))
    bars = ax.barh(labels, vals, color=_GREEN)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_width() + max(vals) * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{v:.1f}%", va="center", fontsize=8.5)
    ax.set_xlabel("기여 비율 (%)", fontsize=9)
    ax.set_xlim(0, max(vals) * 1.15)
    ax.set_title("활동별 배출 기여", fontsize=12, fontweight="bold", pad=10)
    ax.spines[["top", "right"]].set_visible(False)
    return _fig_to_data_uri(fig)


def _chart_sensitivity(dp):
    """민감도: 기여 상위 배출원별 변동(%) → 최종 PCF 라인(드라이버마다 1선)."""
    if not dp.sensitivity:
        return None
    groups = {}
    for s in dp.sensitivity:
        groups.setdefault(s.parameter, []).append(s)
    fig, ax = plt.subplots(figsize=(5.8, 3.4))
    for param, rows in groups.items():
        rows = sorted(rows, key=lambda s: s.delta_percent)
        ax.plot([s.delta_percent for s in rows], [s.new_pcf for s in rows],
                marker="o", linewidth=2, label=param)
    ax.axvline(0, color="#bbb", linestyle="--", linewidth=1)
    ax.set_xlabel("배출원 변동 (%)", fontsize=9)
    ax.set_ylabel(f"최종 PCF ({dp.result.pcf_unit})", fontsize=9)
    ax.set_title("민감도 분석 (기여 상위 배출원)", fontsize=12, fontweight="bold", pad=10)
    ax.legend(fontsize=7, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.3)
    return _fig_to_data_uri(fig)


def _chart_materials(dp):
    """자재별 배출(가로 막대, tCO₂eq)."""
    items = [m for m in dp.materials if m.emission_tco2eq]
    items = sorted(items, key=lambda m: m.emission_tco2eq)
    if not items:
        return None
    labels = [m.material_name for m in items]
    vals = [float(m.emission_tco2eq) for m in items]    # Decimal → float (matplotlib)
    fig, ax = plt.subplots(figsize=(6.2, 0.55 * len(items) + 1.2))
    bars = ax.barh(labels, vals, color=_PALETTE[1])
    for bar, v in zip(bars, vals):
        ax.text(bar.get_width() + max(vals) * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{v:,.0f}", va="center", fontsize=8.5)
    ax.set_xlabel("배출량 (tCO₂eq)", fontsize=9)
    ax.set_xlim(0, max(vals) * 1.15)
    ax.set_title("자재별 배출", fontsize=12, fontweight="bold", pad=10)
    ax.spines[["top", "right"]].set_visible(False)
    return _fig_to_data_uri(fig)


def _chart_emission_lines(dp):
    """활동별 배출 구성 도넛 — emission_lines를 배출량 기준으로.
    한 항목(양극재)이 압도적이라, 2% 미만 활동은 '기타'로 묶어 가독성을 확보한다."""
    lines = [l for l in dp.emission_lines if l.total_tco2eq and float(l.total_tco2eq) > 0]
    if not lines:
        return None
    total = sum(float(l.total_tco2eq) for l in lines)
    items = sorted(((l.activity, float(l.total_tco2eq)) for l in lines),
                   key=lambda x: x[1], reverse=True)
    THRESH = 2.0   # % 미만은 '기타'로 묶음
    named = [(a, v) for a, v in items if v / total * 100 >= THRESH]
    small = [(a, v) for a, v in items if v / total * 100 < THRESH]
    pairs = list(named)
    if small:
        pairs.append((f"기타 ({len(small)}개 활동)", sum(v for _, v in small)))

    labels = [a for a, _ in pairs]
    vals = [v for _, v in pairs]
    colors = [_PALETTE[i % len(_PALETTE)] for i in range(len(vals))]
    fig, ax = plt.subplots(figsize=(6.6, 4.0))
    wedges, _ = ax.pie(
        vals, startangle=90, counterclock=False, colors=colors, radius=1.0,
        wedgeprops=dict(width=0.42, edgecolor="white", linewidth=1.2),
    )
    for w, v in zip(wedges, vals):
        pct = v / total * 100
        if pct >= 5:
            ang = (w.theta2 + w.theta1) / 2
            x = 0.79 * math.cos(math.radians(ang))
            y = 0.79 * math.sin(math.radians(ang))
            ax.text(x, y, f"{pct:.1f}%", ha="center", va="center",
                    fontsize=9, color="white", fontweight="bold")
    leg = [f"{a}  {v:,.0f} tCO₂eq ({v / total * 100:.1f}%)" for a, v in pairs]
    ax.legend(wedges, leg, loc="center left", bbox_to_anchor=(0.98, 0.5),
              fontsize=8, frameon=False)
    ax.set_title("활동별 배출 구성", fontsize=12, fontweight="bold", pad=12)
    return _fig_to_data_uri(fig)


def _chart_boundary(dp):
    """시스템 경계 흐름도 — 포함 단계(박스+화살표) + 제외(회색) + Cut-off.
    포함 단계는 meta.system_boundary 토큰에서, 제조 세부공정은 processes에서(데이터 주도)."""
    boundary = dp.meta.system_boundary or ""
    tokens = {t.strip().lower() for t in boundary.split("+")}
    included = [lbl for key, lbl in _STAGE_ORDER if key in tokens]
    if not included:
        return None
    proc_chain = " → ".join(p.process_name for p in dp.processes) if dp.processes else ""

    n = len(included)
    fig, ax = plt.subplots(figsize=(7.4, 2.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")

    # 제목 + 경계 문자열
    ax.text(5, 3.72, "시스템 경계 (System Boundary)", ha="center", fontsize=11, fontweight="bold")
    ax.text(5, 3.30, boundary, ha="center", fontsize=8, color="#666")

    # 포함 박스(녹색) — 가운데 영역에 균등 배치
    x0, x1, cy = 1.7, 8.3, 2.25
    gap = (x1 - x0) / n
    bw = gap * 0.82
    centers = [x0 + gap * (i + 0.5) for i in range(n)]
    for cx, lbl in zip(centers, included):
        ax.add_patch(FancyBboxPatch(
            (cx - bw / 2, cy - 0.42), bw, 0.84,
            boxstyle="round,pad=0.02,rounding_size=0.08",
            linewidth=1.4, edgecolor=_GREEN, facecolor="#eaf6f0",
        ))
        ax.text(cx, cy, lbl, ha="center", va="center", fontsize=8.3, color="#14503a")
    for i in range(n - 1):                 # 포함 단계 사이 화살표
        ax.annotate("", xy=(centers[i + 1] - bw / 2, cy), xytext=(centers[i] + bw / 2, cy),
                    arrowprops=dict(arrowstyle="-|>", color=_GREEN, lw=1.6))

    # 제외(회색) — 좌(상류)·우(하류)
    ax.text(0.75, cy, "원자재\n채굴·정제\n[제외]", ha="center", va="center", fontsize=7, color="#b0b0b0")
    ax.annotate("", xy=(x0 - 0.05, cy), xytext=(1.35, cy),
                arrowprops=dict(arrowstyle="-|>", color="#cfcfcf", lw=1.2))
    ax.text(9.25, cy, "제품 유통\n사용·폐기\n[제외]", ha="center", va="center", fontsize=7, color="#b0b0b0")
    ax.annotate("", xy=(9.0, cy), xytext=(x1 + 0.05, cy),
                arrowprops=dict(arrowstyle="-|>", color="#cfcfcf", lw=1.2))

    # 제조 세부공정 + 고지 노트
    if proc_chain:
        ax.text(5, 1.18, f"제조 세부공정:  {proc_chain}", ha="center", va="center",
                fontsize=7.2, color="#14503a")
    notes = []
    if getattr(dp.flags, "boundary_partial", False):
        notes.append("Cradle-to-Grave 아님")
    if getattr(dp.flags, "cutoff_applied", False):
        notes.append("재활용 회피 배출 Cut-off (ISO 14067)")
    if notes:
        ax.text(5, 0.45, " · ".join(notes), ha="center", fontsize=7, color="#999")

    return _fig_to_data_uri(fig)


_BUILDERS = {
    "boundary": _chart_boundary,
    "scope": _chart_scope,
    "breakdown": _chart_breakdown,
    "emission_lines": _chart_emission_lines,
    "sensitivity": _chart_sensitivity,
    "materials": _chart_materials,
}


def build_charts(dp) -> dict:
    """DataPack → {chart_id: SVG data-URI}. 개별 차트 실패는 건너뛴다(하나 깨져도 나머지 유지)."""
    out = {}
    for cid, fn in _BUILDERS.items():
        try:
            uri = fn(dp)
            if uri:
                out[cid] = uri
        except Exception as e:
            print(f"[charts] '{cid}' 생성 실패(건너뜀): {e}")
    return out


def build_table_charts(dp) -> dict:
    """DataPack → {표 캡션 → [SVG data-URI, ...]}.

    build_charts로 차트를 만든 뒤 CHART_ANCHORS(차트 id→표 캡션)로 캡션별로 묶는다.
    to_pdf가 이 매핑으로 '그 표 바로 위'에 차트를 주입한다. 같은 캡션이면 삽입순으로 쌓인다."""
    charts = build_charts(dp)
    grouped = {}
    for cid, caption in CHART_ANCHORS.items():
        if cid in charts:
            grouped.setdefault(caption, []).append(charts[cid])
    return grouped
