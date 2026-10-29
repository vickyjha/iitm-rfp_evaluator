"""Altair charts with one consistent, quiet style: thin marks, recessive axes, tooltips on every mark."""
from __future__ import annotations

import altair as alt
import pandas as pd

from ui.components import BRASS, INK, MUTED, SERIES

FONT = "IBM Plex Sans, sans-serif"
OTHER = "#8FA3A8"
SEQ = ["#E6F0FB", "#B9D4F3", "#7FB0E8", "#3F86D9", "#1F5FAE"]   # single-hue sequential (blue)


def _style(chart: alt.Chart, height) -> alt.Chart:
    return (chart.properties(height=height)
            .configure(font=FONT)
            .configure_view(strokeWidth=0)
            .configure_axis(labelColor=MUTED, titleColor=MUTED, gridColor="#E8EEEC", domain=False, tickColor="#E8EEEC",
                            labelFontSize=12, titleFontSize=12, titleFontWeight="normal")
            .configure_legend(labelColor=INK, titleColor=MUTED, orient="top", labelFontSize=12, titleFontSize=12))


def count_bars(df: pd.DataFrame, cat: str, value: str, title: str, height: int | None = None) -> alt.Chart:
    """Horizontal bars, single series, value labels at the end of each bar."""
    h = height or max(120, 46 * len(df))
    base = alt.Chart(df).encode(
        y=alt.Y(f"{cat}:N", sort="-x", title=None, axis=alt.Axis(labelLimit=260)),
        x=alt.X(f"{value}:Q", title=title, axis=alt.Axis(tickMinStep=1, format="d")),
        tooltip=[alt.Tooltip(f"{cat}:N", title="Category"), alt.Tooltip(f"{value}:Q", title=title)],
    )
    bars = base.mark_bar(color=SERIES, cornerRadiusEnd=4, height=22)
    labels = base.mark_text(align="left", dx=5, color=INK, fontSize=12).encode(text=f"{value}:Q")
    return _style(bars + labels, h)


def timeline(df: pd.DataFrame, date_col: str, value: str, title: str, weekly: bool = True) -> alt.Chart:
    """Counts per period as bars on an ordinal date axis (no gaps or oversized bars for sparse data)."""
    df = df.assign(label=df[date_col].dt.strftime("%d %b"))
    chart = alt.Chart(df).mark_bar(color=SERIES, cornerRadiusTopLeft=4, cornerRadiusTopRight=4, size=28).encode(
        x=alt.X("label:O", title=None, sort=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y(f"{value}:Q", title=title, axis=alt.Axis(tickMinStep=1, format="d")),
        tooltip=[alt.Tooltip(f"{date_col}:T", title="Week of" if weekly else "Date", format="%d %b %Y"),
                 alt.Tooltip(f"{value}:Q", title=title)],
    )
    return _style(chart, 230)


def ppi_strip(df: pd.DataFrame) -> alt.Chart:
    """Each dot is one supplier result; rank #1 suppliers in brass."""
    df = df.assign(Result=df["final_rank"].map(lambda r: "Ranked #1" if r == 1 else "Other suppliers"))
    chart = alt.Chart(df).mark_circle(size=110, opacity=0.9, stroke="white", strokeWidth=1.5).encode(
        x=alt.X("ppi:Q", title="Peer Performance Index (PPI)", scale=alt.Scale(domain=[0, 100])),
        y=alt.Y("category_label:N", title=None, axis=alt.Axis(labelLimit=260)),
        yOffset=alt.YOffset("jitter:Q"),
        color=alt.Color("Result:N", title=None, scale=alt.Scale(domain=["Ranked #1", "Other suppliers"],
                                                                range=[BRASS, OTHER])),
        tooltip=[alt.Tooltip("supplier_name:N", title="Supplier"), alt.Tooltip("rfp_title:N", title="RFP"),
                 alt.Tooltip("ppi:Q", title="PPI", format=".2f"), alt.Tooltip("final_rank:Q", title="Rank")],
    ).transform_calculate(jitter="(random() - 0.5) * 26")
    return _style(chart, max(170, 72 * df["category_label"].nunique()))


def supplier_ppi_bars(df: pd.DataFrame) -> alt.Chart:
    """Leaderboard bars in rank order; rank #1 in brass, the rest in the series colour."""
    df = df.assign(Result=df["Rank"].map(lambda r: "Ranked #1" if r == 1 else "Other suppliers"))
    base = alt.Chart(df).encode(
        y=alt.Y("Supplier:N", sort=list(df.sort_values("Rank")["Supplier"]), title=None,
                axis=alt.Axis(labelLimit=240)),
        x=alt.X("PPI:Q", scale=alt.Scale(domain=[0, 100]), title="Peer Performance Index (PPI)"),
        tooltip=["Rank:Q", "Supplier:N", alt.Tooltip("PPI:Q", format=".2f"),
                 alt.Tooltip("Absolute score:Q", format=".2f")],
    )
    bars = base.mark_bar(cornerRadiusEnd=4, height=22).encode(
        color=alt.Color("Result:N", legend=None, scale=alt.Scale(domain=["Ranked #1", "Other suppliers"],
                                                                 range=[BRASS, SERIES])))
    labels = base.mark_text(align="left", dx=5, color=INK, fontSize=12).encode(text=alt.Text("PPI:Q", format=".1f"))
    return _style(bars + labels, max(140, 44 * len(df)))


def relative_heatmap(df: pd.DataFrame, criteria_order: list[str], supplier_order: list[str]) -> alt.Chart:
    """Relative % vs benchmark per supplier and criterion (single-hue sequential)."""
    base = alt.Chart(df).encode(
        x=alt.X("Criterion:N", sort=criteria_order, title=None,
                axis=alt.Axis(labelAngle=0, labelLimit=160, orient="top", labelExpr="split(datum.label, ' & ')")),
        y=alt.Y("Supplier:N", sort=supplier_order, title=None, axis=alt.Axis(labelLimit=220)),
    )
    cells = base.mark_rect(stroke="white", strokeWidth=2, cornerRadius=3).encode(
        color=alt.Color("Relative %:Q", scale=alt.Scale(domain=[0, 100], range=SEQ),
                        legend=alt.Legend(title="Relative to best (%)", orient="bottom", gradientLength=220)),
        tooltip=["Supplier:N", "Criterion:N", alt.Tooltip("Score:Q", format=".4~g"),
                 alt.Tooltip("Relative %:Q", format=".1f")],
    )
    text = base.mark_text(fontSize=12).encode(
        text=alt.Text("Score:Q", format=".4~g"),
        color=alt.condition("datum['Relative %'] >= 70", alt.value("white"), alt.value(INK)),
    )
    return _style(cells + text, alt.Step(44))
