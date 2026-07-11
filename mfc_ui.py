from __future__ import annotations

from html import escape
from textwrap import dedent

import altair as alt
import pandas as pd
import streamlit as st

from mfc_config import CHART_COLORS


AI_INSIGHT_LABELS = (
    "Count driver",
    "Duration driver",
    "Shared priority",
    "Next focus",
)


def apply_theme() -> None:
    st.markdown(
        dedent(
            """
            <style>
            .stApp {
                background:
                    radial-gradient(circle at top left, rgba(249, 115, 22, 0.10), transparent 32rem),
                    #0b1220;
                color: #e5edf8;
            }
            .block-container {
                max-width: 100%;
                padding: 2.35rem 0.85rem 1.2rem;
            }
            [data-testid="stHorizontalBlock"] {
                gap: 1rem;
            }
            [data-testid="stMarkdownContainer"] p {
                margin-bottom: 0.35rem;
            }
            hr {
                margin: 0.75rem 0;
                border-color: #273549;
            }
            h1, h2, h3, h4, h5, h6, p {
                color: #e5edf8;
            }
            .report-header {
                border: 1px solid #273549;
                border-radius: 14px;
                box-shadow: 0 18px 48px rgba(0, 0, 0, 0.32);
                margin: 0 auto 0.85rem;
                overflow: hidden;
                background: #111827;
                width: 100%;
            }
            .period-bar {
                background: #ff9800;
                color: #050505;
                min-height: 2.35rem;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.24rem;
                font-weight: 850;
                text-align: center;
            }
            .title-bar {
                background: #d9d9d9;
                color: #050505;
                min-height: 3.15rem;
                display: flex;
                align-items: center;
                justify-content: center;
                border-bottom: 2px solid #050505;
                font-size: 1.9rem;
                font-weight: 540;
                text-align: center;
            }
            .table-title {
                color: #f8fafc;
                font-size: 1.25rem;
                font-weight: 760;
                margin: 0.15rem 0 0.45rem;
            }
            .mfc-table-card {
                border: 1px solid #273549;
                border-radius: 14px;
                overflow: hidden;
                box-shadow: 0 12px 32px rgba(0, 0, 0, 0.22);
                background: #111827;
                margin-bottom: 0.75rem;
            }
            .mfc-report-table {
                width: 100%;
                table-layout: fixed;
                border-collapse: collapse;
                color: #e5edf8;
                font-size: 0.96rem;
            }
            .mfc-report-table th {
                background: #0f172a;
                color: #cbd5e1;
                font-size: 0.95rem;
                font-weight: 760;
                text-align: left;
                padding: 0.55rem 0.58rem;
                border-bottom: 1px solid #273549;
                border-right: 1px solid #273549;
                white-space: normal;
                line-height: 1.2;
            }
            .mfc-report-table td {
                padding: 0.4rem 0.58rem;
                border-bottom: 1px solid #273549;
                border-right: 1px solid #273549;
                line-height: 1.25;
            }
            .mfc-report-table tr:last-child td {
                border-bottom: 0;
            }
            .mfc-report-table th:last-child,
            .mfc-report-table td:last-child {
                border-right: 0;
            }
            .mfc-event-cell {
                font-weight: 650;
                overflow-wrap: anywhere;
            }
            .mfc-number-cell,
            .mfc-duration-cell,
            .mfc-status-cell {
                text-align: right;
                font-variant-numeric: tabular-nums;
            }
            .mfc-status-cell {
                text-align: center;
                font-size: 0.9rem;
                font-weight: 850;
                line-height: 1.1;
            }
            .mfc-status-badge {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 0.25rem;
                min-width: 6.8rem;
                border-radius: 999px;
                padding: 0.18rem 0.52rem;
                white-space: nowrap;
            }
            .mfc-status-up {
                color: #fecaca;
                background: rgba(239, 68, 68, 0.18);
                border: 1px solid rgba(239, 68, 68, 0.34);
            }
            .mfc-status-down {
                color: #22c55e;
                background: rgba(34, 197, 94, 0.16);
                border: 1px solid rgba(34, 197, 94, 0.34);
            }
            .mfc-status-same {
                color: #94a3b8;
                background: rgba(148, 163, 184, 0.14);
                border: 1px solid rgba(148, 163, 184, 0.24);
            }
            .ai-card {
                border: 1px solid #273549;
                border-radius: 14px;
                background:
                    linear-gradient(135deg, rgba(255, 152, 0, 0.08), transparent 34%),
                    #111827;
                box-shadow: 0 12px 32px rgba(0, 0, 0, 0.22);
                padding: 1rem 1.05rem 0.9rem;
                margin: -0.35rem 0 0.75rem;
            }
            .ai-card-header {
                display: flex;
                align-items: center;
                justify-content: flex-start;
                gap: 0.75rem;
                margin-bottom: 0.65rem;
            }
            .ai-card-title {
                color: #f8fafc;
                font-size: 1.22rem;
                font-weight: 820;
                letter-spacing: 0;
                margin: 0;
            }
            .ai-insight-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(245px, 1fr));
                gap: 0.65rem;
            }
            .ai-insight-card {
                min-height: 4.4rem;
                border: 1px solid #2d3a50;
                border-radius: 12px;
                background: rgba(15, 23, 42, 0.74);
                padding: 0.72rem 0.78rem;
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
            }
            .ai-insight-top {
                display: flex;
                align-items: center;
                gap: 0.42rem;
            }
            .ai-insight-index {
                width: 1.55rem;
                height: 1.55rem;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                border-radius: 999px;
                background: rgba(255, 152, 0, 0.15);
                border: 1px solid rgba(255, 152, 0, 0.32);
                color: #ffb74d;
                font-size: 0.8rem;
                font-weight: 880;
                font-variant-numeric: tabular-nums;
            }
            .ai-insight-label {
                color: #fed7aa;
                font-size: 0.78rem;
                font-weight: 820;
                text-transform: uppercase;
                letter-spacing: 0;
            }
            .ai-insight-text {
                color: #e5edf8;
                font-size: 1.02rem;
                font-weight: 660;
                line-height: 1.35;
                overflow-wrap: anywhere;
            }
            .ai-card-body,
            .ai-card-body p,
            .ai-card-body li {
                color: #dbeafe;
                font-size: 1rem;
                line-height: 1.45;
                overflow-wrap: anywhere;
                white-space: normal;
            }
            .ai-card-body ul {
                margin: 0.2rem 0 0.35rem 1.2rem;
                padding: 0;
            }
            .ai-card-body p {
                margin: 0.2rem 0 0.35rem;
            }
            .ai-card-caption {
                color: #94a3b8;
                font-size: 0.82rem;
                margin-top: 0.4rem;
            }
            div[data-testid="stDataFrame"] {
                border: 1px solid #273549;
                border-radius: 14px;
                overflow: hidden;
                box-shadow: 0 12px 32px rgba(0, 0, 0, 0.22);
                background: #111827;
            }
            div[data-testid="stVegaLiteChart"] {
                border: 1px solid #273549;
                border-radius: 14px;
                overflow: hidden;
                box-shadow: 0 12px 32px rgba(0, 0, 0, 0.22);
                background: #111827;
                padding: 0.6rem 0.7rem 0.15rem;
                margin-bottom: 0;
            }
            div[data-testid="stMetric"] {
                background: #111827;
                border: 1px solid #273549;
                border-radius: 14px;
                padding: 0.75rem 0.9rem;
                box-shadow: 0 8px 22px rgba(0, 0, 0, 0.18);
            }
            div[data-testid="stMetric"] label,
            div[data-testid="stMetric"] [data-testid="stMetricValue"] {
                color: #e5edf8;
            }
            [data-testid="stAlert"] {
                border-radius: 12px;
            }
            </style>
            """
        ),
        unsafe_allow_html=True,
    )


