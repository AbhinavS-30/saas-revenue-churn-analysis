-- Monthly MRR by industry — mirrors 05_segment_monthly_mrr.sql (which
-- is by plan_tier) but sliced by industry instead. Added for the
-- Streamlit interactive filters (Stage 7): industry is the segment
-- dimension that actually showed a significant churn difference
-- (04/06), so it's the more meaningful one to let a viewer filter by
-- and watch the trend/KPIs actually change.

SELECT
    month_start,
    industry,
    COUNT(*) FILTER (WHERE mrr > 0) AS active_accounts,
    SUM(mrr) AS total_mrr,
    ROUND(AVG(mrr) FILTER (WHERE mrr > 0), 2) AS avg_mrr_per_account
FROM account_month_mrr
GROUP BY month_start, industry
ORDER BY month_start, industry;
