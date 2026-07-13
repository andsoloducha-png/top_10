from __future__ import annotations

from io import BytesIO
from typing import Iterable

import pandas as pd

from mfc_config import (
    CHUTE_FULL_MAX,
    CHUTE_FULL_MIN,
    JAM_WASTELINE_END,
    JAM_WASTELINE_START,
    PROCESS_END,
    PROCESS_START,
    REQUIRED_COLUMNS,
    RETURN_DIMENSION_EVENTS,
    RETURN_DIMENSION_ITEMS,
)


def quarter_range(year: int, quarter: int) -> tuple[pd.Timestamp, pd.Timestamp]:
    start_month = 3 * (quarter - 1) + 1
    start = pd.Timestamp(year=year, month=start_month, day=1)
    return start, start + pd.DateOffset(months=3)


def previous_quarter(year: int, quarter: int) -> tuple[int, int]:
    if quarter == 1:
        return year - 1, 4
    return year, quarter - 1


def display_period(start: pd.Timestamp, end_exclusive: pd.Timestamp) -> str:
    end_inclusive = (end_exclusive - pd.Timedelta(days=1)).date()
    return f"{start.date():%d.%m.%Y} - {end_inclusive:%d.%m.%Y}"


def display_data_span(df: pd.DataFrame) -> str:
    if df.empty or df["Begin"].dropna().empty:
        return "no valid dates"
    return f"{df['Begin'].min():%d.%m.%Y} - {df['Begin'].max():%d.%m.%Y}"


def seconds_to_hhmmss(seconds: float | int) -> str:
    seconds_int = int(round(float(seconds)))
    hours = seconds_int // 3600
    minutes = (seconds_int % 3600) // 60
    secs = seconds_int % 60
    return f"{hours}:{minutes:02d}:{secs:02d}"


def number_text(value: int | float) -> str:
    return f"{int(value):,}".replace(",", " ")