def render_header(period: str, top_n: int) -> None:
    st.markdown(
        (
            '<div class="report-header">'
            f'<div class="period-bar">Analysed period: {period}</div>'
            f'<div class="title-bar">Top {top_n} events based on MFC</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def display_table_title(title: str) -> None:
    st.markdown(f'<div class="table-title">{title}</div>', unsafe_allow_html=True)


def display_ai_summary(summary: str, caption: str) -> None:
    items = _summary_items(summary)
    if items:
        body = (
            '<div class="ai-insight-grid">'
            + "".join(
                (
                    '<div class="ai-insight-card">'
                    '<div class="ai-insight-top">'
                    f'<div class="ai-insight-index">{index:02d}</div>'
                    f'<div class="ai-insight-label">{AI_INSIGHT_LABELS[index - 1]}</div>'
                    '</div>'
                    f'<div class="ai-insight-text">{_inline_markdown(item)}</div>'
                    '</div>'
                )
                for index, item in enumerate(items, start=1)
            )
            + '</div>'
        )
    else:
        body = f'<div class="ai-card-body">{_markdown_to_html(summary)}</div>'

    st.markdown(
        (
            '<div class="ai-card">'
            '<div class="ai-card-header">'
            '<div class="ai-card-title">AI summary</div>'
            '</div>'
            f'{body}'
            f'<div class="ai-card-caption">{escape(caption)}</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def _markdown_to_html(text: str) -> str:
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if not lines:
        return "<p>No summary available.</p>"

    if all(_is_bullet(line) for line in lines):
        items = "".join(f"<li>{_inline_markdown(_bullet_text(line))}</li>" for line in lines)
        return f"<ul>{items}</ul>"

    html_lines = []
    list_items = []
    for line in lines:
        if _is_bullet(line):
            list_items.append(f"<li>{_inline_markdown(_bullet_text(line))}</li>")
        else:
            if list_items:
                html_lines.append(f"<ul>{''.join(list_items)}</ul>")
                list_items = []
            html_lines.append(f"<p>{_inline_markdown(line)}</p>")
    if list_items:
        html_lines.append(f"<ul>{''.join(list_items)}</ul>")
    return "".join(html_lines)


def _inline_markdown(text: str) -> str:
    escaped = escape(text)
    if escaped.count("**") % 2:
        escaped = escaped.replace("**", "")
    parts = escaped.split("**")
    if len(parts) < 3:
        return escaped
    result = []
    for index, part in enumerate(parts):
        if index % 2 == 1:
            result.append(f"<strong>{part}</strong>")
        else:
            result.append(part)
    return "".join(result)


def _is_bullet(line: str) -> bool:
    return line.startswith(("- ", "* "))


def _bullet_text(line: str) -> str:
    return line[2:].strip()


def _summary_items(text: str) -> list[str]:
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    items: list[str] = []
    for line in lines:
        if _is_bullet(line):
            value = _bullet_text(line)
        else:
            value = line
        value = _strip_insight_label(value.strip())
        if value:
            items.append(value)
    return items[:4]


def _strip_insight_label(value: str) -> str:
    lowered = value.lower()
    for label in AI_INSIGHT_LABELS:
        prefix = f"{label.lower()}:"
        if lowered.startswith(prefix):
            return value[len(prefix):].strip()
    return value


def display_table(df: pd.DataFrame, height: int) -> None:
    min_rows = max(len(df), int(max(0, height - 82) / 36))
    rows = [_table_row(row) for _, row in df.iterrows()]
    rows.extend(_blank_row() for _ in range(max(0, min_rows - len(rows))))
    html = (
        '<div class="mfc-table-card">'
        '<table class="mfc-report-table">'
        '<colgroup>'
        '<col style="width: 40%;">'
        '<col style="width: 12%;">'
        '<col style="width: 18%;">'
        '<col style="width: 30%;">'
        '</colgroup>'
        '<thead><tr>'
        '<th>Event</th>'
        '<th>Count</th>'
        '<th>Total Duration</th>'
        '<th>Comparison to previous quarter</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        '</table>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def _table_row(row: pd.Series) -> str:
    status = str(row.get("Comparison to previous quarter", "-"))
    if status == "UP":
        status_class = "mfc-status-up"
        status_value = "&uarr; Increase"
    elif status == "DOWN":
        status_class = "mfc-status-down"
        status_value = "&darr; Decrease"
    else:
        status_class = "mfc-status-same"
        status_value = "-"

    return (
        "<tr>"
        f'<td class="mfc-event-cell">{escape(str(row.get("Event", "")))}</td>'
        f'<td class="mfc-number-cell">{escape(str(row.get("Count", "")))}</td>'
        f'<td class="mfc-duration-cell">{escape(str(row.get("Total Duration", "")))}</td>'
        f'<td class="mfc-status-cell"><span class="mfc-status-badge {status_class}">{status_value}</span></td>'
        "</tr>"
    )


def _blank_row() -> str:
    return (
        "<tr>"
        '<td class="mfc-event-cell">&nbsp;</td>'
        '<td class="mfc-number-cell">&nbsp;</td>'
        '<td class="mfc-duration-cell">&nbsp;</td>'
        '<td class="mfc-status-cell">&nbsp;</td>'
        "</tr>"
    )


def chart_data(df: pd.DataFrame, metric_col: str, limit: int) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Event", "Value", "Share", "Label"])

    result = df.sort_values([metric_col, "Count"], ascending=False).head(limit).copy()
    total = float(df[metric_col].sum())
    result["Value"] = result[metric_col]
    result["Share"] = result["Value"] / total if total else 0.0
    result["Label"] = result["Share"].map(lambda value: f"{value * 100:.1f}%")
    return result[["Event", "Value", "Share", "Label"]]


def bar_chart(df: pd.DataFrame, metric_col: str, title: str, limit: int) -> alt.Chart:
    data = chart_data(df, metric_col, limit)
    chart_height = max(250, limit * 31)
    max_share = float(data["Share"].max()) if not data.empty else 1.0
    domain_max = min(1.0, max(0.1, max_share * 1.18))

    bars = (
        alt.Chart(data)
        .mark_bar(cornerRadius=5)
        .encode(
            y=alt.Y(
                "Event:N",
                sort="-x",
                title=None,
                axis=alt.Axis(
                    labelLimit=305,
                    labelColor="#dbeafe",
                    labelFontSize=13,
                    labelFontWeight=600,
                    tickSize=0,
                ),
            ),
            x=alt.X(
                "Share:Q",
                title=None,
                axis=alt.Axis(
                    labels=False,
                    ticks=False,
                    title=None,
                    grid=True,
                    domain=False,
                ),
                scale=alt.Scale(domain=[0, domain_max]),
            ),
            color=alt.Color("Event:N", scale=alt.Scale(range=CHART_COLORS), legend=None),
            tooltip=[
                alt.Tooltip("Event:N", title="Event"),
                alt.Tooltip("Share:Q", title="Share", format=".1%"),
                alt.Tooltip("Value:Q", title="Value", format=",.0f"),
            ],
        )
    )

    labels = (
        alt.Chart(data)
        .mark_text(align="left", baseline="middle", dx=6, color="#e5edf8", fontSize=15, fontWeight=800)
        .encode(
            y=alt.Y("Event:N", sort="-x", title=None),
            x=alt.X("Share:Q", scale=alt.Scale(domain=[0, domain_max])),
            text="Label:N",
        )
    )

    return (
        (bars + labels)
        .properties(title=title, height=chart_height)
        .configure(background="#111827")
        .configure_view(strokeWidth=0)
        .configure_axis(gridColor="#263244", domain=False)
        .configure_title(anchor="start", color="#f8fafc", fontSize=17, fontWeight=700)
    )
