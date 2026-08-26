-- RavenStack schema: 5 tables mirroring the source CSVs.
-- Written to be re-runnable (DROP ... IF EXISTS) so we can rebuild
-- cleanly whenever the data refreshes.
--
-- Types: raw string IDs (e.g. 'A-2e4581') kept as TEXT rather than
-- forced into UUID/INT — that's genuinely what they are, and there's
-- no benefit to reformatting them. Money columns are NUMERIC, never
-- FLOAT, so cent-level MRR math doesn't drift.

DROP TABLE IF EXISTS churn_events CASCADE;
DROP TABLE IF EXISTS support_tickets CASCADE;
DROP TABLE IF EXISTS feature_usage CASCADE;
DROP TABLE IF EXISTS subscriptions CASCADE;
DROP TABLE IF EXISTS accounts CASCADE;

CREATE TABLE accounts (
    account_id      TEXT PRIMARY KEY,
    account_name    TEXT NOT NULL,
    industry        TEXT,
    country         TEXT,
    signup_date     DATE NOT NULL,
    referral_source TEXT,
    plan_tier       TEXT,
    seats           INTEGER,
    is_trial        BOOLEAN,
    churn_flag      BOOLEAN
);

CREATE TABLE subscriptions (
    subscription_id   TEXT PRIMARY KEY,
    account_id        TEXT NOT NULL REFERENCES accounts(account_id),
    start_date        DATE NOT NULL,
    end_date          DATE,                 -- NULL = still active
    plan_tier         TEXT,
    seats             INTEGER,
    mrr_amount        NUMERIC(12, 2),
    arr_amount        NUMERIC(12, 2),
    is_trial          BOOLEAN,
    upgrade_flag      BOOLEAN,
    downgrade_flag    BOOLEAN,
    churn_flag        BOOLEAN,
    billing_frequency TEXT,
    auto_renew_flag   BOOLEAN
);

-- usage_id is NOT used as the primary key: 21 of 25,000 rows in the
-- source CSV reuse an ID across genuinely different events (different
-- subscription/date/feature) — an ID-generation artifact upstream, not
-- a real natural key. We use a surrogate key instead and keep usage_id
-- as a plain, non-unique reference column.
CREATE TABLE feature_usage (
    usage_pk             BIGSERIAL PRIMARY KEY,
    usage_id              TEXT NOT NULL,
    subscription_id     TEXT NOT NULL REFERENCES subscriptions(subscription_id),
    usage_date           DATE NOT NULL,
    feature_name         TEXT,
    usage_count          INTEGER,
    usage_duration_secs  INTEGER,
    error_count          INTEGER,
    is_beta_feature      BOOLEAN
);

CREATE TABLE support_tickets (
    ticket_id                    TEXT PRIMARY KEY,
    account_id                   TEXT NOT NULL REFERENCES accounts(account_id),
    submitted_at                 TIMESTAMP NOT NULL,
    closed_at                    TIMESTAMP,
    resolution_time_hours        NUMERIC(10, 2),
    priority                     TEXT,
    first_response_time_minutes  INTEGER,
    -- NUMERIC not SMALLINT: source stores whole-number ratings as
    -- decimal strings ("4.0"), a formatting quirk from the generator,
    -- not a true fractional score.
    satisfaction_score           NUMERIC(2, 1),   -- 1-5, NULL = no response
    escalation_flag               BOOLEAN
);

CREATE TABLE churn_events (
    churn_event_id             TEXT PRIMARY KEY,
    account_id                 TEXT NOT NULL REFERENCES accounts(account_id),
    churn_date                 DATE NOT NULL,
    reason_code                TEXT,
    refund_amount_usd          NUMERIC(12, 2),
    preceding_upgrade_flag     BOOLEAN,
    preceding_downgrade_flag   BOOLEAN,
    is_reactivation             BOOLEAN,
    feedback_text                TEXT
);

-- Indexes on the columns we'll filter/join/group by constantly once we
-- get to the metrics queries (dates for monthly bucketing, FKs for joins).
CREATE INDEX idx_subscriptions_account_id   ON subscriptions(account_id);
CREATE INDEX idx_subscriptions_start_date   ON subscriptions(start_date);
CREATE INDEX idx_subscriptions_end_date     ON subscriptions(end_date);
CREATE INDEX idx_feature_usage_sub_id       ON feature_usage(subscription_id);
CREATE INDEX idx_feature_usage_usage_id     ON feature_usage(usage_id);
CREATE INDEX idx_feature_usage_usage_date   ON feature_usage(usage_date);
CREATE INDEX idx_support_tickets_account_id ON support_tickets(account_id);
CREATE INDEX idx_churn_events_account_id    ON churn_events(account_id);
CREATE INDEX idx_accounts_signup_date       ON accounts(signup_date);
