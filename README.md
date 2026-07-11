# MFC Quarter Report

Streamlit app for comparing TOP MFC events between two quarters.

## Run locally

```powershell
pip install -r requirements.txt
streamlit run mfc_quarter_comparator_app.py
```

## Deploy on Streamlit Cloud

Use `mfc_quarter_comparator_app.py` as the app entry point.

Optional AI summary secrets:

```toml
GEMINI_API_KEY = "your-gemini-key"
OPENAI_API_KEY = "your-openai-key"
```

Do not commit real `.streamlit/secrets.toml` files.
