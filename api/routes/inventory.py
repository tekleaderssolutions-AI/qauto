"""GET /api/inventory — Risk-scored inventory with filters."""
from fastapi import APIRouter, Query
from typing import Optional
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from ml.risk_scorer import score_inventory_filtered, get_risk_summary
from api.cache import cache
from llm.groq_client import generate

router = APIRouter(prefix="/api", tags=["inventory"])


def _build_action_prompt(row: dict) -> str:
    make = row.get("make") or "Unknown make"
    model = row.get("model") or ""
    trim = row.get("trim") or ""
    year = int(row.get("year") or 0) or None
    color = row.get("color_exterior") or "Unknown color"
    body_type = row.get("body_type") or "SUV"
    days = int(row.get("days_in_stock") or 0)
    price = float(row.get("list_price_qar") or 0)
    risk_score = int(row.get("risk_score") or 0)
    risk_flag = row.get("risk_flag") or "monitor"

    vehicle = f"{year or ''} {make} {model} {trim}".strip()

    return f"""You are QAUTO-AI, a senior used car inventory manager for Qatar.

You are given one vehicle in stock. Based only on the data, write a very short, dealer-facing action plan for this single unit.

Vehicle: {vehicle}
Body type: {body_type}
Exterior color: {color}
Days in stock: {days}
Listed price: QAR {int(price):,}
Risk flag: {risk_flag}

Output exactly TWO sentences in plain text (no bullets, no markdown tags, no labels like ANSWER/REASONING/DATA/ACTION).
- Sentence 1: the pricing / exit strategy with an approximate % and QAR amount if you recommend a change (or say to hold price).
- Sentence 2: 1–2 concrete operational steps (eg, refresh photos, move to homepage tile, bundle with warranty, cross-list on classifieds, follow-up on leads, etc.).
Be simple and readable, avoid jargon, and keep the total under 45 words."""


@router.get("/inventory/summary")
@cache(ttl=300, key_prefix="inventory")
def inventory_summary():
    return get_risk_summary()


@router.get("/inventory")
@cache(ttl=300, key_prefix="inventory_actions_v2")
def get_inventory(
    risk_flag: Optional[str] = None,
    body_type: Optional[str] = None,
    make: Optional[str] = None,
    color: Optional[str] = None,
    days_min: Optional[int] = None,
    days_max: Optional[int] = None,
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
):
    df = score_inventory_filtered(
        risk_flag=risk_flag,
        body_type=body_type,
        make=make,
        color=color,
        days_min=days_min,
        days_max=days_max,
    )
    if df.empty:
        return {"items": [], "total": 0}
    total = len(df)
    df = df.iloc[offset : offset + limit]
    cols = [
        "vehicle_id",
        "make",
        "model",
        "trim",
        "year",
        "color_exterior",
        "days_in_stock",
        "list_price_qar",
        "risk_score",
        "risk_flag",
        "recommended_action",
        "body_type",
    ]
    cols = [c for c in cols if c in df.columns]
    items = df[cols].fillna("").to_dict("records")
    # Enrich recommended_action using LLM for non-healthy units.
    system_path = ROOT / "llm" / "system_prompt.txt"
    system_prompt = (
        system_path.read_text(encoding="utf-8", errors="replace")
        if system_path.exists()
        else None
    )
    for r in items:
        for k, v in r.items():
            if hasattr(v, "item"):
                r[k] = v.item()
        if r.get("risk_flag") != "healthy":
            prompt = _build_action_prompt(r)
            advice = generate(prompt, system=system_prompt, max_tokens=120)
            if advice:
                r["recommended_action"] = advice
    return {"items": items, "total": total}
