# MFC Quarter Comparator

Streamlit dashboard for comparing the top MFC events between two quarters.

The app loads two `.xlsx` files, filters both quarters with the same rules, calculates TOP event tables by count and total duration, shows bar charts, and can generate a short AI summary with Gemini or OpenAI.

## Features

- Compare previous quarter vs analysed quarter.
- Fixed quarter date windows, so rows outside the selected quarter are rejected by `Begin` date.
- Shared filtering for both files.
- Aggregation by `Description` or `Description + Item`.
- TOP tables sorted by count and total duration.
- Dark dashboard layout with equal-height tables and bar charts.
- Optional AI summary:
  - Local summary without any API key.
  - Gemini summary with `GEMINI_API_KEY` or `GOOGLE_API_KEY`.
  - OpenAI summary with `OPENAI_API_KEY`.

## Input File Format

Upload two `.xlsx` files:

- `Previous quarter`
- `Analysed quarter`

Required columns, case-insensitive:

| Column | Meaning |
| --- | --- |
| `Begin` | Event start timestamp |
| `End` | Event end timestamp |
| `Item` | MFC item/chute identifier |
| `Description` | Event description |

The app reads the first sheet from each workbook.

## Filters

The same filters are applied to both quarters:

- `Jam Wasteline`
  - When disabled, excludes `Product jam` rows with `Item` from `301.010` to `317.030`.
- `Chute full return`
  - When disabled, excludes `Chute full` rows outside the `200-299` item range.
- `Return dimension events`
  - When disabled, excludes return-line dimension events on items `105.020` and `106.020`.
  - Covered events: `Product out of dimensions`, `Product too high`, `Product too long`, `Product too wide`.
- `Exclude outside 06:00-22:30`
- `Exclude Sundays`
- `Reject events longer than limit`
- Event multiselect filter

## Run Locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run mfc_quarter_comparator_app.py
```

Then open:

```text
http://localhost:8501
```

## Streamlit Cloud Deploy

Use this as the app entry point:

```text
mfc_quarter_comparator_app.py
```

The required packages are listed in:

```text
requirements.txt
```

## AI Secrets

AI is optional. The app works without any API key by using `Local summary`.

For Streamlit Cloud, add secrets in the app settings:

```toml
GEMINI_API_KEY = "your-gemini-key"
OPENAI_API_KEY = "your-openai-key"
```

Gemini also accepts:

```toml
GOOGLE_API_KEY = "your-gemini-key"
```

Do not commit real `.streamlit/secrets.toml` files.

Use `.streamlit/secrets.example.toml` only as a template.

## Gemini Models

The sidebar includes Gemini model choices, including:

- `gemini-3.5-flash`
- `gemini-3.1-flash-lite`
- custom model ID

Use model IDs, not marketing names.

## Repository Structure

```text
mfc_quarter_comparator_app.py   # Streamlit app entry point
mfc_data.py                     # XLSX parsing, filtering, aggregation
mfc_ai.py                       # Local/Gemini/OpenAI summary logic
mfc_ui.py                       # Dashboard styling, tables, charts
mfc_config.py                   # Constants and ranges
.streamlit/config.toml          # Streamlit dark theme
.streamlit/secrets.example.toml # Example secrets template
requirements.txt                # Python dependencies
```

## Notes

- Raw `.xlsx` files are ignored by Git.
- Local logs, virtual environments, caches, and real secrets are ignored by Git.
- The AI summary receives only prepared TOP tables, not raw workbook rows.
