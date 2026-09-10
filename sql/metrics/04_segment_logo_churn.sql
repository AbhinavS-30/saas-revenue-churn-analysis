-- Logo churn rate by ORIGINAL signup plan_tier. Uses accounts directly
-- (churn_flag = churned at any point in the whole window, plan_tier =
-- the tier they signed up on) — the simple, defensible cut used for the
-- Stage 4 hypothesis test: did one initial tier retain worse than another?

SELECT
    plan_tier,
    COUNT(*) AS n_accounts,
    SUM(CASE WHEN churn_flag THEN 1 ELSE 0 END) AS n_churned,
    ROUND(100.0 * SUM(CASE WHEN churn_flag THEN 1 ELSE 0 END) / COUNT(*), 1) AS churn_rate_pct
FROM accounts
GROUP BY plan_tier
ORDER BY churn_rate_pct DESC;
