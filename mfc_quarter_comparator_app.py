from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from mfc_ai import (
    AI_SUMMARY_VERSION,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_OPENAI_MODEL,
    GEMINI_MODEL_OPTIONS,
    build_local_summary,
    generate_gemini_summary,
    generate_openai_summary,
    resolve_gemini_api_key,
    resolve_openai_api_key,
)
from mfc_data import (
    aggregate_events,
    comparison_table,
    display_data_span,
    display_period,
    number_text,
    previous_quarter,
    process_period,
    quarter_range,
    read_xlsx_bytes,
    seconds_to_hhmmss,
)
from mfc_ui import apply_theme, bar_chart, display_ai_summary, display_table, display_table_title, render_header


st.set_page_config(
    page_title="MFC quarter report",
    page_icon="MFC",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def read_xlsx(file_bytes: bytes) -> pd.DataFrame:
    return read_xlsx_bytes(file_bytes)


def read_secret(*names: str) -> str | None:
    try:
        secrets = st.secrets
        for name in names:
            value = secrets.get(name)
            if value and str(value).strip():
                return str(value).strip()
    except Exception:
        return None
    return None


apply_theme()

with st.sidebar:
    st.markdown("### XLSX files")
    previous_file = st.file_uploader("Previous quarter", type=["xlsx"], key="previous_file")
    current_file = st.file_uploader("Analysed quarter", type=["xlsx"], key="current_file")

    st.markdown("---")
    st.markdown("### Quarter")
    today = date.today()
    year = st.number_input("Analysed year", min_value=2020, max_value=2035, value=today.year, step=1)
    quarter = st.selectbox("Analysed quarter", options=[1, 2, 3, 4], index=(today.month - 1) // 3)
    prev_year, prev_quarter = previous_quarter(int(year), int(quarter))
    previous_start, previous_end = quarter_range(prev_year, prev_quarter)
    current_start, current_end = quarter_range(int(year), int(quarter))

    st.caption(f"Previous: Q{prev_quarter} {prev_year}: {display_period(previous_start, previous_end)}")
    st.caption(f"Analysed: Q{quarter} {year}: {display_period(current_start, current_end)}")

    st.markdown("---")
    st.markdown("### Filters")
    group_mode = st.radio(
        "Aggregation",
        options=["Description", "Description + Item"],
        index=0,
    )
    group_col = "Event" if group_mode == "Description" else "Event + Item"

    include_jam_wasteline = st.checkbox("Jam Wasteline", value=True)
    include_chute_full_return = st.checkbox("Chute full return", value=True)
    exclude_nights = st.checkbox("Exclude outside 06:00-22:30", value=False)
    exclude_sundays = st.checkbox("Exclude Sundays", value=False)
    use_max_minutes = st.checkbox("Reject events longer than limit", value=False)
    max_minutes = None
    if use_max_minutes:
        max_minutes = st.number_input("Duration limit [min]", min_value=1, value=240, step=5)

    st.markdown("---")
    top_n = st.number_input("TOP rows", min_value=1, max_value=30, value=10, step=1)

    st.markdown("---")
    st.markdown("### AI summary")
    ai_provider = st.selectbox(
        "Provider",
        options=["Local summary", "Gemini", "OpenAI"],
        index=0,
    )
    ai_key_input = ""
    ai_model = ""
    if ai_provider == "Gemini":
        selected_gemini_model = st.selectbox(
            "Gemini model",
            options=list(GEMINI_MODEL_OPTIONS),
            index=list(GEMINI_MODEL_OPTIONS).index(DEFAULT_GEMINI_MODEL),
        )
        if selected_gemini_model == "Custom model...":
            ai_model = st.text_input("Custom Gemini model", value=DEFAULT_GEMINI_MODEL)
        else:
            ai_model = selected_gemini_model
        ai_key_input = st.text_input(
            "Gemini API key override",
            type="password",
            help="Optional. Uses GOOGLE_API_KEY or GEMINI_API_KEY from Streamlit secrets/environment.",
        )
    elif ai_provider == "OpenAI":
        ai_model = st.text_input("OpenAI model", value=DEFAULT_OPENAI_MODEL)
        ai_key_input = st.text_input(
            "OpenAI API key override",
            type="password",
            help="Optional. Uses OPENAI_API_KEY from Streamlit secrets/environment.",
        )
    else:
        st.caption("No external API. Summary is generated locally.")


render_header(display_period(current_start, current_end), int(top_n))

if not previous_file or not current_file:
    st.info("Upload two XLSX files: previous quarter and analysed quarter.")
    st.stop()

try:
    previous_raw = read_xlsx(previous_file.getvalue())
    current_raw = read_xlsx(current_file.getvalue())
except Exception as exc:
    st.error(f"Cannot read XLSX files: {exc}")
    st.stop()

previous_processed = process_period(
    previous_raw,
    previous_start,
    previous_end,
    exclude_nights,
    exclude_sundays,
    max_minutes,
    include_jam_wasteline,
    include_chute_full_return,
)
current_processed = process_period(
    current_raw,
    current_start,
    current_end,
    exclude_nights,
    exclude_sundays,
    max_minutes,
    include_jam_wasteline,
    include_chute_full_return,
)

all_events = (
    pd.concat(
        [
            previous_processed[[group_col]].rename(columns={group_col: "Event"}),
            current_processed[[group_col]].rename(columns={group_col: "Event"}),
        ],
        ignore_index=True,
    )["Event"]
    .dropna()
    .astype(str)
    .sort_values()
    .unique()
    .tolist()
)

with st.sidebar:
    st.markdown("---")
    st.markdown("### Events")
    selected_events = st.multiselect(
        "Used in both quarters",
        options=all_events,
        default=all_events,
    )

if current_processed.empty:
    st.warning(
        "No events in analysed quarter after filters. "
        f"Selected period: {display_period(current_start, current_end)}. "
        f"Current file dates: {display_data_span(current_raw)}."
    )

if not selected_events:
    st.warning("Select at least one event.")
    st.stop()

previous_agg = aggregate_events(previous_processed, group_col, selected_events)
current_agg = aggregate_events(current_processed, group_col, selected_events)

count_table = comparison_table(current_agg, previous_agg, "count", int(top_n))
duration_table = comparison_table(current_agg, previous_agg, "duration", int(top_n))

table_height = 82 + int(top_n) * 36
left, right = st.columns(2, gap="medium")
with left:
    display_table_title("Top all events sorted by count - aggregate")
    display_table(count_table, table_height)
with right:
    display_table_title("Top all events sorted by total duration - aggregate")
    display_table(duration_table, table_height)

chart_left, chart_right = st.columns(2, gap="medium")
with chart_left:
    st.altair_chart(bar_chart(current_agg, "Count", "Events Count Chart", int(top_n)), width="stretch")
with chart_right:
    st.altair_chart(
        bar_chart(current_agg, "Total_seconds", "Events Duration Chart", int(top_n)),
        width="stretch",
    )

local_summary = build_local_summary(count_table, duration_table)
caption = "Validated local summary. Select Gemini or OpenAI to generate an AI-written version."
summary_to_show = local_summary
summary_key = (
    AI_SUMMARY_VERSION
    + "|"
    + ai_provider
    + "|"
    + ai_model.strip()
    + "|"
    + count_table.to_json(orient="records")
    + duration_table.to_json(orient="records")
)

api_key = None
provider_model = ai_model.strip()
missing_key_message = ""
if ai_provider == "Gemini":
    secret_key = read_secret("GOOGLE_API_KEY", "GEMINI_API_KEY")
    api_key = resolve_gemini_api_key(ai_key_input or secret_key)
    provider_model = provider_model or DEFAULT_GEMINI_MODEL
    missing_key_message = "Set GOOGLE_API_KEY or GEMINI_API_KEY in Streamlit secrets, or paste a key in the sidebar."
elif ai_provider == "OpenAI":
    secret_key = read_secret("OPENAI_API_KEY")
    api_key = resolve_openai_api_key(ai_key_input or secret_key)
    provider_model = provider_model or DEFAULT_OPENAI_MODEL
    missing_key_message = "Set OPENAI_API_KEY in Streamlit secrets, or paste a key in the sidebar."

if "ai_summary_text" not in st.session_state:
    st.session_state.ai_summary_text = ""
if "ai_summary_error" not in st.session_state:
    st.session_state.ai_summary_error = ""
if "ai_summary_key" not in st.session_state:
    st.session_state.ai_summary_key = ""
if st.session_state.ai_summary_key != summary_key:
    st.session_state.ai_summary_text = ""
    st.session_state.ai_summary_error = ""
    st.session_state.ai_summary_key = summary_key

def current_summary_card() -> tuple[str, str]:
    if st.session_state.ai_summary_text:
        return st.session_state.ai_summary_text, f"AI generated with {ai_provider} / {provider_model}."
    if st.session_state.ai_summary_error:
        return local_summary, f"{ai_provider} summary was incomplete. Showing validated local summary."
    return local_summary, caption


summary_placeholder = st.empty()
summary_to_show, summary_caption = current_summary_card()
with summary_placeholder.container():
    display_ai_summary(summary_to_show, summary_caption)

generate_clicked = False
if ai_provider != "Local summary":
    ai_left, ai_right = st.columns([1, 5], gap="small")
    with ai_left:
        generate_clicked = st.button("Generate AI summary", disabled=not bool(api_key), width="stretch")
    with ai_right:
        if not api_key:
            st.caption(missing_key_message)

if generate_clicked and api_key:
    with st.spinner(f"Generating AI summary with {ai_provider}..."):
        try:
            if ai_provider == "Gemini":
                st.session_state.ai_summary_text = generate_gemini_summary(
                    count_table,
                    duration_table,
                    api_key,
                    provider_model,
                )
            else:
                st.session_state.ai_summary_text = generate_openai_summary(
                    count_table,
                    duration_table,
                    api_key,
                    provider_model,
                )
            st.session_state.ai_summary_error = ""
            st.session_state.ai_summary_key = summary_key
        except Exception as exc:
            st.session_state.ai_summary_error = str(exc)

    summary_to_show, summary_caption = current_summary_card()
    with summary_placeholder.container():
        display_ai_summary(summary_to_show, summary_caption)

raw_outside_previous = len(previous_raw) - len(
    previous_raw[(previous_raw["Begin"] >= previous_start) & (previous_raw["Begin"] < previous_end)]
)
raw_outside_current = len(current_raw) - len(
    current_raw[(current_raw["Begin"] >= current_start) & (current_raw["Begin"] < current_end)]
)

st.markdown("---")
metrics = st.columns(4)
metrics[0].metric("Current records", number_text(len(current_processed)), f"from {number_text(len(current_raw))}")
metrics[1].metric("Previous records", number_text(len(previous_processed)), f"from {number_text(len(previous_raw))}")
metrics[2].metric("Current outside quarter", number_text(raw_outside_current))
metrics[3].metric("Previous outside quarter", number_text(raw_outside_previous))

with st.expander("Data preview"):
    preview_left, preview_right = st.columns(2)
    with preview_left:
        st.markdown("#### Previous quarter")
        prev_preview = previous_processed[["Begin", "End", "Item", "Description", "Duration_seconds"]].copy()
        prev_preview["Duration"] = prev_preview["Duration_seconds"].map(seconds_to_hhmmss)
        st.dataframe(prev_preview.drop(columns=["Duration_seconds"]).head(500), hide_index=True, width="stretch")
    with preview_right:
        st.markdown("#### Analysed quarter")
        cur_preview = current_processed[["Begin", "End", "Item", "Description", "Duration_seconds"]].copy()
        cur_preview["Duration"] = cur_preview["Duration_seconds"].map(seconds_to_hhmmss)
        st.dataframe(cur_preview.drop(columns=["Duration_seconds"]).head(500), hide_index=True, width="stretch")
