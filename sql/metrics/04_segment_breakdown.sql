-- Segment breakdown, two cuts:
--
-- (1) Logo churn rate by ORIGINAL signup plan_tier — uses accounts
--     directly (churn_flag = churned at any point in the whole window,
--     plan_tier = the tier they signed up on). This is the simple,
--     defensible cut for the Stage 4 hypothesis test: did some initial
--     tier retain customers worse than another?
--
-- (2) Monthly MRR by CURRENT plan_tier — uses account_month_mrr, so a
--     customer's revenue is attributed to whichever tier they're
--     actually on that month (post any upgrade/downgrade). This is
--     what feeds the Tableau segment + date-range filters.

-- (1) Logo churn rate by original signup tier
SELECT
    plan_tier,
    COUNT(*) AS n_accounts,
    SUM(CASE WHEN churn_flag THEN 1 ELSE 0 END) AS n_churned,
    ROUND(100.0 * SUM(CASE WHEN churn_flag THEN 1 ELSE 0 END) / COUNT(*), 1) AS churn_rate_pct
FROM accounts
GROUP BY plan_tier
ORDER BY churn_rate_pct DESC;
