"""
Model 4 — Buyer-Listing Matcher.
Matches customers (next_upgrade_prediction, budget, preferred model/color) with vehicle_inventory.
Score: model_match + budget_fit + color_preference + feature_match + upgrade_timing.
"""
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import datetime as dt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from db import get_engine

def _jsonify_value(v):
    # pandas timestamp / datetime-like → ISO string
    try:
        if isinstance(v, pd.Timestamp):
            if pd.isna(v):
                return None
            return v.isoformat()
    except Exception:
        pass
    if isinstance(v, (datetime, )):
        return v.isoformat()
    # numpy scalar → python scalar
    try:
        if isinstance(v, np.generic):
            return v.item()
    except Exception:
        pass
    # NaN / NaT → None
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass
    return v


def _jsonify_dict(d: dict) -> dict:
    return {k: _jsonify_value(v) for k, v in (d or {}).items()}


def load_customers(upgrade_within_days: int = 90):
    try:
        engine = get_engine()
        cust = pd.read_sql("SELECT * FROM customers", engine)
        inv = pd.read_sql("SELECT * FROM vehicle_inventory WHERE status = 'available'", engine)
    except Exception:
        return pd.DataFrame(), pd.DataFrame()
    cust["next_upgrade_prediction"] = pd.to_datetime(cust["next_upgrade_prediction"], errors="coerce")
    cutoff = pd.Timestamp.now() + pd.Timedelta(days=upgrade_within_days)
    cust = cust[cust["next_upgrade_prediction"].notna() & (cust["next_upgrade_prediction"] <= cutoff)]
    return cust, inv


def budget_fit(listed_price: float, budget: float) -> float:
    if not budget or budget <= 0:
        return 60
    if listed_price <= budget * 1.1:
        return 100
    if listed_price <= budget * 1.2:
        return 60
    return 0


def color_match(preferred: str, actual: str) -> float:
    if pd.isna(preferred) or pd.isna(actual):
        return 50
    p = str(preferred).strip().lower()
    a = str(actual).strip().lower()
    if p in a or a in p:
        return 100
    neutrals = ["white", "silver", "black", "grey", "graphite"]
    if a in neutrals:
        return 70
    return 30


def upgrade_timing_score(next_upgrade: pd.Timestamp) -> float:
    if pd.isna(next_upgrade):
        return 20
    delta = (next_upgrade - pd.Timestamp.now()).days
    if delta <= 30: return 100
    if delta <= 60: return 75
    if delta <= 90: return 50
    return 20


def match_score(customer: dict, vehicle: dict) -> float:
    model_match = 100 if (str(customer.get("preferred_body_type") or "") in str(vehicle.get("body_type") or "")) else 50
    budget = float(customer.get("lifetime_value_qar") or customer.get("avg_purchase_value_qar") or 0)
    if budget <= 0:
        budget = 150000
    listed = float(vehicle.get("list_price_qar") or 0)
    b_fit = budget_fit(listed, budget)
    c_match = color_match(customer.get("preferred_color"), vehicle.get("color_exterior"))
    upg = customer.get("next_upgrade_prediction")
    if hasattr(upg, "days"):
        upg_ts = upg
    else:
        upg_ts = pd.to_datetime(upg, errors="coerce")
    u_score = upgrade_timing_score(upg_ts)
    base = model_match * 0.30 + b_fit * 0.25 + c_match * 0.20 + 50 * 0.15 + u_score * 0.10
    price_prox = 0
    if budget > 0 and listed > 0:
        ratio = listed / budget
        if ratio <= 0.95:
            price_prox = 5
        elif ratio <= 1.0:
            price_prox = 3
        elif ratio <= 1.05:
            price_prox = 0
        else:
            price_prox = -2
    year_bonus = 0
    v_year = vehicle.get("year")
    if v_year and isinstance(v_year, (int, float)):
        curr = dt.datetime.now().year
        if v_year >= curr - 2:
            year_bonus = 2
        elif v_year >= curr - 4:
            year_bonus = 0
        else:
            year_bonus = -1
    score = base + price_prox + year_bonus
    return min(100, max(0, round(score, 1)))


def get_matches_for_buyer(customer_id: int, top_n: int = 5):
    cust_df, inv_df = load_customers(upgrade_within_days=365)
    cust = cust_df[cust_df["customer_id"] == customer_id]
    if cust.empty:
        return []
    cust = cust.iloc[0].to_dict()
    scores = []
    for _, row in inv_df.iterrows():
        v = row.to_dict()
        sc = match_score(cust, v)
        scores.append(_jsonify_dict({
            "vehicle_id": v.get("vehicle_id"),
            "make": v.get("make"), "model": v.get("model"), "trim": v.get("trim"), "year": v.get("year"),
            "color_exterior": v.get("color_exterior"), "list_price_qar": v.get("list_price_qar"),
            "match_score": sc,
        }))
    scores.sort(key=lambda x: -x["match_score"])
    return scores[:top_n]


def get_ready_buyers(limit: int = 20):
    """Customers with next_upgrade within 90 days."""
    cust_df, _ = load_customers(upgrade_within_days=90)
    return [_jsonify_dict(r) for r in cust_df.head(limit).to_dict("records")]


def get_matches_for_all_ready_buyers(top_per_buyer: int = 3):
    """For dashboard: each ready buyer with top N inventory matches."""
    cust_df, inv_df = load_customers(upgrade_within_days=90)
    out = []
    for _, c in cust_df.head(50).iterrows():
        matches = []
        for _, v in inv_df.iterrows():
            sc = match_score(c.to_dict(), v.to_dict())
            matches.append(_jsonify_dict({"vehicle_id": v["vehicle_id"], "make": v["make"], "model": v["model"], "list_price_qar": v["list_price_qar"], "match_score": sc}))
        matches.sort(key=lambda x: -x["match_score"])
        out.append({"customer": _jsonify_dict(c.to_dict()), "top_matches": matches[:top_per_buyer]})
    return out


if __name__ == "__main__":
    print(get_ready_buyers(5))
    print(get_matches_for_buyer(1001, 3))
