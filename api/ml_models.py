"""ML model singleton registry — load once at startup, never per-request."""
import json
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "ml" / "models"


class ModelRegistry:
    _price_model: Any = None
    _price_encoders: dict = {}
    _price_feature_cols: list = []
    _loaded: bool = False

    @classmethod
    def load_all(cls) -> None:
        """Load price predictor model + encoders at startup."""
        if cls._loaded:
            return
        try:
            import xgboost as xgb
            from sklearn.preprocessing import LabelEncoder

            model_path = MODELS_DIR / "price_predictor_v1.json"
            enc_path = MODELS_DIR / "price_encoders.json"
            feat_path = MODELS_DIR / "price_feature_cols.json"
            if model_path.exists():
                m = xgb.XGBRegressor()
                m.load_model(str(model_path))
                cls._price_model = m
            if enc_path.exists():
                with open(enc_path) as f:
                    classes = json.load(f)
                cls._price_encoders = {k: LabelEncoder().fit(c) for k, c in classes.items()}
            if feat_path.exists():
                with open(feat_path) as f:
                    cls._price_feature_cols = json.load(f)
            cls._loaded = True
        except Exception:
            pass

    @classmethod
    def get_price_model(cls) -> Optional[Any]:
        return cls._price_model

    @classmethod
    def get_price_encoders(cls) -> dict:
        return cls._price_encoders

    @classmethod
    def get_price_feature_cols(cls) -> list:
        return cls._price_feature_cols
