-- Gross MRR Churn, Net MRR Churn, and NRR — three DISTINCT metrics,
-- deliberately not conflated. All three are ratios over the same
-- underlying monthly totals, aggregated once here and reused for each.
--
-- Sign convention carried over from account_mrr_changes: contraction_mrr
-- and churned_mrr are already negative (current_mrr - prior_mrr when
-- current < prior). We negate them below so the churn RATES read as
-- positive percentages, the way they're reported in practice.

WITH monthly_totals AS (
    SELECT
        month_start,
        SUM(prior_mrr) AS starting_mrr,
        SUM(CASE WHEN movement_type = 'expansion'   THEN mrr_delta ELSE 0 END) AS expansion_mrr,
        SUM(CASE WHEN movement_type = 'contraction' THEN mrr_delta ELSE 0 END) AS contraction_mrr,
        SUM(CASE WHEN movement_type = 'churned'     THEN mrr_delta ELSE 0 END) AS churned_mrr
    FROM account_mrr_changes
    GROUP BY month_start
)
SELECT
    month_start,
    starting_mrr,
    expansion_mrr,
    contraction_mrr,
    churned_mrr,

    -- GROSS MRR CHURN RATE: revenue lost from the existing base
    -- (contraction + churn), completely ignoring expansion. This is the
    -- "how much is leaking, full stop" number — it can never be negative.
    -- NULLIF(starting_mrr, 0) turns a would-be division-by-zero (only
    -- possible in Jan 2023, which has no prior base) into a clean NULL
    -- instead of an error.
    ROUND(
        -(contraction_mrr + churned_mrr) / NULLIF(starting_mrr, 0) * 100,
        2
    ) AS gross_mrr_churn_rate_pct,

    -- NET MRR CHURN RATE: same losses, but netted against expansion.
    -- Can go NEGATIVE when expansion outweighs contraction + churn —
    -- "negative churn," the sign of a genuinely healthy SaaS base.
    ROUND(
        -(contraction_mrr + churned_mrr + expansion_mrr) / NULLIF(starting_mrr, 0) * 100,
        2
    ) AS net_mrr_churn_rate_pct,

    -- NRR: what % of last month's EXISTING-customer revenue survived
    -- into this month, expansion included. New MRR is excluded from
    -- this formula entirely, by construction — NRR is never "ending /
    -- starting," it only ever asks what happened to the customers who
    -- were already there. Note NRR = 100% - net_mrr_churn_rate_pct,
    -- always — they're the same fact expressed two ways. We compute it
    -- independently here (not derived from the column above) as a
    -- built-in cross-check.
    ROUND(
        (starting_mrr + expansion_mrr + contraction_mrr + churned_mrr) / NULLIF(starting_mrr, 0) * 100,
        2
    ) AS nrr_pct
FROM monthly_totals
ORDER BY month_start;
