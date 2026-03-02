"""POST /api/price — Price prediction endpoint with LLM-generated AI advice."""
from __future__ import annotations
from typing import List, Optional, Tuple
from fastapi import APIRouter, HTTPException, Request
from api.schemas import PriceRequest, PriceResponse
from api.ml_models import ModelRegistry
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from ml.price_predictor import predict
from llm.groq_client import generate
from db import get_engine, is_postgres
from sqlalchemy import text
from api.limiter import limiter

router = APIRouter(prefix="/api", tags=["pricing"])


def _run(engine, stmt, params=None):
    with engine.connect() as conn:
        return conn.execute(text(stmt), params or {}).fetchall()


def _fetch_market_context(make: str, model: str, color: str, body_type: str) -> Tuple[dict, List[str], int]:
    """Fetch market KPIs, competitor info, similar transaction count. Returns (kpis, market_context_lines, similar_count)."""
    kpis = {}
    market_context = []
    similar_count = 0

    try:
        engine = get_engine()
    except Exception:
        return kpis, market_context, similar_count

    # Market KPIs
    try:
        r = _run(engine, "SELECT overall_market_health_score FROM qatar_economic_indicators ORDER BY date DESC LIMIT 1")
        kpis["market_health"] = r[0][0] if r else 75
    except Exception:
        kpis["market_health"] = 75

    try:
        r = _run(engine, 'SELECT "Oil Price USD/bbl", "Interest Rate %", "Consumer Conf Index" FROM qatar_economic__monthly_data ORDER BY "Year" DESC, "Date" DESC LIMIT 1')
        if r and r[0][0] is not None:
            kpis["oil_usd"] = float(r[0][0])
            kpis["interest_rate"] = float(r[0][1]) if r[0][1] is not None else None
            kpis["consumer_confidence"] = int(r[0][2]) if r[0][2] is not None else None
    except Exception:
        try:
            import pandas as pd
            df = pd.read_sql("SELECT * FROM qatar_economic__monthly_data ORDER BY 1 DESC LIMIT 1", engine)
            if not df.empty:
                oil_col = next((c for c in df.columns if "oil" in c.lower() and "price" in c.lower()), None)
                if oil_col and pd.notna(df[oil_col].iloc[0]):
                    kpis["oil_usd"] = float(df[oil_col].iloc[0])
                conf_col = next((c for c in df.columns if "consumer" in c.lower() and "conf" in c.lower()), None)
                if conf_col and pd.notna(df[conf_col].iloc[0]):
                    kpis["consumer_confidence"] = int(df[conf_col].iloc[0])
        except Exception:
            pass

    # Avg days to sell for body type
    date_90 = "(CURRENT_DATE - INTERVAL '90 days')" if is_postgres() else "date('now','-90 days')"
    try:
        bt = "".join(c for c in (body_type or "SUV") if c.isalnum() or c.isspace())[:20] or "SUV"
        r = _run(engine, f"SELECT AVG(days_to_sell) FROM historical_sales WHERE body_type LIKE '%{bt}%' AND date_out >= {date_90}")
        kpis["avg_days_to_sell"] = round(r[0][0], 0) if r and r[0][0] is not None else 45
    except Exception:
        kpis["avg_days_to_sell"] = 45

    # Similar transactions (make+model in historical_sales)
    try:
        r = _run(engine, "SELECT COUNT(*) FROM historical_sales WHERE make = :m AND model = :md", {"m": make, "md": model})
        similar_count = r[0][0] if r else 0
    except Exception:
        pass

    # Build market_context bullet points
    month = __import__("datetime").datetime.now().month
    if 11 <= month or month <= 2:
        market_context.append("Winter peak season – buyers active, prices firm")
    elif 6 <= month <= 8:
        market_context.append("Summer slowdown – consider flexible pricing")
    else:
        market_context.append("Moderate season – steady buyer activity")

    if kpis.get("oil_usd") is not None:
        conf = kpis.get("consumer_confidence", 70)
        market_context.append(f"Oil ${int(kpis['oil_usd'])} – consumer confidence {conf}/100")
    elif kpis.get("consumer_confidence") is not None:
        market_context.append(f"Consumer confidence {kpis['consumer_confidence']}/100")

    color_lower = (color or "").lower()
    if color_lower in ("white", "pearl white", "silver", "silver metallic"):
        market_context.append("White/silver color premium: +4–5% above market average")
    elif color_lower in ("black", "grey", "gray"):
        market_context.append("Neutral colors – strong resale appeal")
    elif color_lower in ("red", "blue", "green"):
        market_context.append("Colored unit – may take longer to sell")

    # Competitor listings for same make/model
    try:
        r = _run(engine, """
            SELECT COUNT(*), MIN(listed_price_qar), MAX(listed_price_qar)
            FROM competitor_pricing
            WHERE make = :m AND model = :md AND listed_price_qar > 0
        """, {"m": make, "md": model})
        if r and r[0][0] and r[0][0] > 0:
            cnt, lo, hi = r[0][0], r[0][1], r[0][2]
            lo_str = f"QAR {int(lo / 1000)}K" if lo else "N/A"
            hi_str = f"QAR {int(hi / 1000)}K" if hi else "N/A"
            market_context.append(f"{cnt} similar {model}s listed at {lo_str}-{hi_str}")
    except Exception:
        pass

    return kpis, market_context, similar_count


