"""GET /api/market — Market signals, KPIs, economic snapshot."""
import sys
from datetime import date
from pathlib import Path
from fastapi import APIRouter, Query
from sqlalchemy import text
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from db import get_engine, is_postgres
from ml.market_analyzer import compute_scores, generate_briefing, get_trend_series, get_sentiment_by_brand
from api.cache import cache

router = APIRouter(prefix="/api", tags=["market"])


def _run(engine, stmt, params=None):
    with engine.connect() as conn:
        return conn.execute(text(stmt), params or {}).fetchall()


@router.get("/market/kpis")
@cache(ttl=300, key_prefix="market")
def market_kpis():
    out = {}
    try:
        engine = get_engine()
    except Exception:
        return out
    date_90 = "(CURRENT_DATE - INTERVAL '90 days')" if is_postgres() else "date('now','-90 days')"
    try:
        r = _run(engine, "SELECT overall_market_health_score FROM qatar_economic_indicators ORDER BY date DESC LIMIT 1")
        out["market_health_score"] = r[0][0] if r else 75
    except Exception:
        out["market_health_score"] = 75
    try:
        r = _run(engine, f"SELECT AVG(days_to_sell) FROM historical_sales WHERE body_type LIKE '%%SUV%%' AND date_out >= {date_90}")
        out["avg_days_to_sell_suv"] = round(r[0][0], 0) if r and r[0][0] is not None else 45
    except Exception:
        out["avg_days_to_sell_suv"] = 45
    try:
        r = _run(engine, "SELECT COUNT(*) FROM vehicle_inventory WHERE risk_flag = 'critical'")
        out["critical_inventory_count"] = r[0][0]
    except Exception:
        out["critical_inventory_count"] = 0
    try:
        if is_postgres():
            r = _run(engine, "SELECT COUNT(*) FROM customers WHERE next_upgrade_prediction <= CURRENT_DATE + INTERVAL '60 days' AND next_upgrade_prediction >= CURRENT_DATE")
        else:
            r = _run(engine, "SELECT COUNT(*) FROM customers WHERE next_upgrade_prediction <= date('now','+60 days') AND next_upgrade_prediction >= date('now')")
        out["active_buyers_60d"] = r[0][0]
    except Exception:
        out["active_buyers_60d"] = 0
    try:
        r = _run(engine, 'SELECT "Oil Price USD/bbl", "Interest Rate %", "Consumer Conf Index", "Year", "Month Name" FROM qatar_economic__monthly_data ORDER BY "Year" DESC, "Date" DESC LIMIT 1')
        if r and r[0][0] is not None:
            out["oil_price_usd"] = float(r[0][0])
            out["interest_rate_pct"] = float(r[0][1]) if r[0][1] is not None else None
            out["consumer_confidence_index"] = int(r[0][2]) if r[0][2] is not None else None
    except Exception:
        try:
            df = pd.read_sql("SELECT * FROM qatar_economic__monthly_data ORDER BY 1 DESC LIMIT 1", engine)
            if not df.empty:
                oil_col = next((c for c in df.columns if "oil" in c.lower() and "price" in c.lower()), None)
                if oil_col and pd.notna(df[oil_col].iloc[0]):
                    out["oil_price_usd"] = float(df[oil_col].iloc[0])
                rate_col = next((c for c in df.columns if "interest" in c.lower() and "rate" in c.lower()), None)
                if rate_col and pd.notna(df[rate_col].iloc[0]):
                    out["interest_rate_pct"] = float(df[rate_col].iloc[0])
                conf_col = next((c for c in df.columns if "consumer" in c.lower() and "conf" in c.lower()), None)
                if conf_col and pd.notna(df[conf_col].iloc[0]):
                    out["consumer_confidence_index"] = int(df[conf_col].iloc[0])
        except Exception:
            pass
    return out


@router.get("/market/trends")
@cache(ttl=300, key_prefix="market")
def market_trends():
    """Monthly new car registrations from qatar_economic__monthly_data (column L)."""
    try:
        engine = get_engine()
        df = pd.read_sql("SELECT * FROM qatar_economic__monthly_data ORDER BY 1 ASC", engine)
        if df.empty:
            return {"months": [], "volumes": []}
        date_col = next((c for c in df.columns if "date" in c.lower() and "year" not in c.lower()), df.columns[0])
        reg_col = next((c for c in df.columns if "new" in c.lower() and "reg" in c.lower()), None)
        if reg_col is None and len(df.columns) >= 12:
            reg_col = df.columns[11]
        if reg_col is None:
            return {"months": [], "volumes": []}
        df["_month"] = pd.to_datetime(df[date_col], errors="coerce").dt.strftime("%Y-%m")
        df = df.dropna(subset=["_month"])
        return {
            "months": df["_month"].tolist(),
            "volumes": df[reg_col].fillna(0).astype(int).tolist(),
        }
    except Exception:
        return {"months": [], "volumes": []}


@router.get("/market/events")
@cache(ttl=300, key_prefix="market")
def upcoming_events(limit: int = 10):
    """Upcoming events: project recurring events (same month/day) to next occurrence on or after today."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT event_name, start_date, end_date, demand_multiplier FROM qatar_events_calendar"
            )).fetchall()
        if not rows:
            return []
        today = date.today()
        seen = {}
        for r in rows:
            name, start, end, mult = r[0], r[1], r[2], r[3]
            if start is None:
                continue
            start_ts = pd.Timestamp(start) if hasattr(start, "year") else pd.Timestamp(str(start))
            yr_offset = today.year - start_ts.year
            next_date = start_ts + pd.DateOffset(years=yr_offset)
            if next_date.date() < today:
                next_date = next_date + pd.DateOffset(years=1)
            sd = next_date.strftime("%Y-%m-%d")
            if name not in seen or seen[name]["start_date"] > sd:
                seen[name] = {
                    "event_name": name,
                    "start_date": sd,
                    "end_date": str(end) if end else sd,
                    "demand_multiplier": float(mult) if mult is not None else 0,
                }
        out = sorted(seen.values(), key=lambda x: x["start_date"])
        return out[:limit]
    except Exception:
        return []


@router.get("/market/trend-series")
@cache(ttl=300, key_prefix="market")
def market_trend_series(weeks: int = 5):
    """Weekly trend index for top 4 models (chart data)."""
    try:
        return get_trend_series(top_n=4, weeks=weeks)
    except Exception:
        return []


@router.get("/market/sentiment")
@cache(ttl=300, key_prefix="market")
def market_sentiment():
    """Brand-level sentiment for charting."""
    try:
        return get_sentiment_by_brand()
    except Exception:
        return []


@router.get("/market/analysis")
@cache(ttl=300, key_prefix="market")
def market_analysis(limit: int = Query(20, le=100)):
    """
    Aggregate market, Google Trends, and social data into model-level demand scores.
    Used by dashboards and AI Advisor for high-level signals.
    """
    models = compute_scores(limit=limit)
    briefing = generate_briefing(top_n=min(5, len(models)))
    return {"models": models, "briefing": briefing}
