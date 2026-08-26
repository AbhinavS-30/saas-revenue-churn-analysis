# SaaS Revenue & Churn Health Dashboard

**Status:** 🚧 In progress — Stage 1 (environment setup)

## Business context

I'm supporting a VP of Customer Success at a mid-size SaaS company. The
question on the table: **is this business actually growing in a healthy
way, or is churn quietly eating our gains — and which customer segments
need intervention right now?**

That splits into three parts, each answered with its own layer of this
project:

1. **Are we growing?** — monthly MRR trend (new / expansion / contraction / churned)
2. **Are we leaking?** — gross MRR churn, net MRR churn, and net revenue
   retention (NRR), calculated as three distinct metrics, not conflated
3. **Where's the risk concentrated?** — cohort retention and segment-level
   breakdowns, with a hypothesis test on churn differences between segments

This is an analyst project: the rigor comes from correct SQL, correctly
defined financial metrics, and light statistical testing — not from
machine learning. There is no predictive model here.

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
  while remaining active overall, etc.) — reconciling these correctly is
  part of the SQL work in Stage 3, not a data quality issue to ignore

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
  can't run one, and it's called out plainly rather than presented as
  live inference.
- **Docker** — reproducible environment for Postgres (and later, the app)

## Repo structure

```
data/raw/          original Kaggle CSVs (not committed — see below)
data/processed/    SQL query outputs used by the Python/Tableau layers
sql/schema/        table DDL
sql/metrics/       MRR waterfall, gross/net churn + NRR, cohorts, segments
python/eda/        EDA + light statistics
python/ai_summary/ local Ollama summary generation script
dashboard/         Tableau workbook + screenshots
streamlit_app/     the Streamlit page
docker/            docker-compose.yml, Postgres init
outputs/           charts and generated AI summaries
```

Raw and processed data aren't committed to the repo (see `.gitignore`) —
the dataset is free and one command away via the Kaggle API; instructions
below.

## Getting the data

```bash
# one-time: put your Kaggle API token at ~/.kaggle/kaggle.json (see
# kaggle.com/settings -> API -> Create New Token), then:
.venv/bin/kaggle datasets download -d rivalytics/saas-subscription-and-churn-analytics-dataset -p data/raw --unzip
```

## Progress log

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

## Key findings

*(filled in once the SQL metrics layer is built)*

## Business recommendation

*(filled in at the end, once findings are in)*
