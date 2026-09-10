"""
EDA + light statistics on top of the SQL metrics layer.

Deliberately thin: every number here is already computed and verified in
SQL (sql/metrics/*.sql) — this script does NOT recompute metric logic in
pandas. It (1) runs those exact .sql files against Postgres so there is
one source of truth for metric definitions, (2) saves the results as CSVs
for Tableau, (3) makes a few trend/comparison charts, (4) runs two
hypothesis tests on segment churn differences, and (5) writes a JSON
snapshot of the latest figures for the Stage 6 Ollama summary step.

Run from the repo root: .venv/bin/python python/eda/eda_and_stats.py
"""

import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from dotenv import load_dotenv
from scipy import stats
from sqlalchemy import create_engine, text

# --- paths -------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = REPO_ROOT / "sql" / "metrics"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
FIGURES_DIR = REPO_ROOT / "outputs" / "figures"
SUMMARIES_DIR = REPO_ROOT / "outputs" / "summaries"
for d in (PROCESSED_DIR, FIGURES_DIR, SUMMARIES_DIR):
    d.mkdir(parents=True, exist_ok=True)

# --- palette (validated via the dataviz skill's colorblind-safety
# checker — see conversation log; slots used in fixed order, never
# reassigned per-chart) ---------------------------------------------------
BLUE, ORANGE, AQUA, YELLOW, MAGENTA = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4",
)
INK = "#0b0b0b"
MUTED = "#898781"
GRID = "#e1e0d9"
SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#5598e7", "#2a78d6", "#184f95"]

plt.rcParams.update({
    "font.family": "sans-serif",
    "axes.edgecolor": MUTED,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.6,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": "#fcfcfb",
    "axes.facecolor": "#fcfcfb",
})


def get_engine():
    load_dotenv(REPO_ROOT / ".env")
    user = os.environ["POSTGRES_USER"]
    pw = os.environ["POSTGRES_PASSWORD"]
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ["POSTGRES_PORT"]
    db = os.environ["POSTGRES_DB"]
    return create_engine(f"postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}")


def run_metric(engine, filename: str) -> pd.DataFrame:
    """Execute one of our already-verified .sql files and return the result.
    Keeps metric logic living in exactly one place (SQL), not duplicated here."""
    sql_text = (SQL_DIR / filename).read_text()
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql_text), conn)


