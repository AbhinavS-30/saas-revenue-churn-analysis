-- Cohort retention: group accounts by the month they became a PAYING
-- customer, track what % of each cohort is still active (any MRR > 0)
-- N months later. Classic long-format output — Tableau pivots this
-- into the retention heatmap (rows = cohort_month, columns =
-- months_since_signup, color = retention_pct).
--
-- Methodology note: cohort_month is anchored on each account's FIRST
-- SUBSCRIPTION start_date, not accounts.signup_date. Checked first:
-- 475 of 500 accounts (95%) have a real gap between signup_date and
-- their first subscription (avg 33 days, up to 432) — signup_date
-- means "account created," not "became a paying customer." Anchoring
-- on signup_date produced an inverted, nonsensical curve (11.8% at
-- month 0, RISING to 82% by month 17) purely because most accounts
-- hadn't started paying yet in their signup month. First-subscription
-- date is the standard, defensible basis for a retention curve.
--
-- Note this is naturally a triangle, not a full grid: a late cohort
-- only has a few months_since_signup values available before the
-- dataset's Dec 2024 cutoff. That's expected, not missing data.

WITH first_sub AS (
    SELECT account_id, MIN(start_date) AS first_sub_date
    FROM subscriptions
    GROUP BY account_id
),
cohorts AS (
    SELECT account_id, DATE_TRUNC('month', first_sub_date)::date AS cohort_month
    FROM first_sub
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(*) AS cohort_size
    FROM cohorts
    GROUP BY cohort_month
),
cohort_activity AS (
    SELECT
        c.cohort_month,
        amm.account_id,
        -- months_since_signup: whole-month difference between the
        -- account's cohort month and the month being observed.
        (EXTRACT(YEAR FROM amm.month_start)::int - EXTRACT(YEAR FROM c.cohort_month)::int) * 12
          + (EXTRACT(MONTH FROM amm.month_start)::int - EXTRACT(MONTH FROM c.cohort_month)::int)
          AS months_since_signup,
        (amm.mrr > 0) AS is_active
    FROM cohorts c
    JOIN account_month_mrr amm
      ON amm.account_id = c.account_id
     AND amm.month_start >= c.cohort_month   -- only track forward from signup
)
SELECT
    ca.cohort_month,
    ca.months_since_signup,
    cs.cohort_size,
    COUNT(*) FILTER (WHERE ca.is_active) AS active_accounts,
    ROUND(100.0 * COUNT(*) FILTER (WHERE ca.is_active) / cs.cohort_size, 1) AS retention_pct
FROM cohort_activity ca
JOIN cohort_sizes cs ON cs.cohort_month = ca.cohort_month
GROUP BY ca.cohort_month, ca.months_since_signup, cs.cohort_size
ORDER BY ca.cohort_month, ca.months_since_signup;
