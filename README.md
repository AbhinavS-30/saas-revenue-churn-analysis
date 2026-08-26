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
sql/views/         reusable building-block views (clean subscription
                    timeline, calendar spine, account-month MRR grid)
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

### Data quality notes (found and handled during load)

- `feature_usage.usage_id` is **not actually unique** in the source CSV
  (21 of 25,000 rows reuse an ID across unrelated events). We use a
  surrogate `BIGSERIAL` primary key instead and keep `usage_id` as a
  plain reference column — flagged rather than silently forced through.
- `support_tickets.satisfaction_score` is stored as a decimal-formatted
  string (`"4.0"`) for what's really a 1–5 whole-number rating —
  `NUMERIC(2,1)` instead of `SMALLINT` to accept it as-is.

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
- **Stage 2** — Postgres 16 (arm64-native, no emulation) running in
  Docker via `docker-compose.yml`. Schema created across 5 tables with
  PK/FK constraints and indexes on join/filter columns. All 5 CSVs
  loaded via `\copy`; row counts and referential integrity (zero
  orphaned foreign keys) verified against source.
- **Stage 3 (in progress)** — MRR waterfall built and verified. Found
  that raw `subscription.end_date` is unreliable (353 of 441 chained
  subscription pairs per account overlapped in the raw data — a source
  data-quality gap, not a real business scenario of concurrent plans),
  so built `subscription_timeline` (a view) to derive a trustworthy
  effective end date from each account's own event sequence instead.
  Built on that: a `calendar_months` spine, an `account_month_mrr` grid,
  and the final waterfall — verified with zero arithmetic mismatches
  and zero month-to-month continuity breaks across all 24 months.
  Still to build: gross/net MRR churn + NRR, cohort retention, segment
  breakdowns. Open question flagged for later: some subscription rows
  carry `mrr_amount = 0` (appear to be trial periods) — need a
  documented rule for how these count before we get to churn/NRR.

## Key findings

*(more to be added as the remaining metrics are built)*

- MRR grew from $4.5K (Jan 2023) to a peak of $1.17M (Nov 2024) — steady
  month-over-month growth for nearly the entire window.
- **December 2024 is the first month MRR actually declines** ($1.173M →
  $1.151M), driven by the single largest churned-MRR figure in the whole
  dataset (-$185,954) — new + expansion revenue ($443K) wasn't enough to
  offset contraction + churn (-$466K) that month. Worth investigating
  which segment(s) drove this once the segment breakdowns are built.

## Business recommendation

*(filled in at the end, once findings are in)*
