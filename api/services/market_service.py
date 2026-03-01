"""Market service — KPIs, trends, events. No direct DB in routes; use this layer."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from db import get_engine, is_postgres
from sqlalchemy import text
import pandas as pd


def get_market_kpis() -> dict:
    """Aggregate market KPIs from DB."""
    out = {}
    try:
        engine = get_engine()
    except Exception:
        return out
    date_90 = "(CURRENT_DATE - INTERVAL '90 days')" if is_postgres() else "date('now','-90 days')"
    try:
        r = __run(engine, "SELECT overall_market_health_score FROM qatar_economic_indicators ORDER BY date DESC LIMIT 1")
        out["market_health_score"] = r[0][0] if r else 75
    except Exception:
        out["market_health_score"] = 75
    try:
        r = __run(engine, f"SELECT AVG(days_to_sell) FROM historical_sales WHERE body_type LIKE '%%SUV%%' AND date_out >= {date_90}")
        out["avg_days_to_sell_suv"] = round(r[0][0], 0) if r and r[0][0] is not None else 45
    except Exception:
        out["avg_days_to_sell_suv"] = 45
    try:
        r = __run(engine, "SELECT COUNT(*) FROM vehicle_inventory WHERE risk_flag = 'critical'")
        out["critical_inventory_count"] = r[0][0]
    except Exception:
        out["critical_inventory_count"] = 0
    try:
        if is_postgres():
            r = __run(engine, "SELECT COUNT(*) FROM customers WHERE next_upgrade_prediction <= CURRENT_DATE + INTERVAL '60 days' AND next_upgrade_prediction >= CURRENT_DATE")
        else:
            r = __run(engine, "SELECT COUNT(*) FROM customers WHERE next_upgrade_prediction <= date('now','+60 days') AND next_upgrade_prediction >= date('now')")
        out["active_buyers_60d"] = r[0][0]
    except Exception:
        out["active_buyers_60d"] = 0
    try:
        r = __run(engine, "SELECT oil_price_usd_barrel, interest_rate_pct, consumer_confidence_index FROM qatar_economic_indicators ORDER BY date DESC LIMIT 1")
        if r:
            out["oil_price_usd"] = r[0][0]
            out["interest_rate_pct"] = r[0][1]
            out["consumer_confidence_index"] = r[0][2]
    except Exception:
        pass
    return out


def __run(engine, stmt, params=None):
    with engine.connect() as conn:
        return conn.execute(text(stmt), params or {}).fetchall()
