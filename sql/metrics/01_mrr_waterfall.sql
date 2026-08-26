-- MRR Waterfall: Starting MRR, New, Expansion, Contraction, Churned,
-- Ending MRR, for every month in the data.
--
-- Methodology note (documented deliberately, not hidden): the very
-- first month (Jan 2023) has no prior month to compare against, so
-- account_mrr_changes treats every account's "prior MRR" as $0 for that
-- month only — any account with MRR in Jan 2023 is classified "New" by
-- definition, since we have no earlier history to know otherwise.
--
-- Refactored to build on the account_mrr_changes VIEW (sql/views/004)
-- rather than repeating the LAG/CASE classification inline — the
-- gross/net churn + NRR metrics reuse that exact same classification.

SELECT
    month_start,
    SUM(prior_mrr) AS starting_mrr,
    SUM(CASE WHEN movement_type = 'new'         THEN mrr_delta ELSE 0 END) AS new_mrr,
    SUM(CASE WHEN movement_type = 'expansion'   THEN mrr_delta ELSE 0 END) AS expansion_mrr,
    SUM(CASE WHEN movement_type = 'contraction' THEN mrr_delta ELSE 0 END) AS contraction_mrr,
    SUM(CASE WHEN movement_type = 'churned'     THEN mrr_delta ELSE 0 END) AS churned_mrr,
    SUM(current_mrr) AS ending_mrr
FROM account_mrr_changes
GROUP BY month_start
ORDER BY month_start;
