"""
Qatar AI Platform - ETL: Load Excel/CSV files to PostgreSQL.
Set DATABASE_URL or DB_HOST/DB_USER/DB_PASSWORD/DB_NAME.
"""
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from db import get_engine

DATA_DIR = ROOT / "Data"

# Map: table_name -> (filename_without_ext, optional_sheet for xlsx)
# Core canonical tables used by the backend dashboards
DATASETS = [
    ("vehicle_inventory", "vehicle_inventory", None),
    ("historical_sales", "historical_sales", None),
    ("customers", "customers", None),
    ("purchase_orders", "purchase_orders", None),
    ("competitor_pricing", "competitor_pricing", None),
    ("qatar_events_calendar", "qatar_events_calendar", None),
    # Backwards-compatible aggregate datasets (only loaded if the files exist)
    ("qatar_market_reports", "Qatar_Market_Reports", None),
    ("qatar_economic_indicators", "Qatar_Economic_Indicators", None),
    ("social_media_trends", "social_media_trends", None),
    ("google_trends", "google_trends_analysis", None),
    # New, more granular market datasets (25 total files under Data/)
    ("qatar_market__brand_share", "qatar_market__brand_share", None),
    ("qatar_market__market_volume", "qatar_market__market_volume", None),
    ("qatar_market__ai_signals", "qatar_market__ai_signals", None),
    ("qatar_market__top_models", "qatar_market__top_models", None),
    ("qatar_economic__source_guide", "qatar_economic__source_guide", None),
    ("qatar_economic__ai_economic_signals", "qatar_economic__ai_economic_signals", None),
    ("qatar_economic__annual_summary", "qatar_economic__annual_summary", None),
    ("qatar_economic__monthly_data", "qatar_economic__monthly_data", None),
    ("google_trends__llm_context_latest_qatar", "google_trends__llm_context_latest_qatar", None),
    ("google_trends__qatar_model_ranking", "google_trends__qatar_model_ranking", None),
    ("google_trends__brand_country_summary", "google_trends__brand_country_summary", None),
    ("google_trends__model_weekly_pivot", "google_trends__model_weekly_pivot", None),
    ("google_trends__trends_raw", "google_trends__trends_raw", None),
    ("social_media_trends__llm_context_latest", "social_media_trends__llm_context_latest", None),
    ("social_media_trends__action_alerts", "social_media_trends__action_alerts", None),
    ("social_media_trends__weekly_brand_heatmap", "social_media_trends__weekly_brand_heatmap", None),
    ("social_media_trends__model_ranking", "social_media_trends__model_ranking", None),
    ("social_media_trends__brand_platform_summary", "social_media_trends__brand_platform_summary", None),
    ("social_media_trends__social_raw", "social_media_trends__social_raw", None),
]


def load_file(table_name: str, base_name: str, sheet_name: str | None) -> pd.DataFrame | None:
    """Load a single file (CSV or Excel) into a DataFrame."""
    for ext in [".csv", ".xlsx", ".xls"]:
        path = DATA_DIR / f"{base_name}{ext}"
        if path.exists():
            try:
                if ext == ".csv":
                    return pd.read_csv(path, low_memory=False)
                return pd.read_excel(path, sheet_name=sheet_name or 0)
            except Exception as e:
                print(f"  Error reading {path}: {e}")
                return None
    return None


def run_etl():
    """Load all datasets into PostgreSQL."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    engine = get_engine()
    chunksize = 200
    loaded = 0
    for table_name, base_name, sheet_name in DATASETS:
        df = load_file(table_name, base_name, sheet_name)
        if df is not None and not df.empty:
            df.to_sql(table_name, engine, if_exists="replace", index=False, chunksize=chunksize)
            print(f"  Loaded {table_name}: {len(df)} rows")
            loaded += 1
        else:
            print(f"  Skip {table_name} (file not found or empty)")
    print(f"\nETL complete. Loaded {loaded} tables.")
    return loaded


if __name__ == "__main__":
    print("Qatar AI Platform — ETL")
    run_etl()
