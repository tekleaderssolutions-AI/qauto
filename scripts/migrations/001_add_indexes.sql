-- Qatar AI Platform — Add indexes on filter/sort columns (PostgreSQL).
-- Run: psql $DATABASE_URL -f scripts/migrations/001_add_indexes.sql

-- vehicle_inventory (used by /api/inventory, risk_scorer)
CREATE INDEX IF NOT EXISTS idx_vehicle_inventory_make ON vehicle_inventory(make);
CREATE INDEX IF NOT EXISTS idx_vehicle_inventory_model ON vehicle_inventory(model);
CREATE INDEX IF NOT EXISTS idx_vehicle_inventory_year ON vehicle_inventory(year);
CREATE INDEX IF NOT EXISTS idx_vehicle_inventory_days_in_stock ON vehicle_inventory(days_in_stock);
CREATE INDEX IF NOT EXISTS idx_vehicle_inventory_status ON vehicle_inventory(status);
CREATE INDEX IF NOT EXISTS idx_vehicle_inventory_body_type ON vehicle_inventory(body_type);
CREATE INDEX IF NOT EXISTS idx_vehicle_inventory_color ON vehicle_inventory(color_exterior);

-- customers (used by buyer_matcher, market KPIs)
CREATE INDEX IF NOT EXISTS idx_customers_customer_id ON customers(customer_id);
CREATE INDEX IF NOT EXISTS idx_customers_next_upgrade ON customers(next_upgrade_prediction);

-- competitor_pricing
CREATE INDEX IF NOT EXISTS idx_competitor_pricing_make ON competitor_pricing(make);
CREATE INDEX IF NOT EXISTS idx_competitor_pricing_model ON competitor_pricing(model);
CREATE INDEX IF NOT EXISTS idx_competitor_pricing_platform ON competitor_pricing(platform);
CREATE INDEX IF NOT EXISTS idx_competitor_pricing_listed_price ON competitor_pricing(listed_price_qar);

-- historical_sales (used by market trends, price predictor training)
CREATE INDEX IF NOT EXISTS idx_historical_sales_date_out ON historical_sales(date_out);
CREATE INDEX IF NOT EXISTS idx_historical_sales_make_model ON historical_sales(make, model);
