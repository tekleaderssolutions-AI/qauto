"""
Model 5 — Market Trend Analyzer.
Combines market volume, Google Trends, social media sentiment, and economics into
per-model demand confidence scores and a short market briefing.
"""
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from db import get_engine  # type: ignore

try:
    # Local LLM client (qwen2.5:7b via Ollama)
    from llm.ollama_client import generate as llm_generate  # type: ignore
except Exception:  # pragma: no cover - fallback if LLM not available
    llm_generate = None  # type: ignore

MODEL_KEY_SEP = "|"


def _safe_read(sql: str) -> pd.DataFrame:
    try:
        engine = get_engine()
        return pd.read_sql(sql, engine)
    except Exception:
        return pd.DataFrame()


def _ensure_model_key(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure a 'model_key' column exists.
    Supports either (make, model) or (brand, model) column pairs.
    """
    if "model_key" in df.columns:
        return df
    df = df.copy()
    if {"make", "model"}.issubset(df.columns):
        df["model_key"] = df["make"].astype(str) + MODEL_KEY_SEP + df["model"].astype(str)
    elif {"brand", "model"}.issubset(df.columns):
        df["model_key"] = df["brand"].astype(str) + MODEL_KEY_SEP + df["model"].astype(str)
    return df


def compute_scores(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Aggregate all trend + social + economic signals into a per-model demand score.
    Returns a list of dicts sorted by demand_confidence_score desc.
    """
    mv = _safe_read("SELECT * FROM qatar_market__market_volume")
    gtr = _safe_read("SELECT * FROM google_trends__model_weekly_pivot")
    sm = _safe_read("SELECT * FROM social_media_trends__model_ranking")

    # --- Reshape Google Trends wide → long ---
    if not gtr.empty and "model_key" not in gtr.columns:
        # Expect columns like [brand, model, 2025-W49, 2025-W50, ...]
        id_cols = [c for c in ["brand", "model", "make"] if c in gtr.columns]
        value_cols = [c for c in gtr.columns if c not in id_cols]
        if {"brand", "model"}.issubset(gtr.columns) and value_cols:
            gtr_long = gtr.melt(
                id_vars=["brand", "model"],
                value_vars=value_cols,
                var_name="week",
                value_name="trend_index",
            )
            # Rename brand → make so _ensure_model_key can build model_key
            gtr_long = gtr_long.rename(columns={"brand": "make"})
            gtr = gtr_long

    gtr = _ensure_model_key(gtr)

    # If we still don't have the expected long-form table, bail out gracefully.
    if gtr.empty or not {"model_key", "week", "trend_index"}.issubset(gtr.columns):
        return []

    # --- Google Trends: last 12 weeks average (primary per-model signal) ---
    gtr = gtr.copy()
    raw_week = gtr["week"].astype(str)
    # Handle formats like "2025-W49" by mapping to the Monday of that ISO week.
    if raw_week.str.contains("W").any():
        gtr["week"] = pd.to_datetime(
            raw_week + "-1", format="%Y-W%W-%w", errors="coerce"
        )
    else:
        gtr["week"] = pd.to_datetime(raw_week, errors="coerce")
    if gtr["week"].dropna().empty:
        # Fallback: if parsing completely failed, treat all as "today"
        gtr["week"] = pd.to_datetime("today")
    cutoff_12w = gtr["week"].max() - pd.DateOffset(weeks=12)
    recent_gtr = gtr[gtr["week"] >= cutoff_12w]
    trend_agg = recent_gtr.groupby("model_key")["trend_index"].mean().rename("trend_12w")

    # --- Market volume: last 3 months (macro; may not be per-model) ---
    if not mv.empty:
        mv = mv.copy()
        if {"year", "month"}.issubset(mv.columns):
            try:
                mv["date"] = pd.to_datetime(mv[["year", "month"]].assign(day=1))
            except Exception:
                mv["date"] = pd.to_datetime("today")
        else:
            mv["date"] = pd.to_datetime("today")
        cutoff_3m = mv["date"].max() - pd.DateOffset(months=3)
        recent_mv = mv[mv["date"] >= cutoff_3m]
        if {"model_key", "transactions"}.issubset(recent_mv.columns):
            vol_agg = recent_mv.groupby("model_key")["transactions"].sum(min_count=1).rename(
                "vol_3m"
            )
        else:
            # Fallback: no per-model volume; treat volume as uniform.
            vol_agg = None
    else:
        vol_agg = None

    if vol_agg is not None:
        df = pd.concat([vol_agg, trend_agg], axis=1).dropna()
    else:
        df = trend_agg.to_frame()

    if df.empty:
        return []

    # Normalize 0–1 and compute trend_score 0–100
    if "vol_3m" not in df.columns:
        df["vol_3m"] = 1.0
    df["vol_norm"] = df["vol_3m"] / (df["vol_3m"].max() or 1)
    df["trend_norm"] = df["trend_12w"] / (df["trend_12w"].max() or 1)
    df["trend_score"] = (df["vol_norm"] * 0.5 + df["trend_norm"] * 0.5) * 100

    # --- Social sentiment: last 4 weeks average ---
    if not sm.empty:
        sm = sm.copy()
        # Map social_media_trends__model_ranking schema → generic columns
        if {"brand", "model"}.issubset(sm.columns):
            sm = sm.rename(columns={"brand": "make"})
        if "avg_sentiment" in sm.columns and "sentiment_score" not in sm.columns:
            sm["sentiment_score"] = sm["avg_sentiment"]
        if "avg_mentions" in sm.columns and "engagement_score" not in sm.columns:
            sm["engagement_score"] = sm["avg_mentions"]

        sm = _ensure_model_key(sm)
        cols = [c for c in ["sentiment_score", "engagement_score"] if c in sm.columns]
        if cols:
            social_agg = sm.groupby("model_key")[cols].mean()
            df = df.join(social_agg, how="left")

    if "sentiment_score" not in df.columns:
        df["sentiment_score"] = 0.5
    else:
        df["sentiment_score"] = df["sentiment_score"].fillna(0.5)

    if "engagement_score" not in df.columns:
        df["engagement_score"] = df["engagement_score"] = 0.0
    else:
        med = float(df["engagement_score"].median()) if not df["engagement_score"].dropna().empty else 0.0
        df["engagement_score"] = df["engagement_score"].fillna(med)

    df["trend_score"] = df["trend_score"].clip(0, 100)
    df["sentiment_scaled"] = df["sentiment_score"].clip(0, 1) * 50.0
    df["demand_confidence_score"] = (
        df["trend_score"] * 0.6 + df["sentiment_scaled"] * 0.4
    ).clip(0, 100)

    # --- Rising 3-week trend flag from Google Trends ---
    rising_flag: Dict[str, bool] = {}
    for key, sub in recent_gtr.groupby("model_key"):
        sub = sub.sort_values("week").tail(3)
        if len(sub) >= 3 and sub["trend_index"].is_monotonic_increasing:
            rising_flag[key] = True
    df["is_rising_3w"] = df.index.map(lambda k: bool(rising_flag.get(k, False)))

    df = df.sort_values("demand_confidence_score", ascending=False).head(limit)
    out: List[Dict[str, Any]] = []
    for model_key, row in df.iterrows():
        if MODEL_KEY_SEP in model_key:
            make, model = model_key.split(MODEL_KEY_SEP, 1)
        else:
            make, model = "", model_key
        out.append(
            {
                "model_key": model_key,
                "make": make,
                "model": model,
                "trend_score": float(row["trend_score"]),
                "social_sentiment": float(row["sentiment_score"]),
                "social_engagement": float(row["engagement_score"]),
                "demand_confidence_score": float(row["demand_confidence_score"]),
                "is_rising_3w": bool(row["is_rising_3w"]),
            }
        )
    return out


def generate_briefing(top_n: int = 5) -> str:
    scores = compute_scores(limit=top_n)
    if not scores:
        return "Insufficient trend and social data to generate a market briefing."

    # Baseline rule-based summary
    lines: List[str] = []
    best = scores[0]
    lines.append(
        f"Hottest model: {best['make']} {best['model']} "
        f"(demand confidence {best['demand_confidence_score']:.0f}/100)."
    )
    rising = [s for s in scores if s["is_rising_3w"]]
    if rising:
        names = ", ".join(f"{s['make']} {s['model']}" for s in rising)
        lines.append(f" Strong 3-week rising trend in: {names}.")
    avg_conf = sum(s["demand_confidence_score"] for s in scores) / len(scores)
    lines.append(f" Overall segment heat: {avg_conf:.0f}/100 across top {len(scores)} models.")
    base_text = " ".join(lines)

    # If local LLM is not available, return the baseline summary.
    if llm_generate is None:
        return base_text

    # Enrich briefing using local LLM (qwen2.5:7b) for more narrative insight.
    try:
        table_lines = []
        for i, s in enumerate(scores[:top_n]):
            table_lines.append(
                f"{i+1}. {s['make']} {s['model']} | "
                f"trend_score={s['trend_score']:.1f}, "
                f"sentiment={s['social_sentiment']:.2f}, "
                f"engagement={s['social_engagement']:.1f}, "
                f"demand_confidence={s['demand_confidence_score']:.1f}, "
                f"is_rising_3w={s['is_rising_3w']}"
            )
        data_block = "\n".join(table_lines)
        prompt = (
            "You are QAUTO-AI, an automotive market analyst for the Qatar used car market.\n\n"
            "Here are per-model demand signals over the last quarter:\n"
            f"{data_block}\n\n"
            "Write a concise (2–4 sentences) briefing for a dealership executive. "
            "Highlight which models are hottest, any rising trends, and how confident the signals are. "
            "Use specific model names and keep it business-focused."
        )
        llm_text: str = llm_generate(  # type: ignore[operator]
            prompt,
            system="You are a senior automotive market analyst for the Qatar used car market.",
            max_tokens=256,
        )
        llm_text = (llm_text or "").strip()
        return llm_text or base_text
    except Exception:
        # If LLM call fails for any reason, fall back to deterministic summary.
        return base_text


CHART_KEYS = ["lc300", "lx600", "prado", "patrol"]


def get_trend_series(top_n: int = 4, weeks: int = 5) -> List[Dict[str, Any]]:
    """
    Return weekly trend index for top N models for charting.
    Keys: lc300, lx600, prado, patrol (or positional fallback).
    """
    gtr = _safe_read("SELECT * FROM google_trends__model_weekly_pivot")
    if gtr.empty:
        return []
    if "model_key" not in gtr.columns and {"brand", "model"}.issubset(gtr.columns):
        gtr = gtr.copy()
        gtr["model_key"] = gtr["brand"].astype(str) + MODEL_KEY_SEP + gtr["model"].astype(str)
    id_cols = [c for c in ["brand", "model", "model_key"] if c in gtr.columns]
    value_cols = [c for c in gtr.columns if c not in id_cols]
    if not value_cols:
        return []
    melted = gtr.melt(id_vars=id_cols, value_vars=value_cols, var_name="week", value_name="trend_index")
    if "model_key" not in melted.columns:
        melted["model_key"] = melted["brand"].astype(str) + MODEL_KEY_SEP + melted["model"].astype(str)
    top = melted.groupby("model_key")["trend_index"].mean().sort_values(ascending=False).head(top_n)
    week_order = sorted(melted["week"].unique(), key=lambda w: (str(w)[:4], str(w)))[-weeks:]
    out = []
    for i, wk in enumerate(week_order):
        row: Dict[str, Any] = {"week": f"W{i+1}"}
        for j, (mk, _) in enumerate(top.items()):
            key = CHART_KEYS[j] if j < len(CHART_KEYS) else f"m{j}"
            val = melted[(melted["week"] == wk) & (melted["model_key"] == mk)]["trend_index"].mean()
            row[key] = round(float(val), 0) if pd.notna(val) else 0
        out.append(row)
    return out


def get_sentiment_by_brand() -> List[Dict[str, Any]]:
    """Return brand-level sentiment for charting."""
    sm = _safe_read("SELECT * FROM social_media_trends__model_ranking")
    if sm.empty:
        return []
    brand_col = "brand" if "brand" in sm.columns else "make"
    if brand_col not in sm.columns:
        return []
    score_col = "avg_sentiment" if "avg_sentiment" in sm.columns else "sentiment_score"
    if score_col not in sm.columns:
        return []
    agg = sm.groupby(brand_col)[score_col].mean().sort_values(ascending=False).head(8)
    return [{"brand": k, "score": round(float(v) * 100 if v <= 1 else float(v), 0)} for k, v in agg.items()]