def _generate_ai_advice(
    make: str,
    model: str,
    year: int,
    mileage_km: Optional[int],
    color: str,
    body_type: str,
    recommended_price: float,
    price_low: float,
    price_high: float,
    confidence: float,
    market_context: list[str],
    similar_count: int,
    time_rec: int,
    time_fast: int,
    time_max: int,
) -> str:
    """Call Groq to generate detailed AI pricing advice."""
    ctx_str = "\n".join(f"  • {c}" for c in market_context) if market_context else "  • General market conditions"
    mileage_str = f"{mileage_km:,} km" if mileage_km is not None else "unknown mileage"
    body_type_str = body_type or "SUV"

    prompt = f"""You are a Qatar used car pricing expert. Give a SHORT, actionable recommendation (2–4 sentences max) for listing this car.

Car: {year} {make} {model}, {color}, {body_type_str}, {mileage_str}
Recommended price: QAR {int(recommended_price):,}
Range: QAR {int(price_low):,} – QAR {int(price_high):,}
Confidence: {confidence:.0f}% based on {similar_count} similar transactions

Market context:
{ctx_str}

Time to sell estimates:
- At recommended: ~{time_rec} days
- At -6% (fast sale): ~{time_fast} days
- At +6% (max price): ~{time_max} days

Provide a concise recommendation: when to list, suggested price point, and what to expect (e.g. offer timing). Be specific. No preamble."""

    return generate(prompt, max_tokens=256)


@router.post("/price", response_model=PriceResponse)
@limiter.limit("30/minute")
def get_price(req: PriceRequest, request: Request):
    try:
        car = {
            "make": req.make,
            "model": req.model,
            "trim": req.trim or "",
            "year": req.year,
            "color_exterior": req.color_exterior or "Silver",
            "body_type": req.body_type or "SUV",
            "sunroof_flag": req.sunroof_flag,
            "ventilated_seats_flag": req.ventilated_seats_flag,
            "displacement_cc": req.displacement_cc or 2500,
            "color_demand_score": req.color_demand_score or 70,
            "feature_demand_score": req.feature_demand_score or 80,
        }
        model_obj = ModelRegistry.get_price_model()
        encoders = ModelRegistry.get_price_encoders()
        feature_cols = ModelRegistry.get_price_feature_cols()
        price, confidence = predict(
            car,
            model=model_obj if model_obj else None,
            encoders=encoders if encoders else None,
            feature_cols=feature_cols if feature_cols else None,
        )
        spread = price * 0.06  # ±6%
        price_low = round(price - spread, 0)
        price_high = round(price + spread, 0)

        # Fetch market context and build LLM prompt
        kpis, market_context, similar_count = _fetch_market_context(
            req.make, req.model, req.color_exterior or "Silver", req.body_type or "SUV"
        )
        avg_days = int(kpis.get("avg_days_to_sell", 45))
        time_rec = max(14, min(60, int(avg_days * 0.6)))   # ~24–28 typical
        time_fast = max(7, int(avg_days * 0.3))            # at -6%: faster
        time_max = min(90, int(avg_days * 1.2))           # at +6%: slower

        ai_advice = _generate_ai_advice(
            make=req.make,
            model=req.model,
            year=req.year,
            mileage_km=req.mileage_km,
            color=req.color_exterior or "Silver",
            body_type=req.body_type or "SUV",
            recommended_price=price,
            price_low=price_low,
            price_high=price_high,
            confidence=confidence,
            market_context=market_context,
            similar_count=similar_count or 0,
            time_rec=time_rec,
            time_fast=time_fast,
            time_max=time_max,
        )

        return PriceResponse(
            recommended_price_qar=price,
            price_range_low=price_low,
            price_range_high=price_high,
            confidence_pct=confidence,
            time_to_sell_days=time_rec,
            time_to_sell_fast_days=time_fast,
            time_to_sell_max_days=time_max,
            similar_transactions_count=similar_count,
            market_context=market_context,
            ai_advice=ai_advice.strip() if ai_advice else None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
