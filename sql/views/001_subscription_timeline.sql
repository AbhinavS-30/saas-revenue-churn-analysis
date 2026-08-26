-- subscription_timeline: one row per subscription, with a trustworthy
-- "effective_end_date" — because the raw end_date column is unreliable
-- (many rows that were clearly superseded by a later subscription for
-- the same account never got their end_date populated; see README).
--
-- Rule: a subscription's effective end is whichever comes first —
-- (a) its own recorded end_date, or
-- (b) the day before the NEXT subscription for that account starts.
-- If neither exists (no end_date, no later subscription), effective_end_date
-- is NULL, meaning "still active."

CREATE OR REPLACE VIEW subscription_timeline AS
WITH ordered_subscriptions AS (
    -- Step 1: for every subscription row, look ahead to find the start
    -- date of the NEXT subscription belonging to the same account.
    -- PARTITION BY account_id resets the "look ahead" per account, so we
    -- never leak one account's dates into another's.
    -- ORDER BY start_date is what makes "next" mean "chronologically next."
    SELECT
        subscription_id,
        account_id,
        start_date,
        end_date,
        plan_tier,
        mrr_amount,
        upgrade_flag,
        downgrade_flag,
        churn_flag,
        LEAD(start_date) OVER (
            PARTITION BY account_id
            ORDER BY start_date
        ) AS next_start_date
    FROM subscriptions
)
SELECT
    subscription_id,
    account_id,
    start_date,
    end_date,
    plan_tier,
    mrr_amount,
    upgrade_flag,
    downgrade_flag,
    churn_flag,
    next_start_date,
    -- Step 2: pick whichever end comes first.
    -- LEAST() in Postgres ignores NULLs and only returns NULL if BOTH
    -- inputs are NULL — so this naturally handles all 3 cases:
    --   end_date set, no next row      -> effective_end_date = end_date
    --   no end_date, next row exists   -> effective_end_date = next_start_date - 1
    --   neither exists (still active)  -> effective_end_date = NULL
    LEAST(end_date, next_start_date - 1) AS effective_end_date
FROM ordered_subscriptions;
