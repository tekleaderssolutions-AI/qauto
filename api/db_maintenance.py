from sqlalchemy import text

from db import get_engine


def ensure_indexes() -> None:
    """Create indexes on frequently filtered columns if they do not exist."""
    engine = get_engine()
    stmts = [
        "CREATE INDEX IF NOT EXISTS idx_vehicle_inventory_make ON vehicle_inventory(make)",
        "CREATE INDEX IF NOT EXISTS idx_vehicle_inventory_model ON vehicle_inventory(model)",
        "CREATE INDEX IF NOT EXISTS idx_vehicle_inventory_year ON vehicle_inventory(year)",
        "CREATE INDEX IF NOT EXISTS idx_vehicle_inventory_risk_flag ON vehicle_inventory(risk_flag)",
        "CREATE INDEX IF NOT EXISTS idx_customers_customer_id ON customers(customer_id)",
    ]
    with engine.begin() as conn:
        for stmt in stmts:
            conn.execute(text(stmt))


def ensure_materialized_views() -> None:
    """Create basic materialized views for KPIs and monthly trends (PostgreSQL)."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE MATERIALIZED VIEW IF NOT EXISTS market_kpis_summary AS
                SELECT
                    MAX(date) AS last_date,
                    MAX(overall_market_health_score) AS market_health_score
                FROM qatar_economic_indicators;
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE MATERIALIZED VIEW IF NOT EXISTS monthly_sales_trends AS
                SELECT
                    DATE_TRUNC('month', date_out) AS month,
                    COUNT(*) AS sales_count
                FROM historical_sales
                GROUP BY 1
                ORDER BY 1;
                """
            )
        )


def refresh_materialized_views() -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY market_kpis_summary"))
        conn.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY monthly_sales_trends"))

