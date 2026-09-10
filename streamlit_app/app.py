"""
Streamlit companion page: AI executive summary + KPI tiles + the Tableau
dashboard, side by side.

IMPORTANT — how the AI summary gets here: this app does NOT call Ollama
itself (Streamlit Community Cloud's free tier has no local-model
hosting). The summary is generated LOCALLY, on your own machine, by
running python/ai_summary/generate_summary.py, which writes
outputs/summaries/executive_summary.json. That file is committed to the
repo, and this app just reads it. So the summary reflects whenever you
last ran that script locally, not the moment a visitor loads the page —
the timestamp on the page makes that explicit rather than implying live
inference. This is a common, legitimate pattern for combining a
local-only tool with free cloud hosting, not a workaround being hidden.

Run locally: .venv/bin/streamlit run streamlit_app/app.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from config import TABLEAU_PUBLIC_EMBED_URL

REPO_ROOT = Path(__file__).resolve().parents[1]
SUMMARY_PATH = REPO_ROOT / "outputs" / "summaries" / "executive_summary.json"
SNAPSHOT_PATH = REPO_ROOT / "outputs" / "summaries" / "metrics_snapshot.json"
FIGURES_DIR = REPO_ROOT / "outputs" / "figures"

st.set_page_config(page_title="SaaS Revenue & Churn Health", layout="wide")
st.title("SaaS Revenue & Churn Health Dashboard")
st.caption("Supporting the VP of Customer Success: is the business growing "
           "in a healthy way, or is churn quietly eating the gains?")


def load_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text())


snapshot = load_json(SNAPSHOT_PATH)
summary = load_json(SUMMARY_PATH)

# --- KPI tiles -----------------------------------------------------------
if snapshot:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ending MRR", f"${snapshot['ending_mrr']:,.0f}",
              f"{snapshot['mom_mrr_growth_pct']}% MoM")
    c2.metric("Gross MRR Churn", f"{snapshot['gross_mrr_churn_rate_pct']}%")
    c3.metric("Net MRR Churn", f"{snapshot['net_mrr_churn_rate_pct']}%")
    c4.metric("NRR", f"{snapshot['nrr_pct']}%")
else:
    st.warning(
        "No metrics snapshot found. Run `.venv/bin/python python/eda/eda_and_stats.py` "
        "locally first."
    )

st.divider()

left, right = st.columns([1, 1])

# --- AI executive summary -------------------------------------------------
with left:
    st.subheader("Executive Summary (AI-generated, locally)")
    if summary:
        generated_at = datetime.fromisoformat(summary["generated_at"])
        age = datetime.now(timezone.utc) - generated_at
        st.info(
            f"Generated locally by **{summary['model']}** via Ollama on "
            f"{generated_at.strftime('%Y-%m-%d %H:%M UTC')} "
            f"({age.days} day{'s' if age.days != 1 else ''} ago), covering data "
            f"through **{summary['source_month']}**. This is NOT computed live "
            f"per visitor — it reflects the last local refresh. "
            f"See the README for why."
        )
        st.write(summary["summary"])
    else:
        st.warning(
            "No AI summary found. Run `.venv/bin/python python/ai_summary/generate_summary.py` "
            "locally first (requires Ollama running)."
        )

# --- Tableau dashboard -----------------------------------------------------
with right:
    st.subheader("Interactive Dashboard (Tableau)")
    if TABLEAU_PUBLIC_EMBED_URL:
        st.components.v1.iframe(TABLEAU_PUBLIC_EMBED_URL, height=600, scrolling=True)
    else:
        st.warning(
            "Tableau dashboard not yet linked. Publish the workbook to Tableau "
            "Public (free), then set TABLEAU_PUBLIC_EMBED_URL in "
            "streamlit_app/config.py."
        )

st.divider()

# --- Supplementary charts (from the Python EDA pass) ------------------------
st.subheader("Supplementary charts")
chart_files = sorted(FIGURES_DIR.glob("*.png")) if FIGURES_DIR.exists() else []
if chart_files:
    cols = st.columns(2)
    for i, chart_path in enumerate(chart_files):
        cols[i % 2].image(str(chart_path), use_container_width=True)
else:
    st.caption("No charts found — run python/eda/eda_and_stats.py locally first.")
