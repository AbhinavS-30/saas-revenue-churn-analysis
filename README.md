# SaaS Revenue & Churn Health Dashboard

**Status:** SQL/Python analysis layer, local AI summary, and Streamlit
companion page are built and verified. **The Tableau dashboard (Stage 5)
is still pending** — built manually in Tableau Public from the CSVs in
`data/processed/`, not scripted, so it isn't done automatically by
anything in this repo. The [Charts](#charts) below are the Python-side
equivalents in the meantime; swap in the live Tableau link/embed once
published (`streamlit_app/config.py`).

## Problem statement

I'm supporting a VP of Customer Success at a mid-size SaaS company who
needs a straight answer to one question: **is this business actually
growing in a healthy way, or is churn quietly eating our gains — and
which customer segments need intervention right now?**

That splits into three parts, each answered with its own layer of this
project:

1. **Are we growing?** — the monthly MRR trend, broken into new,
   expansion, contraction, and churned revenue (not just a single
   top-line number)
2. **Are we leaking?** — gross MRR churn, net MRR churn, and net
   revenue retention (NRR), calculated as three genuinely distinct
   metrics rather than blended into one
3. **Where's the risk concentrated?** — cohort retention and
   segment-level breakdowns, backed by a hypothesis test rather than an
   eyeballed guess

This is an analyst deliverable, not a data science project: the rigor
comes from correct SQL, correctly defined financial metrics, and light
statistical testing — not from machine learning. There is no predictive
model here.

## Approach

Full pipeline: a Kaggle SaaS dataset loaded into Postgres (Docker) →
metrics built in SQL (the core of the project) → light EDA and two
hypothesis tests in Python → a Tableau dashboard → a local LLM
(Ollama) generating a plain-English executive summary → a Streamlit
page presenting the AI summary alongside the dashboard. Every tool used
has a genuinely free tier; nothing in this project costs money to
reproduce. Full technical detail — dataset, schema decisions, data
quality issues found and fixed, setup instructions — is in the
[Engineering Notes](#engineering-notes) section below; this section and
the next two are the business-facing summary.

## Key findings

1. **MRR grew from $4.5K (Jan 2023) to a peak of $1.17M (Nov 2024)** —
   steady month-over-month growth for nearly the entire window — **but
   December 2024 is the first month MRR actually declines** ($1.173M →
   $1.151M), driven by the single largest churned-MRR figure in the
   whole dataset (-$185,954). New + expansion revenue that month
   ($443K) wasn't enough to offset contraction + churn (-$466K).

2. **Gross and net MRR churn tell different stories, and both are
   true at once.** Gross MRR churn averages 28.3%/month, but net MRR
   churn averages only 8.2%/month (avg NRR: 91.8%) — expansion revenue
   is consistently offsetting roughly 70% of gross losses. 3 of 23
   measurable months even had *negative* net churn (NRR > 100%). A
   dashboard that only reports one of these numbers would mislead
   leadership in one direction or the other. (Note: the *absolute*
   magnitude of gross churn here is high for a real-world SaaS
   benchmark — this dataset models an early pilot-stage startup with
   unusually high turnover, per its own documentation. The
   **relationship** between gross and net — net consistently well
   below gross — is the transferable finding; the magnitude is a
   dataset characteristic, not an industry norm.)

3. **Plan tier does not predict churn. Industry does.** Logo churn by
   plan tier is nearly identical — Enterprise 22.1%, Basic 22.0%, Pro
   21.9% — confirmed with a chi-square test (p = 0.999, not
   significant). But churn by industry shows a real, statistically
   significant split: **DevTools churns at 31.0% vs Cybersecurity at
   16.0%** — nearly double (two-proportion z-test, p = 0.011). If
   Customer Success has to prioritize outreach, industry vertical is a
   far better signal than plan tier.

4. **Cohort retention is stable, not eroding with tenure** — once
   correctly anchored on each account's first subscription date rather
   than signup date (see Engineering Notes — this took a real
   correction), blended retention holds fairly flat around 80-85%
   through month 12. There's no steep early-onboarding cliff, which
   rules out "customers are abandoning us in their first 90 days" as
   the primary churn story.

## Business recommendation

**Re-target Customer Success outreach by industry vertical, not plan
tier, starting with DevTools accounts.** Plan tier — the dimension most
CS playbooks default to — carries no statistically meaningful signal in
this data (finding 3). Industry does, and the gap is large enough to
act on: DevTools accounts churn at roughly double the rate of the
best-performing vertical. A tier-based intervention program is
targeting the wrong axis entirely.

Three supporting actions:

- **Investigate the December 2024 churn spike specifically**, cutting
  it by industry before assuming it's broad-based — it's the largest
  single-month churn event in the dataset (finding 1), and if it's
  concentrated in DevTools, that corroborates finding 3 and sharpens
  the intervention target further.
- **Report gross and net MRR churn separately in every leadership
  update, not just NRR.** NRR alone (91.8% average) reads as
  comfortably healthy; it obscures that gross monthly losses are
  running 3-4x higher before expansion revenue papers over them
  (finding 2). Expansion is currently doing a lot of load-bearing work
  that a single soft quarter from top accounts could expose.
- **Deprioritize onboarding-focused retention fixes** in favor of the
  industry-vertical investigation — the flat cohort curve (finding 4)
  suggests the leak isn't concentrated in customers' first few months,
  so resources aimed at onboarding are less likely to move the number
  than a DevTools-specific root-cause investigation would.

## Charts

![MRR Waterfall](outputs/figures/01_mrr_waterfall.png)
![Gross vs Net MRR Churn](outputs/figures/02_gross_vs_net_churn.png)
![Cohort Retention Heatmap](outputs/figures/03_cohort_retention_heatmap.png)
![Segment Churn Comparison](outputs/figures/04_segment_churn_comparison.png)

## AI-generated executive summary (example, Dec 2024 data)

*Generated locally by `llama3.2:3b` via Ollama — see
[Local AI summary layer](#local-ai-summary-layer-ollama) below for what
this pattern is and how it was validated for factual accuracy.*

> Our latest month's MRR ended at $1,150,514, showing a month-over-month
> decline of $22,470 from the prior month's ending MRR. This represents
> a growth rate of -1.92% from the previous month. Notably, the
> expansion revenue from existing customers has offset some of the
> contraction revenue, leading to a net MRR churn rate of 17.58%, which
> is lower than the gross churn rate of 39.72%.
>
> The distinction between the two churn rates is attributed to the
> expansion revenue offsetting some of the losses. Expansion revenue
> from existing customers is the primary driver of this difference,
> rather than any other factor.
>
> In terms of churn patterns, the analysis reveals that plan tier does
> not meaningfully predict churn. The chi-square test result indicates
> that the tiers are essentially tied, with the Enterprise tier at
> 22.1%, Basic at 22.0%, and Pro at 21.9% — the difference between the
> tiers is not statistically significant.
>
> Segmenting the data by industry reveals a real trend: DevTools
> exhibits the highest churn rate at 31.0%, while Cybersecurity has the
> lowest at 16.0%.
>
> **Recommendation:** Customer Success should focus on proactively
> engaging with DevTools customers to understand the root causes of
> their churn and develop targeted retention strategies.

---

# Engineering Notes

Everything below is the technical supporting material — dataset,
schema, setup instructions, data quality decisions, and a stage-by-stage
build log. The business case above is the deliverable; this is how it
was built and how to reproduce it.

## Dataset

[RavenStack SaaS Subscription & Churn Analytics Dataset](https://www.kaggle.com/datasets/rivalytics/saas-subscription-and-churn-analytics-dataset)
by **River @ Rivalytics** (Kaggle, MIT-like license, fully synthetic —
credit to the original author as required by the license). Five
relational tables: `accounts`, `subscriptions` (with MRR/ARR and
upgrade/downgrade flags), `feature_usage` (time-series engagement),
`support_tickets`, and `churn_events`.

**Data profile:**
- accounts: 500 · subscriptions: 5,000 · feature_usage: 25,000 ·
  support_tickets: 2,000 · churn_events: 600
- Calendar coverage: **Jan 2023 – Dec 2024** (2 full years) across every
  table — enough for a real MRR trend and up to 24 months of cohort
  tracking on the earliest signups
- Churn is tracked at **three levels** that won't always agree:
  `accounts.churn_flag`, `subscriptions.churn_flag`, and a separate
  `churn_events` table (an account can have one churned subscription
  while remaining active overall, etc.) — reconciling these correctly
  was part of the SQL work, not a data quality issue left ignored

## Tech stack (all free)

- **PostgreSQL** (Docker) — the SQL layer where all metrics are built
- **Python** (pandas, scipy) — EDA and light statistical testing on top of
  the SQL outputs
- **Tableau Public** — the dashboard
- **Ollama** (local LLM, runs on-device) — generates a plain-English
  executive summary of the latest metrics, no API costs
- **Streamlit Community Cloud** — hosts a page presenting the AI summary
  alongside the dashboard. Ollama can't run on Streamlit's free hosting,
  so the summary is *pre-generated locally* on each data refresh and
  read from a saved file by the deployed app — a common, legitimate
  pattern for keeping a local-LLM step out of a hosting environment that
  can't run one, called out plainly rather than presented as live
  inference.
- **Docker** — reproducible environment for Postgres, and optionally the
  Streamlit app locally

## Repo structure

```
data/raw/          original Kaggle CSVs (not committed — see below)
data/processed/    SQL query outputs used by the Python/Tableau layers
sql/schema/        table DDL
sql/views/         reusable building-block views (clean subscription
                    timeline, calendar spine, account-month MRR grid)
sql/metrics/       MRR waterfall, gross/net churn + NRR, cohorts, segments
python/eda/        EDA + light statistics
python/ai_summary/ local Ollama summary generation script
dashboard/         Tableau workbook + screenshots
streamlit_app/     the Streamlit page + its Dockerfile
docker/            docker-compose.yml, Postgres init
outputs/           charts (committed) and generated AI summaries (committed)
```

**Raw** data isn't committed (see `.gitignore`) — the dataset is free
and one command away via the Kaggle API; instructions below.
`data/processed/*.csv`, `outputs/figures/*.png`, and
`outputs/summaries/*.json` **are** committed on purpose: the deployed
Streamlit app has no Postgres or pipeline behind it, so it can only read
whatever's actually in the repo — it reads `data/processed/*.csv`
directly for its interactive filters and `executive_summary.json` for
the AI summary, since it can't run Ollama itself. (Learned this the
hard way: the app worked locally but showed "No processed data found"
on first deploy, because `data/processed/` was still gitignored at the
time.) The figures are committed too, so the README is self-contained
on GitHub without anyone needing to run the pipeline.

## Getting the data

```bash
# one-time: put your Kaggle API token at ~/.kaggle/access_token (see
# kaggle.com/settings -> API -> Create New Token), then:
.venv/bin/kaggle datasets download -d rivalytics/saas-subscription-and-churn-analytics-dataset -p data/raw --unzip
```

## Running the database

```bash
cp .env.example .env        # fill in your own local credentials
docker compose -f docker/docker-compose.yml --env-file .env up -d

set -a; source .env; set +a
export PGPASSWORD="$POSTGRES_PASSWORD"
psql -h localhost -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f sql/schema/001_create_tables.sql
psql -h localhost -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f sql/schema/002_load_data.sql
```

Then apply the views and run the metric queries in `sql/views/` (in
numeric order) and `sql/metrics/` — or just run
`.venv/bin/python python/eda/eda_and_stats.py`, which executes all of
them against the database and produces the CSVs/charts/snapshot in one
pass.

### Data quality notes (found and handled during load)

- `feature_usage.usage_id` is **not actually unique** in the source CSV
  (21 of 25,000 rows reuse an ID across unrelated events). We use a
  surrogate `BIGSERIAL` primary key instead and keep `usage_id` as a
  plain reference column — flagged rather than silently forced through.
- `support_tickets.satisfaction_score` is stored as a decimal-formatted
  string (`"4.0"`) for what's really a 1–5 whole-number rating —
  `NUMERIC(2,1)` instead of `SMALLINT` to accept it as-is.
- Raw `subscriptions.end_date` is unreliable — 353 of 441 chained
  subscription pairs per account overlapped in the raw data (a source
  data-quality gap, not real concurrent plans). Fixed by deriving a
  trustworthy effective end date from each account's own event sequence
  (`sql/views/001_subscription_timeline.sql`) instead of trusting the
  raw column.
- `accounts.signup_date` means "account created," not "started paying"
  — 95% of accounts have a real gap (avg 33 days, up to 432) before
  their first subscription. Cohort retention is anchored on first
  *subscription* date instead; anchoring on signup_date produced an
  inverted, nonsensical retention curve (see build log, Stage 3).

## Running the Streamlit app locally

```bash
# venv (fast, for iterating on the app)
.venv/bin/streamlit run streamlit_app/app.py

# OR Docker (build context must be the repo ROOT, not streamlit_app/,
# since it needs requirements.txt and outputs/ from there)
docker build -f streamlit_app/Dockerfile -t saas-churn-streamlit .
docker run -p 8501:8501 saas-churn-streamlit
```
Free deployment (what's actually used in production): push to GitHub,
connect the repo at share.streamlit.io (free tier), set the main file
to `streamlit_app/app.py`. That deployment does NOT use the Dockerfile
above — Streamlit Community Cloud builds directly from
`requirements.txt`. The Dockerfile is for local reproducibility only,
consistent with this project's Docker-for-the-environment approach.

## Local AI summary layer (Ollama)

`python/ai_summary/generate_summary.py` uses **Ollama** running
`llama3.2:3b` locally (free, no API key, ~2GB model, runs comfortably on
an M-series Mac) to turn `outputs/summaries/metrics_snapshot.json` into
a plain-English executive summary, saved to
`outputs/summaries/executive_summary.json`.

**Why local, and why pre-generated rather than live:** Streamlit
Community Cloud's free tier can't run Ollama (no GPU/local model
hosting). So this script is meant to be run locally each time the data
refreshes — its only output is a small JSON file that gets committed
alongside the data, and the deployed Streamlit app just reads that file.
This is a legitimate, common real-world pattern for keeping a
local-inference step out of a hosting environment that can't run one —
the README is upfront about it rather than presenting it as live
per-visitor inference.

**A real limitation worth documenting, not hiding:** getting factually
reliable output from a 3B model took real iteration, not a one-shot
prompt. First draft invented a cause for the gross/net churn gap
("billing issues" — not in the data) and mislabeled the lowest-churn
industry as a churn problem. Second draft fixed the industry mix-up but
fabricated a dollar figure ($57,121) that didn't match either number it
had been given. The fix that actually worked: stop asking the model to
compare or calculate anything — precompute every ranking and every
derived number (highest/lowest industry, highest/lowest plan tier, the
exact dollar MRR delta) in Python and hand them over as stated facts,
leaving the model's job purely prose, not arithmetic or comparison. This
is a real constraint of small local models worth knowing before relying
on one for anything numeric.

## Build log

- **Stage 0** — Evaluated 3 candidate Kaggle datasets, chose RavenStack
  for having real MRR amounts, upgrade/downgrade flags (needed for a
  correct expansion/contraction waterfall), true calendar dates, and a
  time-series engagement table.
- **Stage 1** — Repo scaffolded, git initialized, Python 3.12 virtual
  environment created (Homebrew Python, not the older Apple-system
  3.9.6), Docker Desktop confirmed running natively on Apple Silicon
  (`linux/aarch64`, no emulation). Dataset pulled via Kaggle API,
  MIT-like license confirmed, row counts and date range validated
  against the source.
- **Stage 2** — Postgres 16 (arm64-native, no emulation) running in
  Docker via `docker-compose.yml`. Schema created across 5 tables with
  PK/FK constraints and indexes on join/filter columns. All 5 CSVs
  loaded via `\copy`; row counts and referential integrity (zero
  orphaned foreign keys) verified against source.
- **Stage 3** — MRR waterfall built and verified. Found that raw
  `subscription.end_date` is unreliable (see Data quality notes above),
  so built `subscription_timeline` (a view) to derive a trustworthy
  effective end date instead. Built on that: a `calendar_months` spine,
  an `account_month_mrr` grid, and the final waterfall — verified with
  zero arithmetic mismatches and zero month-to-month continuity breaks
  across all 24 months. Gross MRR churn, net MRR churn, and NRR built on
  top of the same classification view — verified the identity NRR% +
  Net Churn% = 100% holds with zero mismatches across every month.
  Cohort retention required correcting the anchor date (signup_date →
  first subscription date, see Data quality notes) after the first
  version produced an inverted, nonsensical curve. Segment breakdown:
  logo churn by plan tier (flat) and by industry (real spread), plus
  monthly MRR by current plan tier for Tableau's segment/date filters.
- **Stage 4** — Python EDA + light stats (`python/eda/eda_and_stats.py`).
  Deliberately thin: it runs the already-verified `.sql` files directly
  (one source of truth for metric logic, no reimplementation in
  pandas), exports 6 CSVs to `data/processed/` for Tableau, makes 4
  charts, and runs 2 hypothesis tests. Chart colors picked and verified
  colorblind-safe via the project's data-viz color validator (fixed
  categorical slot order, single-hue sequential ramp for the heatmap —
  not a rainbow colormap). Also writes
  `outputs/summaries/metrics_snapshot.json`, the structured input the
  Ollama summary reads.
- **Stage 5 (pending, not part of this repo's automation)** — Tableau
  dashboard: built directly in Tableau Public from the CSVs in
  `data/processed/` (`mrr_waterfall.csv`, `gross_net_churn_and_nrr.csv`,
  `cohort_retention.csv`, `segment_plan_tier_churn.csv`,
  `segment_monthly_mrr.csv`, `segment_industry_churn.csv`). Target: MRR
  trends, the churn/NRR distinction, a cohort retention heatmap, a
  segment comparison view; filterable by date range and segment. Once
  published, set the embed URL in `streamlit_app/config.py`.
- **Stage 6** — Ollama installed (Homebrew, arm64-native), `llama3.2:3b`
  pulled (~2GB). Summary generation script built and iterated until
  factually reliable (see "Local AI summary layer" above for what went
  wrong and the fix). Verified the final generated summary against the
  source numbers by hand — all figures and comparisons check out.
- **Stage 7** — Streamlit page (`streamlit_app/app.py`): a date-range
  slider + segment dimension selector (Plan Tier / Industry) that
  genuinely recompute the KPI tiles and re-render the charts (Altair,
  not static images) — not just a display page. Extended the SQL layer
  to support this: `account_month_mrr` now carries `industry` alongside
  `plan_tier`, and a new `07_segment_monthly_industry_mrr.sql` gives
  industry a monthly breakdown to filter by (industry is the dimension
  that's actually significant, so it's the more meaningful one to make
  interactive). Verified the filter logic directly (not just via the
  UI): confirmed KPI values genuinely differ across segment/date
  combinations, and caught a real edge case in testing — percent growth
  computed from a tiny starting base (e.g. 1 account, $931 MRR) produced
  a mathematically-correct-but-meaningless "+25,070%"; added a minimum-
  base guard that shows "n/a (base too small)" instead. The AI summary
  and Tableau embed remain intentionally static/non-reactive to these
  filters — the page is explicit about which parts are live and which
  aren't. Smoke-tested locally (HTTP 200, no errors).
- **Stage 8** — `streamlit_app/Dockerfile` added for local
  reproducibility (`python:3.12-slim`, official multi-arch image, pulls
  natively on Apple Silicon). Built and ran it: confirmed `linux/arm64`
  (no emulation) and HTTP 200 serving correctly. Postgres remains the
  only service Docker actually runs in production use of this project;
  the Streamlit Dockerfile is for local dev only.
- **Stage 9 (in progress)** — This README restructured into case-study
  form (problem statement / approach / findings / recommendation up
  top, engineering detail below); pushing to GitHub next.
