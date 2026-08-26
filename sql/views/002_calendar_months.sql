-- calendar_months: one row per calendar month in our data's date range
-- (Jan 2023 - Dec 2024, confirmed during Stage 1 data validation).
-- Reused by every metric that needs a "for each month..." backbone —
-- the MRR waterfall now, cohort tracking later.

CREATE OR REPLACE VIEW calendar_months AS
SELECT
    d::date AS month_start,
    -- last day of the same month: jump to the 1st of the FOLLOWING
    -- month, then step back one day.
    (d + INTERVAL '1 month' - INTERVAL '1 day')::date AS month_end
FROM generate_series(
    DATE '2023-01-01',   -- first month in the data
    DATE '2024-12-01',   -- last month in the data
    INTERVAL '1 month'   -- step size: jump forward one calendar month each row
) AS d;
