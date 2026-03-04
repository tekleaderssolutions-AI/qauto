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
@cache(ttl=3600, key_prefix="competitors:v6")
def get_competitors(
    make_filter: Optional[str] = Query(None, description="Filter by make/brand name"),
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
            return {"items": [], "platform_summary": {}, "error": "No competitor listings found in competitor_pricing."}
        inv = pd.read_sql(
            "SELECT make, model, year, trim, list_price_qar FROM vehicle_inventory WHERE status = 'available' AND list_price_qar IS NOT NULL AND list_price_qar > 0",
            engine
        )
        # Normalize strings/types so matching is reliable across sources.
        comp["make"] = comp["make"].astype(str).str.strip()
        comp["model"] = comp["model"].astype(str).str.strip()
        comp["trim"] = comp.get("trim", "").astype(str).str.strip()
        comp["year"] = pd.to_numeric(comp.get("year"), errors="coerce").fillna(0).astype(int)
        comp["listed_price_qar"] = pd.to_numeric(comp["listed_price_qar"], errors="coerce")
        comp = comp[comp["listed_price_qar"].notna() & (comp["listed_price_qar"] > 0)]
        
        # --- Filter: 2022-2025 only as requested ---
        comp = comp[(comp["year"] >= 2022) & (comp["year"] <= 2025)]
        
        if comp.empty:
            return {"items": [], "platform_summary": {}, "error": "No competitor listings found for the 2022-2025 year range."}

        if inv is None or inv.empty:
            comp["our_price"] = comp["listed_price_qar"]
        else:
            inv["make"] = inv["make"].astype(str).str.strip()
            inv["model"] = inv["model"].astype(str).str.strip()
            inv["trim"] = inv.get("trim", "").astype(str).str.strip()
            inv["year"] = pd.to_numeric(inv.get("year"), errors="coerce").fillna(0).astype(int)
            inv["list_price_qar"] = pd.to_numeric(inv["list_price_qar"], errors="coerce")
            inv = inv[inv["list_price_qar"].notna() & (inv["list_price_qar"] > 0)]
            
            # --- Filter: 2022-2025 only as requested ---
            inv = inv[(inv["year"] >= 2022) & (inv["year"] <= 2025)]

            # Use medians (more robust than averages) for "our price" reference.
            inv["trim_norm"] = inv["trim"].str.lower()
            comp["trim_norm"] = comp["trim"].str.lower()

            inv_m1 = (
                inv.groupby(["make", "model", "year", "trim_norm"], as_index=False)["list_price_qar"]
                .median()
                .rename(columns={"list_price_qar": "our_med"})
            )
            inv_m2 = (
                inv.groupby(["make", "model", "year"], as_index=False)["list_price_qar"]
                .median()
                .rename(columns={"list_price_qar": "our_med"})
            )
            inv_m3 = (
                inv.groupby(["make", "model"], as_index=False)["list_price_qar"]
                .median()
                .rename(columns={"list_price_qar": "our_med"})
            )

            # 1) make+model+year+trim
            comp = comp.merge(inv_m1, how="left", on=["make", "model", "year", "trim_norm"])
            # 2) make+model+year
            missing = comp["our_med"].isna()
            if missing.any():
                comp.loc[missing, "our_med"] = (
                    comp.loc[missing, ["make", "model", "year"]]
                    .merge(inv_m2, how="left", on=["make", "model", "year"])["our_med"]
                    .to_numpy()
                )
            # --- Max year gap: don't compare a 2016 car to 2024 inventory ---
            MAX_YEAR_GAP = 3

            # 3) make+model with nearest year (if inventory has other years)
            missing = comp["our_med"].isna()
            if missing.any():
                inv_year = (
                    inv.groupby(["make", "model", "year"], as_index=False)["list_price_qar"]
                    .median()
                )
                # Use a cross-merge + nearest-year filter instead of merge_asof
                # to avoid "left keys must be sorted" errors with messy data.
                comp_miss = comp.loc[missing, ["make", "model", "year"]].copy()
                comp_miss["_idx"] = comp_miss.index  # remember original index
                merged = comp_miss.merge(inv_year, on=["make", "model"], suffixes=("", "_inv"))
                if not merged.empty:
                    merged["_ydist"] = (merged["year"] - merged["year_inv"]).abs()
                    # Only keep matches within the max year gap
                    merged = merged[merged["_ydist"] <= MAX_YEAR_GAP]
                if not merged.empty:
                    best = merged.loc[merged.groupby("_idx")["_ydist"].idxmin()]
                    best = best.set_index("_idx")
                    comp.loc[best.index, "our_med"] = best["list_price_qar"].values

            # 4) final fallback: make+model (any year) median — only if years overlap
            missing = comp["our_med"].isna()
            if missing.any():
                # Build make+model median but only from inventory years close to competitor years
                for idx in comp.loc[missing].index:
                    c_make = comp.at[idx, "make"]
                    c_model = comp.at[idx, "model"]
                    c_year = comp.at[idx, "year"]
                    nearby = inv[
                        (inv["make"] == c_make) &
                        (inv["model"] == c_model) &
                        ((inv["year"] - c_year).abs() <= MAX_YEAR_GAP)
                    ]
                    if not nearby.empty:
                        comp.at[idx, "our_med"] = nearby["list_price_qar"].median()

            comp["our_price"] = comp["our_med"].fillna(comp["listed_price_qar"])
            comp = comp.drop(columns=[c for c in ["our_med", "trim_norm"] if c in comp.columns])
        comp["gap"] = comp["our_price"] - comp["listed_price_qar"]
        comp["gap_pct"] = (comp["gap"] / comp["listed_price_qar"] * 100).round(1)
        def _ai_advice(gap_pct: float) -> str:
            if gap_pct > 25:
                return f"AI: We are {gap_pct:.0f}% above market — consider repricing"
            elif gap_pct > 10:
                return f"AI: Drop {gap_pct/2:.0f}–{gap_pct:.0f}% to match competitors"
            elif gap_pct > 0:
                return "AI: Hold price or offer small discount"
            elif gap_pct > -10:
                return "AI: We are competitive — maintain pricing"
            else:
                return f"AI: We are {abs(gap_pct):.0f}% below market — opportunity to raise price"
        comp["ai_advice"] = comp["gap_pct"].apply(_ai_advice)
        if make_filter:
            comp = comp[comp["make"].astype(str).str.contains(make_filter, case=False, na=False)]
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

        # In the unfiltered "All" view, don't let a single model dominate the first page.
        if not make_filter and not model_filter and not search:
            comp = comp.groupby(["make", "model"], sort=False).head(3)

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
