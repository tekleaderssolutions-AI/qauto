"""GET /api/competitors — Competitor price data with gap analysis."""
import sys
from pathlib import Path
from fastapi import APIRouter, Query
from typing import Optional, Any
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from db import get_engine
from api.cache import cache

router = APIRouter(prefix="/api", tags=["competitors"])

def _py(v: Any):
    try:
        import numpy as np  # local import to avoid hard dependency assumptions
        if isinstance(v, np.generic):
            return v.item()
    except Exception:
        pass
    return v


@router.get("/competitors")
@cache(ttl=300, key_prefix="competitors")
def get_competitors(
    model_filter: Optional[str] = Query(None, description="Filter by model name"),
    search: Optional[str] = Query(None, description="Search model or platform"),
    sort: str = Query("gap", description="gap | price | days"),
    limit: int = Query(100, le=500),
):
    try:
        engine = get_engine()
        comp = pd.read_sql(
            "SELECT make, model, trim, year, color, mileage_km, listed_price_qar, platform, location_qatar, days_on_platform FROM competitor_pricing WHERE listed_price_qar IS NOT NULL AND listed_price_qar > 0",
            engine
        )
        comp = comp.rename(columns={"days_on_platform": "days_listed"})
        if comp.empty:
            return {"items": [], "platform_summary": {}}
        inv = pd.read_sql(
            "SELECT make, model, AVG(list_price_qar) as our_avg FROM vehicle_inventory WHERE status = 'available' GROUP BY make, model",
            engine
        )
        comp["our_price"] = comp.apply(
            lambda r: inv[(inv["make"] == r["make"]) & (inv["model"] == r["model"])]["our_avg"].iloc[0]
            if len(inv[(inv["make"] == r["make"]) & (inv["model"] == r["model"])]) else None,
            axis=1
        )
        comp["our_price"] = comp["our_price"].fillna(comp["listed_price_qar"])
        comp["gap"] = comp["our_price"] - comp["listed_price_qar"]
        comp["gap_pct"] = (comp["gap"] / comp["listed_price_qar"] * 100).round(0)
        if model_filter:
            comp = comp[comp["model"].astype(str).str.contains(model_filter, case=False, na=False)]
        if search:
            comp = comp[
                comp["model"].astype(str).str.contains(search, case=False, na=False) |
                comp["platform"].astype(str).str.contains(search, case=False, na=False)
            ]
        if sort == "price":
            comp = comp.sort_values("listed_price_qar")
        elif sort == "days":
            comp = comp.sort_values("days_listed", ascending=False)
        else:
            comp = comp.reindex(comp["gap"].abs().sort_values(ascending=False).index)
        comp = comp.head(limit)
        items = comp.rename(columns={"listed_price_qar": "price", "location_qatar": "location"}).to_dict("records")
        for r in items:
            for k, v in r.items():
                r[k] = _py(v.item() if hasattr(v, "item") else v)
        platform_summary = comp.groupby("platform").agg(count=("listed_price_qar", "count"), avg_price=("listed_price_qar", "mean")).to_dict("index")
        # Ensure JSON-friendly numbers
        for plat, d in list(platform_summary.items()):
            platform_summary[plat] = {k: _py(v.item() if hasattr(v, "item") else v) for k, v in d.items()}
        return {"items": items, "platform_summary": platform_summary}
    except Exception as e:
        return {"items": [], "platform_summary": {}, "error": str(e)}