def main():
    engine = get_engine()

    print("Pulling metric outputs from Postgres...")
    waterfall = run_metric(engine, "01_mrr_waterfall.sql")
    churn_nrr = run_metric(engine, "02_gross_net_churn_and_nrr.sql")
    cohort = run_metric(engine, "03_cohort_retention.sql")
    plan_tier_churn = run_metric(engine, "04_segment_logo_churn.sql")
    segment_mrr = run_metric(engine, "05_segment_monthly_mrr.sql")
    industry_churn = run_metric(engine, "06_segment_industry_churn.sql")
    segment_industry_mrr = run_metric(engine, "07_segment_monthly_industry_mrr.sql")

    for name, df in [
        ("mrr_waterfall", waterfall), ("gross_net_churn_and_nrr", churn_nrr),
        ("cohort_retention", cohort), ("segment_plan_tier_churn", plan_tier_churn),
        ("segment_monthly_mrr", segment_mrr), ("segment_industry_churn", industry_churn),
        ("segment_monthly_industry_mrr", segment_industry_mrr),
    ]:
        df.to_csv(PROCESSED_DIR / f"{name}.csv", index=False)
    print(f"Saved 7 CSVs to {PROCESSED_DIR}")

    # ---------------------------------------------------------------
    # Chart 1: MRR waterfall — stacked bars for the 4 movement types,
    # Ending MRR as a neutral-ink line (it's a running TOTAL, not
    # another category, so it stays out of the categorical palette).
    # ---------------------------------------------------------------
    wf = waterfall.copy()
    wf["month_start"] = pd.to_datetime(wf["month_start"])
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(wf["month_start"], wf["new_mrr"], width=20, color=BLUE, label="New")
    ax.bar(wf["month_start"], wf["expansion_mrr"], width=20, bottom=wf["new_mrr"],
           color=AQUA, label="Expansion")
    ax.bar(wf["month_start"], wf["contraction_mrr"], width=20, color=YELLOW, label="Contraction")
    ax.bar(wf["month_start"], wf["churned_mrr"], width=20,
           bottom=wf["contraction_mrr"], color=ORANGE, label="Churned")
    ax.plot(wf["month_start"], wf["ending_mrr"], color=INK, linewidth=2,
            marker="o", markersize=4, label="Ending MRR (total)")
    ax.axhline(0, color=MUTED, linewidth=0.8)
    ax.set_title("MRR Waterfall: monthly movement + ending balance")
    ax.set_ylabel("MRR ($)")
    ax.legend(frameon=False, ncol=5, loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "01_mrr_waterfall.png", dpi=150)
    plt.close(fig)

    # ---------------------------------------------------------------
    # Chart 2: Gross vs Net MRR churn rate — the core "not conflated"
    # distinction. Zero reference line marks where net churn goes
    # negative (expansion outweighing losses).
    # ---------------------------------------------------------------
    cn = churn_nrr.copy()
    cn["month_start"] = pd.to_datetime(cn["month_start"])
    cn = cn.dropna(subset=["gross_mrr_churn_rate_pct"])  # Jan 2023 has no prior base
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(cn["month_start"], cn["gross_mrr_churn_rate_pct"], color=BLUE,
            linewidth=2, marker="o", markersize=4, label="Gross MRR churn rate")
    ax.plot(cn["month_start"], cn["net_mrr_churn_rate_pct"], color=ORANGE,
            linewidth=2, marker="o", markersize=4, label="Net MRR churn rate")
    ax.axhline(0, color=MUTED, linewidth=0.8, linestyle="--")
    ax.set_title("Gross vs Net MRR Churn — two different questions, not one")
    ax.set_ylabel("% of starting MRR")
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "02_gross_vs_net_churn.png", dpi=150)
    plt.close(fig)

    # ---------------------------------------------------------------
    # Chart 3: Cohort retention heatmap — single-hue sequential ramp,
    # not a rainbow colormap.
    # ---------------------------------------------------------------
    coh = cohort.copy()
    coh["cohort_month"] = pd.to_datetime(coh["cohort_month"]).dt.strftime("%Y-%m")
    pivot = coh.pivot(index="cohort_month", columns="months_since_signup", values="retention_pct")
    fig, ax = plt.subplots(figsize=(13, 7))
    cmap = sns.color_palette(SEQ_BLUE, as_cmap=False)
    sns.heatmap(pivot, cmap=sns.light_palette(BLUE, as_cmap=True), annot=False,
                cbar_kws={"label": "Retention %"}, ax=ax, linewidths=0.5, linecolor="#fcfcfb")
    ax.set_title("Cohort Retention: % of cohort still active, by months since first subscription")
    ax.set_xlabel("Months since signup")
    ax.set_ylabel("Signup cohort (month)")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "03_cohort_retention_heatmap.png", dpi=150)
    plt.close(fig)

    # ---------------------------------------------------------------
    # Chart 4: Segment comparison — plan tier (flat) vs industry
    # (real spread), side by side to make the contrast visually obvious.
    # Direct value labels included (contrast-vs-surface WARN on some
    # slots means color alone isn't enough — labels are the relief).
    # ---------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    tier_colors = [BLUE, ORANGE, AQUA]
    ind_colors = [BLUE, ORANGE, AQUA, YELLOW, MAGENTA]

    ax = axes[0]
    bars = ax.bar(plan_tier_churn["plan_tier"], plan_tier_churn["churn_rate_pct"], color=tier_colors)
    ax.bar_label(bars, fmt="%.1f%%", padding=3)
    ax.set_title("Logo churn by plan tier\n(no real difference)")
    ax.set_ylabel("Churn rate %")
    ax.set_ylim(0, 35)

    ax = axes[1]
    ind_sorted = industry_churn.sort_values("churn_rate_pct", ascending=False)
    bars = ax.bar(ind_sorted["industry"], ind_sorted["churn_rate_pct"], color=ind_colors)
    ax.bar_label(bars, fmt="%.1f%%", padding=3)
    ax.set_title("Logo churn by industry\n(real spread: DevTools vs Cybersecurity)")
    ax.set_ylabel("Churn rate %")
    ax.set_ylim(0, 35)
    ax.tick_params(axis="x", rotation=20)

    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "04_segment_churn_comparison.png", dpi=150)
    plt.close(fig)
    print(f"Saved 4 charts to {FIGURES_DIR}")

    # ---------------------------------------------------------------
    # Hypothesis test 1: does churn differ by plan tier? (omnibus)
    # Chi-square test of independence on a 3x2 contingency table
    # (tier x churned/not-churned).
    # ---------------------------------------------------------------
    contingency_tier = plan_tier_churn.assign(
        n_not_churned=lambda d: d["n_accounts"] - d["n_churned"]
    )[["n_churned", "n_not_churned"]].values
    chi2, p_tier, dof, _ = stats.chi2_contingency(contingency_tier)
    print(f"\nTest 1 (plan tier, chi-square): chi2={chi2:.3f}, dof={dof}, p={p_tier:.4f}")

    # ---------------------------------------------------------------
    # Hypothesis test 2: DevTools vs Cybersecurity churn rate —
    # two-proportion z-test (the two most divergent industries).
    # ---------------------------------------------------------------
    row_a = industry_churn.loc[industry_churn["industry"] == "DevTools"].iloc[0]
    row_b = industry_churn.loc[industry_churn["industry"] == "Cybersecurity"].iloc[0]
    n1, x1 = int(row_a["n_accounts"]), int(row_a["n_churned"])
    n2, x2 = int(row_b["n_accounts"]), int(row_b["n_churned"])
    p1, p2 = x1 / n1, x2 / n2
    p_pool = (x1 + x2) / (n1 + n2)
    se = (p_pool * (1 - p_pool) * (1 / n1 + 1 / n2)) ** 0.5
    z = (p1 - p2) / se
    p_industry = 2 * (1 - stats.norm.cdf(abs(z)))
    print(f"Test 2 (DevTools {p1:.1%} vs Cybersecurity {p2:.1%}, two-proportion z-test): "
          f"z={z:.3f}, p={p_industry:.4f}")

    # ---------------------------------------------------------------
    # Metrics snapshot for Stage 6 (Ollama executive summary input)
    # ---------------------------------------------------------------
    latest = waterfall.iloc[-1]
    prior = waterfall.iloc[-2]
    latest_churn = churn_nrr.iloc[-1]
    mom_growth_pct = round(100 * (latest["ending_mrr"] - prior["ending_mrr"]) / prior["ending_mrr"], 2)

    snapshot = {
        "latest_month": str(latest["month_start"].date() if hasattr(latest["month_start"], "date") else latest["month_start"]),
        "ending_mrr": float(latest["ending_mrr"]),
        "prior_month_ending_mrr": float(prior["ending_mrr"]),
        "mrr_change_dollars": round(float(latest["ending_mrr"] - prior["ending_mrr"]), 2),
        "mom_mrr_growth_pct": mom_growth_pct,
        "new_mrr": float(latest["new_mrr"]),
        "expansion_mrr": float(latest["expansion_mrr"]),
        "contraction_mrr": float(latest["contraction_mrr"]),
        "churned_mrr": float(latest["churned_mrr"]),
        "gross_mrr_churn_rate_pct": float(latest_churn["gross_mrr_churn_rate_pct"]),
        "net_mrr_churn_rate_pct": float(latest_churn["net_mrr_churn_rate_pct"]),
        "nrr_pct": float(latest_churn["nrr_pct"]),
        "avg_gross_churn_pct_full_period": round(cn["gross_mrr_churn_rate_pct"].mean(), 1),
        "avg_net_churn_pct_full_period": round(cn["net_mrr_churn_rate_pct"].mean(), 1),
        "avg_nrr_pct_full_period": round(cn["nrr_pct"].mean(), 1),
        "plan_tier_churn": plan_tier_churn.to_dict(orient="records"),
        "industry_churn": industry_churn.to_dict(orient="records"),
        "hypothesis_tests": {
            "plan_tier_chi_square": {"chi2": round(chi2, 3), "dof": int(dof), "p_value": round(p_tier, 4),
                                      "significant_at_0.05": bool(p_tier < 0.05)},
            "devtools_vs_cybersecurity_churn_ztest": {
                "devtools_churn_pct": round(p1 * 100, 1), "cybersecurity_churn_pct": round(p2 * 100, 1),
                "z": round(z, 3), "p_value": round(p_industry, 4), "significant_at_0.05": bool(p_industry < 0.05),
            },
        },
    }
    with open(SUMMARIES_DIR / "metrics_snapshot.json", "w") as f:
        json.dump(snapshot, f, indent=2)
    print(f"\nSaved metrics snapshot to {SUMMARIES_DIR / 'metrics_snapshot.json'}")


if __name__ == "__main__":
    main()
