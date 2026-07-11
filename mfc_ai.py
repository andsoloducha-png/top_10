from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

import pandas as pd


DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"
GEMINI_MODEL_OPTIONS = (
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "Custom model...",
)
AI_SUMMARY_VERSION = "english-compact-cards-v4"


def resolve_openai_api_key(manual_key: str | None = None) -> str | None:
    if manual_key and manual_key.strip():
        return manual_key.strip()
    return os.getenv("OPENAI_API_KEY")


def resolve_gemini_api_key(manual_key: str | None = None) -> str | None:
    if manual_key and manual_key.strip():
        return manual_key.strip()
    return os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")


def build_local_summary(count_table: pd.DataFrame, duration_table: pd.DataFrame) -> str:
    if count_table.empty and duration_table.empty:
        return "No rows available for a summary."

    bullets: list[str] = []
    if not count_table.empty:
        row = count_table.iloc[0]
        bullets.append(f"- Count driver: **{row['Event']}** leads with **{row['Count']}** events.")

    if not duration_table.empty:
        row = duration_table.iloc[0]
        bullets.append(f"- Duration driver: **{row['Event']}** totals **{row['Total Duration']}**.")

    common = set(count_table.get("Event", [])) & set(duration_table.get("Event", []))
    if common:
        bullets.append(f"- Shared priority: **{len(common)}** events appear in both TOP tables.")

    trend_counts = _trend_counts(count_table, duration_table)
    increase_count = trend_counts["UP"]
    decrease_count = trend_counts["DOWN"]
    bullets.append(f"- Trend check: **{increase_count}** increases and **{decrease_count}** decreases.")

    return "\n".join(bullets)


def generate_gemini_summary(
    count_table: pd.DataFrame,
    duration_table: pd.DataFrame,
    api_key: str,
    model: str,
) -> str:
    model_path = model if model.startswith("models/") else f"models/{model}"
    model_path = urllib.parse.quote(model_path, safe="/")
    last_error = "Gemini did not return a complete summary."

    for max_tokens in (1024, 2048):
        try:
            return _request_gemini_summary(
                count_table,
                duration_table,
                api_key,
                model_path,
                max_tokens,
            )
        except RuntimeError as exc:
            last_error = str(exc)

    raise RuntimeError(last_error)


def generate_openai_summary(
    count_table: pd.DataFrame,
    duration_table: pd.DataFrame,
    api_key: str,
    model: str,
) -> str:
    payload = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": _summary_system_prompt(),
            },
            {
                "role": "user",
                "content": _summary_input(count_table, duration_table),
            },
        ],
        "temperature": 0.2,
        "max_output_tokens": 900,
    }

    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI request failed: HTTP {exc.code}. {details}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenAI request failed: {exc.reason}") from exc

    text = data.get("output_text")
    if text:
        summary = _normalize_summary_text(text)
        if _is_complete_summary(summary):
            return summary

    chunks: list[str] = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                chunks.append(content["text"])
    if chunks:
        summary = _normalize_summary_text("\n".join(chunks))
        if _is_complete_summary(summary):
            return summary

    raise RuntimeError("OpenAI returned an incomplete summary.")


def _request_gemini_summary(
    count_table: pd.DataFrame,
    duration_table: pd.DataFrame,
    api_key: str,
    model_path: str,
    max_tokens: int,
) -> str:
    payload = {
        "systemInstruction": {
            "parts": [{"text": _summary_system_prompt()}],
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": _summary_input(count_table, duration_table)}],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "candidateCount": 1,
            "maxOutputTokens": max_tokens,
        },
        "store": False,
    }

    request = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/{model_path}:generateContent?key={api_key}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini request failed: HTTP {exc.code}. {details}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Gemini request failed: {exc.reason}") from exc

    summary = _extract_gemini_text(data)
    if _is_complete_summary(summary):
        return summary

    raise RuntimeError("Gemini returned an incomplete summary.")


def _summary_system_prompt() -> str:
    return (
        "You are an operations analyst. Write an English executive summary for an MFC "
        "quarterly event report. Use only the provided tables. Do not invent causes. "
        "Return exactly 4 bullet lines and nothing else. Each line must start with '- '. "
        "Use this order: Count driver, Duration driver, Shared priority, Next focus. "
        "Each line must be 8 to 16 words. No markdown bold, no headings, no tables, no Polish words."
    )


def _summary_input(count_table: pd.DataFrame, duration_table: pd.DataFrame) -> str:
    return json.dumps(
        {
            "top_by_count": _table_records(count_table),
            "top_by_duration": _table_records(duration_table),
        },
        ensure_ascii=False,
    )


def _table_records(df: pd.DataFrame) -> list[dict[str, object]]:
    columns = ["Event", "Count", "Total Duration", "Comparison to previous quarter"]
    if df.empty:
        return []
    return df[columns].head(10).to_dict(orient="records")


def _trend_counts(count_table: pd.DataFrame, duration_table: pd.DataFrame) -> dict[str, int]:
    result = {"UP": 0, "DOWN": 0}
    for table in (count_table, duration_table):
        if "Comparison to previous quarter" in table:
            result["UP"] += int((table["Comparison to previous quarter"] == "UP").sum())
            result["DOWN"] += int((table["Comparison to previous quarter"] == "DOWN").sum())
    return result


def _extract_gemini_text(data: dict[str, object]) -> str:
    chunks: list[str] = []
    finish_reasons: list[str] = []

    for candidate in data.get("candidates", []):
        if not isinstance(candidate, dict):
            continue

        reason = candidate.get("finishReason")
        if isinstance(reason, str) and reason:
            finish_reasons.append(reason)

        content = candidate.get("content", {})
        if not isinstance(content, dict):
            continue

        parts = content.get("parts", [])
        if not isinstance(parts, list):
            continue

        for part in parts:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                chunks.append(part["text"].strip())

    bad_reasons = [
        reason
        for reason in finish_reasons
        if reason not in {"STOP", "FINISH_REASON_UNSPECIFIED"}
    ]
    if bad_reasons:
        raise RuntimeError(f"Gemini stopped before completing the summary: {', '.join(bad_reasons)}.")

    if chunks:
        return _normalize_summary_text("\n".join(chunks))

    direct = data.get("output_text") or data.get("outputText") or data.get("text")
    if isinstance(direct, str) and direct.strip():
        return _normalize_summary_text(direct)

    return ""


def _normalize_summary_text(text: str) -> str:
    lines = [line.strip().replace("**", "") for line in text.strip().splitlines() if line.strip()]
    clean_lines: list[str] = []

    for line in lines:
        line = line.strip("`").strip()
        line = re.sub(r"^\d+[\.)]\s*", "", line)
        if line.startswith(("- ", "* ")):
            line = line[2:].strip()
        elif line and not line[0].isalnum() and line[0] not in {"'", '"'}:
            line = line[1:].strip()
        line = line.strip(" -\t").strip()
        if line:
            clean_lines.append(f"- {line}")

    return "\n".join(clean_lines).strip()


def _is_complete_summary(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    bullet_lines = [line for line in lines if line.startswith("- ")]
    if len(bullet_lines) < 3:
        return False

    incomplete_end = re.compile(r"\b(and|or|with|over|under|from|to|than)\s+[\d,.:]*$", re.IGNORECASE)
    for line in bullet_lines[:4]:
        body = line[2:].strip()
        words = body.split()
        if len(words) < 5:
            return False
        if incomplete_end.search(body):
            return False

    return True
