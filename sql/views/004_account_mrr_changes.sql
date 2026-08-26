-- account_mrr_changes: promotes the per-account month-over-month
-- classification logic (previously inline in 01_mrr_waterfall.sql) into
-- its own view, so both the waterfall AND the churn/NRR metrics can
-- build on the exact same classification without copy-pasting it.
-- Same "build once, reuse everywhere" idea as the earlier views.

CREATE OR REPLACE VIEW account_mrr_changes AS
WITH account_changes AS (
    SELECT
        month_start,
        account_id,
        mrr AS current_mrr,
        COALESCE(
            LAG(mrr) OVER (PARTITION BY account_id ORDER BY month_start),
            0
        ) AS prior_mrr
    FROM account_month_mrr
)
SELECT
    month_start,
    account_id,
    current_mrr,
    prior_mrr,
    (current_mrr - prior_mrr) AS mrr_delta,
    CASE
        WHEN prior_mrr = 0 AND current_mrr > 0 THEN 'new'
        WHEN prior_mrr > 0 AND current_mrr = 0 THEN 'churned'
        WHEN current_mrr > prior_mrr            THEN 'expansion'
        WHEN current_mrr < prior_mrr            THEN 'contraction'
        ELSE 'unchanged'
    END AS movement_type
FROM account_changes;
