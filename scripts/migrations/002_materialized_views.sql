-- Optional: materialized views for KPI/trend aggregation (refresh via APScheduler).
-- Run only after 001_add_indexes.sql and when tables exist.
-- psql $DATABASE_URL -f scripts/migrations/002_materialized_views.sql

-- Example: refresh every 6h via API scheduler
-- CREATE MATERIALIZED VIEW IF NOT EXISTS market_kpis_mv AS
-- SELECT
--   (SELECT COUNT(*) FROM vehicle_inventory) AS total_inventory,
--   (SELECT AVG(list_price_qar) FROM vehicle_inventory WHERE list_price_qar > 0) AS avg_price,
--   (SELECT overall_market_health_score FROM qatar_economic_indicators ORDER BY date DESC LIMIT 1) AS market_health_score;

-- CREATE MATERIALIZED VIEW IF NOT EXISTS monthly_trends_mv AS
-- SELECT
--   DATE_TRUNC('month', date_out)::date AS month,
--   COUNT(*) AS sales_volume,
--   AVG(sale_price_qar) AS avg_price
-- FROM historical_sales
-- WHERE date_out IS NOT NULL AND sale_price_qar > 0
-- GROUP BY 1
-- ORDER BY 1;

-- Refresh: REFRESH MATERIALIZED VIEW market_kpis_mv; REFRESH MATERIALIZED VIEW monthly_trends_mv;
