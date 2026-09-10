"""
Generates a plain-English executive summary from the latest metrics
snapshot, using Ollama (a local LLM runtime — the model runs entirely
on this machine, no API key, no per-call cost).

This is a deliberate architectural choice, not a shortcut: Streamlit
Community Cloud's free tier can't run Ollama, so this script is meant to
be run LOCALLY each time the data refreshes. Its only output is a small
JSON file (outputs/summaries/executive_summary.json) that gets committed
alongside the data — the deployed Streamlit app just reads that file. See
README for the full explanation of this pattern.

Run from the repo root (after eda_and_stats.py has produced
metrics_snapshot.json, and with `ollama serve` running):
  .venv/bin/python python/ai_summary/generate_summary.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_PATH = REPO_ROOT / "outputs" / "summaries" / "metrics_snapshot.json"
OUTPUT_PATH = REPO_ROOT / "outputs" / "summaries" / "executive_summary.json"
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2:3b"

SYSTEM_PROMPT = """You are a data analyst writing a short executive summary \
for a VP of Customer Success at a SaaS company. Write 3-4 short paragraphs \
in plain, direct English (no bullet points, no headers, no markdown). \
Use ONLY the numbers given to you below — never invent, round loosely, \
estimate, calculate, or GUESS AT A CAUSE for a figure that wasn't \
provided. Do not do arithmetic yourself: if a figure you want (a dollar \
change, a difference) isn't given to you directly below, describe the \
trend in words instead of stating a number for it. If you don't know why \
a number moved, say what moved, not why. Cover, in this \
order: (1) overall MRR trend and growth, (2) the distinction between \
gross and net MRR churn — net churn is lower than gross ONLY because \
expansion revenue from existing customers offsets some of the losses; \
do not attribute the gap to any other cause (billing, payments, etc. are \
NOT in this data), (3) the segment finding — cover BOTH tests, not just one: first state \
that plan tier does NOT meaningfully predict churn (the tiers are \
statistically tied, per the non-significant chi-square result), THEN \
state which named industry has the HIGHEST churn rate and which named \
industry has the LOWEST, using the exact percentages given — do not \
describe the lowest-churn industry as a churn problem, and (4) one concrete \
recommendation for where Customer Success should focus. Be honest about \
concerning signals — don't spin bad news as good. Output ONLY the summary \
itself — no preamble like "Here is a summary," no title, no sign-off."""


def build_user_prompt(m: dict) -> str:
    # Precompute the highest/lowest-churn industry in Python rather than
    # asking the model to find it by eye in a JSON list — a 3B model
    # doing that comparison itself picked the wrong one twice in testing
    # (see README). Deterministic code should own any real comparison;
    # the model's job is prose, not arithmetic.
    industries_sorted = sorted(m["industry_churn"], key=lambda r: r["churn_rate_pct"])
    lowest = industries_sorted[0]
    highest = industries_sorted[-1]
    tiers_sorted = sorted(m["plan_tier_churn"], key=lambda r: r["churn_rate_pct"])
    tier_lowest = tiers_sorted[0]
    tier_highest = tiers_sorted[-1]

    return f"""Latest month: {m['latest_month']}
Ending MRR: ${m['ending_mrr']:,.0f}
Prior month ending MRR: ${m['prior_month_ending_mrr']:,.0f}
Dollar change vs prior month: ${m['mrr_change_dollars']:,.0f} \
(use this exact figure if you state a dollar change — do not calculate your own)
Month-over-month MRR growth: {m['mom_mrr_growth_pct']}%
This month's New MRR: ${m['new_mrr']:,.0f}, Expansion: ${m['expansion_mrr']:,.0f}, \
Contraction: ${m['contraction_mrr']:,.0f}, Churned: ${m['churned_mrr']:,.0f}

This month's gross MRR churn rate: {m['gross_mrr_churn_rate_pct']}%
This month's net MRR churn rate: {m['net_mrr_churn_rate_pct']}%
This month's NRR: {m['nrr_pct']}%
Full 24-month average: gross churn {m['avg_gross_churn_pct_full_period']}%, \
net churn {m['avg_net_churn_pct_full_period']}%, NRR {m['avg_nrr_pct_full_period']}%

Segment test 1 — churn by plan tier: {json.dumps(m['plan_tier_churn'])}
The HIGHEST-churn plan tier is {tier_highest['plan_tier']} at {tier_highest['churn_rate_pct']}%.
The LOWEST-churn plan tier is {tier_lowest['plan_tier']} at {tier_lowest['churn_rate_pct']}%.
State exactly these two facts if you mention specific tiers — do not recompute or re-rank them yourself.
Chi-square test result: p = {m['hypothesis_tests']['plan_tier_chi_square']['p_value']} \
({'statistically significant' if m['hypothesis_tests']['plan_tier_chi_square']['significant_at_0.05'] else 'NOT statistically significant'}) \
— since this is NOT significant, emphasize that the tiers are essentially tied, not that one is meaningfully better

Segment test 2 — churn by industry: {json.dumps(m['industry_churn'])}
The HIGHEST-churn industry is {highest['industry']} at {highest['churn_rate_pct']}%.
The LOWEST-churn industry is {lowest['industry']} at {lowest['churn_rate_pct']}%.
State exactly these two facts — do not recompute or re-rank them yourself.
DevTools vs Cybersecurity two-proportion z-test: p = \
{m['hypothesis_tests']['devtools_vs_cybersecurity_churn_ztest']['p_value']} \
({'statistically significant' if m['hypothesis_tests']['devtools_vs_cybersecurity_churn_ztest']['significant_at_0.05'] else 'NOT statistically significant'})

Write the executive summary now."""


def main():
    if not SNAPSHOT_PATH.exists():
        raise SystemExit(
            f"{SNAPSHOT_PATH} not found — run python/eda/eda_and_stats.py first."
        )
    metrics = json.loads(SNAPSHOT_PATH.read_text())

    try:
        resp = requests.get("http://localhost:11434/api/version", timeout=3)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise SystemExit(
            "Could not reach Ollama at localhost:11434. Is it running? "
            "Start it with: brew services start ollama\n"
            f"(original error: {e})"
        )

    print(f"Generating summary with {MODEL}...")
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(metrics)},
        ],
        "stream": False,
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
    resp.raise_for_status()
    summary_text = resp.json()["message"]["content"].strip()

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "source_month": metrics["latest_month"],
        "summary": summary_text,
    }
    OUTPUT_PATH.write_text(json.dumps(output, indent=2))
    print(f"\nSaved executive summary to {OUTPUT_PATH}\n")
    print("--- Generated summary ---")
    print(summary_text)


if __name__ == "__main__":
    main()
