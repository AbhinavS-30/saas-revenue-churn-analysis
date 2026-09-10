"""
Streamlit companion page: AI executive summary + an INTERACTIVE metrics
explorer (date-range + segment filters that actually recompute the KPI
tiles and re-render the charts) + the Tableau dashboard, side by side.

IMPORTANT — how the AI summary gets here: this app does NOT call Ollama
itself (Streamlit Community Cloud's free tier has no local-model
hosting). The summary is generated LOCALLY, on your own machine, by
running python/ai_summary/generate_summary.py, which writes
outputs/summaries/executive_summary.json. That file is committed to the
repo, and this app just reads it — so the summary text itself is static
per deploy, not regenerated per visitor. The KPI tiles and charts below
it, by contrast, ARE genuinely live: they're computed from the
underlying CSVs on every filter change, in this app, in your browser
session. The timestamp banner makes the distinction between the two
explicit rather than blurring "AI-generated" and "interactively
computed" into one thing.

Run locally: .venv/bin/streamlit run streamlit_app/app.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from config import TABLEAU_PUBLIC_EMBED_URL

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
SUMMARY_PATH = REPO_ROOT / "outputs" / "summaries" / "executive_summary.json"
SNAPSHOT_PATH = REPO_ROOT / "outputs" / "summaries" / "metrics_snapshot.json"

# Palette validated for colorblind safety via the project's data-viz
# checker (see README) — fixed slot order, reused everywhere.
BLUE, ORANGE, AQUA, YELLOW, MAGENTA = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4",
)
INK = "#0b0b0b"

st.set_page_config(page_title="SaaS Revenue & Churn Health", layout="wide")
st.title("SaaS Revenue & Churn Health Dashboard")
st.caption("Supporting the VP of Customer Success: is the business growing "
           "in a healthy way, or is churn quietly eating the gains?")


@st.cache_data
def load_csv(name: str) -> pd.DataFrame | None:
    path = PROCESSED_DIR / f"{name}.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    for col in df.columns:
        if col.endswith("month") or col == "month_start":
            df[col] = pd.to_datetime(df[col])
    return df


def load_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text())


waterfall = load_csv("mrr_waterfall")
churn_nrr = load_csv("gross_net_churn_and_nrr")
plan_tier_churn = load_csv("segment_plan_tier_churn")
industry_churn = load_csv("segment_industry_churn")
segment_plan_mrr = load_csv("segment_monthly_mrr")
segment_industry_mrr = load_csv("segment_monthly_industry_mrr")
snapshot = load_json(SNAPSHOT_PATH)
summary = load_json(SUMMARY_PATH)

if waterfall is None:
    st.error("No processed data found. Run `.venv/bin/python python/eda/eda_and_stats.py` "
              "locally first, then reload.")
    st.stop()

# ============================================================
# CONTROLS — these actually drive everything below, live.
# ============================================================
st.subheader("Explore the metrics")
months = sorted(waterfall["month_start"].dt.strftime("%Y-%m").unique())

c1, c2 = st.columns([2, 1])
with c1:
    start_label, end_label = st.select_slider(
        "Date range", options=months, value=(months[0], months[-1])
    )
with c2:
    segment_dim = st.selectbox("Segment dimension", ["All accounts", "Plan Tier", "Industry"])

segment_value = None
if segment_dim == "Plan Tier":
    segment_value = st.selectbox("Plan tier", sorted(plan_tier_churn["plan_tier"].unique()))
elif segment_dim == "Industry":
    segment_value = st.selectbox("Industry", sorted(industry_churn["industry"].unique()))

start_date = pd.to_datetime(start_label)
end_date = pd.to_datetime(end_label)
wf = waterfall[(waterfall["month_start"] >= start_date) & (waterfall["month_start"] <= end_date)].copy()
cn = churn_nrr[(churn_nrr["month_start"] >= start_date) & (churn_nrr["month_start"] <= end_date)].copy()
cn_valid = cn.dropna(subset=["gross_mrr_churn_rate_pct"])

# ============================================================
# KPI TILES — recomputed from the filtered slice above, not fixed
# to "the latest month" the way a static report would be.
# ============================================================

# MIN_BASE_FOR_GROWTH: a percent-growth figure computed from a tiny
# starting base (e.g. 1 account, a few hundred dollars of MRR) is
# mathematically correct but statistically meaningless — a segment that
# grew from $931 to $234K is technically "+25,070%," and displaying
# that on a KPI tile reads as a bug even though the arithmetic is right.
# Below this threshold we show "n/a (base too small)" instead of the
# number. Found via testing: filtering to a narrow segment + early
# start date produced exactly this, before this guard was added.
MIN_BASE_FOR_GROWTH = 2000


def safe_growth_pct(start_val: float, end_val: float) -> float | None:
    if not start_val or start_val < MIN_BASE_FOR_GROWTH:
        return None
    return (end_val - start_val) / start_val * 100


def fmt_growth(pct: float | None) -> str:
    return f"{pct:.1f}%" if pct is not None else "n/a (base too small)"


st.divider()
k1, k2, k3, k4 = st.columns(4)

if segment_dim == "All accounts":
    ending_mrr = wf["ending_mrr"].iloc[-1]
    range_start_mrr = wf["starting_mrr"].iloc[0]
    growth_pct = safe_growth_pct(range_start_mrr, ending_mrr)
    k1.metric(f"Ending MRR ({end_label})", f"${ending_mrr:,.0f}")
    k2.metric("Growth over selected range", fmt_growth(growth_pct))
    k3.metric("Avg gross MRR churn (range)", f"{cn_valid['gross_mrr_churn_rate_pct'].mean():.1f}%")
    k4.metric("Avg net MRR churn (range)", f"{cn_valid['net_mrr_churn_rate_pct'].mean():.1f}%")
else:
    seg_col = "plan_tier" if segment_dim == "Plan Tier" else "industry"
    seg_mrr_df = segment_plan_mrr if segment_dim == "Plan Tier" else segment_industry_mrr
    seg_slice = seg_mrr_df[
        (seg_mrr_df[seg_col] == segment_value)
        & (seg_mrr_df["month_start"] >= start_date)
        & (seg_mrr_df["month_start"] <= end_date)
    ].sort_values("month_start")
    seg_churn_df = plan_tier_churn if segment_dim == "Plan Tier" else industry_churn
    seg_churn_row = seg_churn_df[seg_churn_df[seg_col] == segment_value].iloc[0]

    seg_ending = seg_slice["total_mrr"].iloc[-1] if len(seg_slice) else 0
    seg_start = seg_slice["total_mrr"].iloc[0] if len(seg_slice) else 0
    seg_growth = safe_growth_pct(seg_start, seg_ending)

    k1.metric(f"{segment_value} MRR ({end_label})", f"${seg_ending:,.0f}")
    k2.metric(f"{segment_value} growth over range", fmt_growth(seg_growth))
    k3.metric(f"{segment_value} logo churn (full period)", f"{seg_churn_row['churn_rate_pct']}%")
    k4.metric("Business-wide avg NRR (range, for context)", f"{cn_valid['nrr_pct'].mean():.1f}%")

st.divider()

# ============================================================
# CHARTS — Altair, so they're genuinely reactive to the controls
# above (not static images) and carry hover tooltips by default.
# ============================================================
left, right = st.columns(2)

with left:
    st.markdown("**MRR Waterfall** (selected range)")
    wf_long = wf.melt(
        id_vars=["month_start"],
        value_vars=["new_mrr", "expansion_mrr", "contraction_mrr", "churned_mrr"],
        var_name="movement_type", value_name="amount",
    )
    bar = alt.Chart(wf_long).mark_bar().encode(
        x=alt.X("month_start:T", title="Month"),
        y=alt.Y("amount:Q", title="MRR ($)"),
        color=alt.Color("movement_type:N",
                         scale=alt.Scale(domain=["new_mrr", "expansion_mrr", "contraction_mrr", "churned_mrr"],
                                          range=[BLUE, AQUA, YELLOW, ORANGE]),
                         legend=alt.Legend(title="Movement")),
        tooltip=["month_start:T", "movement_type:N", "amount:Q"],
    )
    line = alt.Chart(wf).mark_line(color=INK, point=True).encode(
        x="month_start:T", y="ending_mrr:Q", tooltip=["month_start:T", "ending_mrr:Q"],
    )
    st.altair_chart((bar + line).properties(height=350), width='stretch')

with right:
    st.markdown("**Gross vs Net MRR Churn** (selected range)")
    cn_long = cn_valid.melt(
        id_vars=["month_start"],
        value_vars=["gross_mrr_churn_rate_pct", "net_mrr_churn_rate_pct"],
        var_name="metric", value_name="pct",
    )
    chart = alt.Chart(cn_long).mark_line(point=True).encode(
        x=alt.X("month_start:T", title="Month"),
        y=alt.Y("pct:Q", title="% of starting MRR"),
        color=alt.Color("metric:N",
                         scale=alt.Scale(domain=["gross_mrr_churn_rate_pct", "net_mrr_churn_rate_pct"],
                                          range=[BLUE, ORANGE]),
                         legend=alt.Legend(title="")),
        tooltip=["month_start:T", "metric:N", "pct:Q"],
    ).properties(height=350)
    zero_line = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(strokeDash=[4, 4], color="#898781").encode(y="y:Q")
    st.altair_chart(chart + zero_line, width='stretch')

st.markdown(f"**MRR Trend — {segment_value if segment_value else 'All accounts'}** (selected range)")
if segment_dim == "All accounts":
    trend_chart = alt.Chart(wf).mark_line(point=True, color=BLUE).encode(
        x=alt.X("month_start:T", title="Month"),
        y=alt.Y("ending_mrr:Q", title="Ending MRR ($)"),
        tooltip=["month_start:T", "ending_mrr:Q"],
    ).properties(height=300)
else:
    trend_chart = alt.Chart(seg_slice).mark_line(point=True, color=BLUE).encode(
        x=alt.X("month_start:T", title="Month"),
        y=alt.Y("total_mrr:Q", title=f"{segment_value} MRR ($)"),
        tooltip=["month_start:T", "total_mrr:Q", "active_accounts:Q"],
    ).properties(height=300)
st.altair_chart(trend_chart, width='stretch')

st.markdown("**Logo churn by segment** (full period, all accounts — not date-filtered, since it's an ever-churned flag)")
churn_source = plan_tier_churn.rename(columns={"plan_tier": "segment"}) if segment_dim != "Industry" \
    else industry_churn.rename(columns={"industry": "segment"})
bar_colors = [BLUE, ORANGE, AQUA, YELLOW, MAGENTA][:len(churn_source)]
churn_bar = alt.Chart(churn_source).mark_bar().encode(
    x=alt.X("segment:N", title=None, sort="-y"),
    y=alt.Y("churn_rate_pct:Q", title="Churn rate %"),
    color=alt.Color("segment:N", scale=alt.Scale(range=bar_colors), legend=None),
    tooltip=["segment:N", "churn_rate_pct:Q", "n_accounts:Q", "n_churned:Q"],
).properties(height=280)
st.altair_chart(churn_bar, width='stretch')

st.divider()

# ============================================================
# AI executive summary + Tableau (unchanged: these two are NOT
# recomputed from the filters above — see module docstring)
# ============================================================
left2, right2 = st.columns([1, 1])

with left2:
    st.subheader("Executive Summary (AI-generated, locally — static, not filtered)")
    if summary:
        generated_at = datetime.fromisoformat(summary["generated_at"])
        age = datetime.now(timezone.utc) - generated_at
        st.info(
            f"Generated locally by **{summary['model']}** via Ollama on "
            f"{generated_at.strftime('%Y-%m-%d %H:%M UTC')} "
            f"({age.days} day{'s' if age.days != 1 else ''} ago), covering data "
            f"through **{summary['source_month']}**. This does NOT respond to the "
            f"filters above and is NOT computed live per visitor — see the README."
        )
        st.write(summary["summary"])
    else:
        st.warning(
            "No AI summary found. Run `.venv/bin/python python/ai_summary/generate_summary.py` "
            "locally first (requires Ollama running)."
        )

with right2:
    st.subheader("Interactive Dashboard (Tableau)")
    if TABLEAU_PUBLIC_EMBED_URL:
        st.components.v1.iframe(TABLEAU_PUBLIC_EMBED_URL, height=500, scrolling=True)
    else:
        st.warning(
            "Tableau dashboard not yet linked. Publish the workbook to Tableau "
            "Public (free), then set TABLEAU_PUBLIC_EMBED_URL in "
            "streamlit_app/config.py."
        )
