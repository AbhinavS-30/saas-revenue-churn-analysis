-- Loads the RavenStack CSVs into the tables created by
-- 001_create_tables.sql. Uses \copy (a psql client-side meta-command,
-- not server-side COPY) so the file paths are resolved on whichever
-- machine is running psql, not inside the Docker container — no volume
-- mount needed. Must be run with psql's cwd at the repo root so the
-- relative paths below resolve correctly.
--
-- Load order matters: parents before children, to satisfy the foreign
-- keys (accounts before subscriptions/support_tickets/churn_events;
-- subscriptions before feature_usage).

\copy accounts        FROM 'data/raw/ravenstack_accounts.csv'        WITH (FORMAT csv, HEADER true)
\copy subscriptions   FROM 'data/raw/ravenstack_subscriptions.csv'   WITH (FORMAT csv, HEADER true)
-- feature_usage: usage_pk is a surrogate BIGSERIAL, not in the CSV, so
-- we list the target columns explicitly and let Postgres generate it.
\copy feature_usage (usage_id, subscription_id, usage_date, feature_name, usage_count, usage_duration_secs, error_count, is_beta_feature) FROM 'data/raw/ravenstack_feature_usage.csv' WITH (FORMAT csv, HEADER true)
\copy support_tickets FROM 'data/raw/ravenstack_support_tickets.csv' WITH (FORMAT csv, HEADER true)
\copy churn_events     FROM 'data/raw/ravenstack_churn_events.csv'     WITH (FORMAT csv, HEADER true)
