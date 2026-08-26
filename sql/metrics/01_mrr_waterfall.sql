-- MRR Waterfall: Starting MRR, New, Expansion, Contraction, Churned,
-- Ending MRR, for every month in the data.
--
-- Methodology note (documented deliberately, not hidden): the very
-- first month (Jan 2023) has no prior month to compare against, so we
-- treat every account's "prior MRR" as $0 for that month only. Any
-- account with MRR in Jan 2023 is therefore classified as "New" in
-- that first month, by definition, since we have no earlier history to
-- know otherwise.

WITH account_changes AS (
    SELECT
        month_start,
        account_id,
        mrr AS current_mrr,
        -- Look at the SAME account's mrr value one row back (i.e. the
        -- previous month, because account_month_mrr is one row per
        -- account per month and we order by month_start).
        -- COALESCE(..., 0) supplies the "$0 prior" assumption for the
        -- first month described above.
        COALESCE(
            LAG(mrr) OVER (PARTITION BY account_id ORDER BY month_start),
            0
        ) AS prior_mrr
    FROM account_month_mrr
),
classified AS (
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
    FROM account_changes
)
-- Final rollup: one row per month. Conditional aggregation (SUM of a
-- CASE) is the SQL equivalent of a pivot table — turning the
-- movement_type CATEGORY into separate VALUE columns.
SELECT
    month_start,
    SUM(prior_mrr) AS starting_mrr,
    SUM(CASE WHEN movement_type = 'new'         THEN mrr_delta ELSE 0 END) AS new_mrr,
    SUM(CASE WHEN movement_type = 'expansion'   THEN mrr_delta ELSE 0 END) AS expansion_mrr,
    SUM(CASE WHEN movement_type = 'contraction' THEN mrr_delta ELSE 0 END) AS contraction_mrr,
    SUM(CASE WHEN movement_type = 'churned'     THEN mrr_delta ELSE 0 END) AS churned_mrr,
    SUM(current_mrr) AS ending_mrr
FROM classified
GROUP BY month_start
ORDER BY month_start;
