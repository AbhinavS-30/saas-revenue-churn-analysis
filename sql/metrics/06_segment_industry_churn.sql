-- Logo churn rate by industry — same idea as 04_segment_logo_churn.sql
-- but sliced on industry instead of plan_tier. Checked before building
-- Stage 4's hypothesis test: plan_tier showed almost no spread
-- (21.9-22.1%), industry shows a real one (DevTools 31.0% vs
-- Cybersecurity 16.0%) — this is the more useful comparison to test.

SELECT
    industry,
    COUNT(*) AS n_accounts,
    SUM(CASE WHEN churn_flag THEN 1 ELSE 0 END) AS n_churned,
    ROUND(100.0 * SUM(CASE WHEN churn_flag THEN 1 ELSE 0 END) / COUNT(*), 1) AS churn_rate_pct
FROM accounts
GROUP BY industry
ORDER BY churn_rate_pct DESC;
