-- Monthly MRR by CURRENT plan_tier (post any upgrade/downgrade) —
-- feeds Tableau's segment + date-range filters. Accounts with no active
-- subscription that month (plan_tier IS NULL) are excluded here since
-- they contribute $0 and don't belong to any tier that month.

SELECT
    month_start,
    plan_tier,
    COUNT(*) AS active_accounts,
    SUM(mrr) AS total_mrr,
    ROUND(AVG(mrr), 2) AS avg_mrr_per_account
FROM account_month_mrr
WHERE plan_tier IS NOT NULL
GROUP BY month_start, plan_tier
ORDER BY month_start, plan_tier;
