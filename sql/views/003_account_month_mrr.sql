-- account_month_mrr: one row per (account, month), with that account's
-- MRR as of the LAST DAY of the month (an end-of-month snapshot — the
-- standard convention for a monthly waterfall, and it lines up cleanly
-- with effective_end_date since that's also defined in whole days).
--
-- 500 accounts x 24 months = 12,000 rows. mrr = 0 for any month before
-- signup or after full churn (no matching subscription_timeline row).

CREATE OR REPLACE VIEW account_month_mrr AS
SELECT
    cm.month_start,
    a.account_id,
    -- COALESCE turns "no matching subscription row" (NULL from the LEFT
    -- JOIN) into an explicit 0 — an account with nothing active that
    -- month contributes $0 MRR, not a missing/unknown value.
    COALESCE(SUM(st.mrr_amount), 0) AS mrr
FROM accounts a
-- CROSS JOIN pairs every account with every month, so every account
-- gets a row for all 24 months even if they signed up partway through
-- (guaranteeing a full grid — this is what lets us COALESCE gaps to 0
-- instead of having "missing" months for late signups).
CROSS JOIN calendar_months cm
LEFT JOIN subscription_timeline st
    ON st.account_id = a.account_id
    -- "active as of month_end": started on or before month_end, AND
    -- either still open (NULL effective_end_date) or didn't end before
    -- month_end. Because piece 1 already removed all overlaps, at most
    -- ONE subscription_timeline row can match per account per month —
    -- so this SUM never double-counts.
   AND st.start_date <= cm.month_end
   AND (st.effective_end_date IS NULL OR st.effective_end_date >= cm.month_end)
GROUP BY cm.month_start, a.account_id;
