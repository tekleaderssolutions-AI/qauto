"""GET /api/inventory — Risk-scored inventory with filters."""
from fastapi import APIRouter, Query
from typing import Optional
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from ml.risk_scorer import score_inventory, get_risk_summary
from api.cache import cache

router = APIRouter(prefix="/api", tags=["inventory"])


@router.get("/inventory/summary")
@cache(ttl=300, key_prefix="inventory")
def inventory_summary():
    return get_risk_summary()


@router.get("/inventory")
@cache(ttl=300, key_prefix="inventory")
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
    df = score_inventory()
    if df.empty:
        return {"items": [], "total": 0}
    if risk_flag:
        df = df[df["risk_flag"] == risk_flag]
    if body_type:
        df = df[df["body_type"].astype(str).str.contains(body_type, case=False, na=False)]
    if make:
        df = df[df["make"].astype(str).str.contains(make, case=False, na=False)]
    if color:
        df = df[df["color_exterior"].astype(str).str.contains(color, case=False, na=False)]
    if days_min is not None:
        df = df[df["days_in_stock"] >= days_min]
    if days_max is not None:
        df = df[df["days_in_stock"] <= days_max]
    total = len(df)
    df = df.iloc[offset : offset + limit]
    cols = ["vehicle_id", "make", "model", "trim", "year", "color_exterior", "days_in_stock",
            "list_price_qar", "risk_score", "risk_flag", "recommended_action", "body_type"]
    cols = [c for c in cols if c in df.columns]
    items = df[cols].fillna("").to_dict("records")
    for r in items:
        for k, v in r.items():
            if hasattr(v, "item"):
                r[k] = v.item()
    return {"items": items, "total": total}