def item_to_number(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype("string")
        .str.strip()
        .str.replace(",", ".", regex=False)
        .str.extract(r"(-?\d+(?:\.\d+)?)", expand=False)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def overlap_seconds(
    a_start: pd.Timestamp,
    a_end: pd.Timestamp,
    b_start: pd.Timestamp,
    b_end: pd.Timestamp,
) -> float:
    start = max(a_start, b_start)
    end = min(a_end, b_end)
    if end <= start:
        return 0.0
    return (end - start).total_seconds()


def included_seconds(
    begin: pd.Timestamp,
    end: pd.Timestamp,
    period_end: pd.Timestamp,
    exclude_nights: bool,
    exclude_sundays: bool,
) -> float:
    end = min(end, period_end)
    if end <= begin:
        return 0.0

    if not exclude_nights and not exclude_sundays:
        return (end - begin).total_seconds()

    total = 0.0
    current_day = begin.normalize()
    last_day = end.normalize()
    while current_day <= last_day:
        if not (exclude_sundays and current_day.weekday() == 6):
            if exclude_nights:
                window_start = current_day + pd.Timedelta(hours=PROCESS_START.hour, minutes=PROCESS_START.minute)
                window_end = current_day + pd.Timedelta(hours=PROCESS_END.hour, minutes=PROCESS_END.minute)
                total += overlap_seconds(begin, end, window_start, window_end)
            else:
                total += overlap_seconds(begin, end, current_day, current_day + pd.Timedelta(days=1))
        current_day += pd.Timedelta(days=1)
    return total


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {str(col).strip().lower(): col for col in df.columns}
    missing = [col for col in REQUIRED_COLUMNS if col not in mapping]
    if missing:
        raise ValueError(
            "Missing columns: "
            + ", ".join(missing)
            + ". Required: Begin, End, Item, Description."
        )

    df = df.rename(
        columns={
            mapping["begin"]: "Begin",
            mapping["end"]: "End",
            mapping["item"]: "Item",
            mapping["description"]: "Description",
        }
    )
    return df[["Begin", "End", "Item", "Description"]].copy()


def read_xlsx_bytes(file_bytes: bytes) -> pd.DataFrame:
    df = pd.read_excel(BytesIO(file_bytes), sheet_name=0)
    df = normalize_columns(df)
    df["Begin"] = pd.to_datetime(df["Begin"], errors="coerce")
    df["End"] = pd.to_datetime(df["End"], errors="coerce")
    df["Item"] = df["Item"].astype("string").str.strip()
    df["Description"] = df["Description"].astype("string").str.strip()
    df = df.dropna(subset=["Begin", "End", "Item", "Description"]).copy()
    df = df[df["End"] > df["Begin"]].copy()
    df["Item_number"] = item_to_number(df["Item"])
    df["Event"] = df["Description"].astype(str)
    df["Event + Item"] = df["Description"].astype(str) + " | " + df["Item"].astype(str)
    return df.reset_index(drop=True)


def apply_special_flags(
    df: pd.DataFrame,
    include_jam_wasteline: bool,
    include_chute_full_return: bool,
    include_return_dimensions: bool,
) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    result = df.copy()
    description = result["Description"].astype(str).str.strip().str.casefold()
    item_number = result["Item_number"]
    keep = pd.Series(True, index=result.index)

    if not include_jam_wasteline:
        jam_wasteline = (
            description.eq("product jam")
            & item_number.ge(JAM_WASTELINE_START)
            & item_number.le(JAM_WASTELINE_END)
        )
        keep &= ~jam_wasteline

    if not include_chute_full_return:
        chute_full = description.eq("chute full")
        chute_full_2xx = item_number.ge(CHUTE_FULL_MIN) & item_number.lt(CHUTE_FULL_MAX)
        keep &= ~(chute_full & ~chute_full_2xx)

    if not include_return_dimensions:
        return_dimension_event = description.isin(RETURN_DIMENSION_EVENTS)
        return_dimension_item = item_number.round(3).isin(RETURN_DIMENSION_ITEMS)
        keep &= ~(return_dimension_event & return_dimension_item)

    return result[keep].copy()


def process_period(
    df: pd.DataFrame,
    period_start: pd.Timestamp,
    period_end: pd.Timestamp,
    exclude_nights: bool,
    exclude_sundays: bool,
    max_minutes: float | None,
    include_jam_wasteline: bool,
    include_chute_full_return: bool,
    include_return_dimensions: bool,
) -> pd.DataFrame:
    result = df[(df["Begin"] >= period_start) & (df["Begin"] < period_end)].copy()
    result = apply_special_flags(
        result,
        include_jam_wasteline,
        include_chute_full_return,
        include_return_dimensions,
    )
    if result.empty:
        result["Duration_seconds"] = pd.Series(dtype="float64")
        return result

    result["Duration_seconds"] = result.apply(
        lambda row: included_seconds(
            row["Begin"],
            row["End"],
            period_end,
            exclude_nights,
            exclude_sundays,
        ),
        axis=1,
    )
    result = result[result["Duration_seconds"] > 0].copy()
    if max_minutes is not None and max_minutes > 0:
        result = result[result["Duration_seconds"] <= max_minutes * 60].copy()
    return result


def aggregate_events(df: pd.DataFrame, group_col: str, selected_events: Iterable[str]) -> pd.DataFrame:
    columns = ["Event", "Count", "Total_seconds", "Total Duration"]
    if df.empty:
        return pd.DataFrame(columns=columns)

    selected = set(selected_events)
    scoped = df[df[group_col].astype(str).isin(selected)].copy()
    if scoped.empty:
        return pd.DataFrame(columns=columns)

    table = (
        scoped.groupby(group_col, dropna=False)
        .agg(Count=(group_col, "size"), Total_seconds=("Duration_seconds", "sum"))
        .reset_index()
        .rename(columns={group_col: "Event"})
    )
    table["Total Duration"] = table["Total_seconds"].map(seconds_to_hhmmss)
    return table[columns]


def comparison_table(current: pd.DataFrame, previous: pd.DataFrame, sort_by: str, limit: int) -> pd.DataFrame:
    current_base = current[["Event", "Count", "Total_seconds", "Total Duration"]].copy()
    previous_base = previous[["Event", "Count", "Total_seconds"]].rename(
        columns={"Count": "Previous Count", "Total_seconds": "Previous seconds"}
    )

    table = current_base.merge(previous_base, on="Event", how="left")
    table["Previous Count"] = table["Previous Count"].fillna(0).astype(int)
    table["Previous seconds"] = table["Previous seconds"].fillna(0.0)

    if sort_by == "duration":
        table = table.sort_values(["Total_seconds", "Count"], ascending=False)
        delta = table["Total_seconds"] - table["Previous seconds"]
    else:
        table = table.sort_values(["Count", "Total_seconds"], ascending=False)
        delta = table["Count"] - table["Previous Count"]

    table = table.head(limit).copy()
    table["Comparison to previous quarter"] = delta.loc[table.index].map(
        lambda value: "UP" if value > 0 else "DOWN" if value < 0 else "-"
    )
    return table[["Event", "Count", "Total Duration", "Comparison to previous quarter"]]
