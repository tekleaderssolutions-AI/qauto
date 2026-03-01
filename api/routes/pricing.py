"""POST /api/price — Price prediction endpoint."""
from fastapi import APIRouter, HTTPException
from api.schemas import PriceRequest, PriceResponse
from api.ml_models import ModelRegistry
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from ml.price_predictor import predict

router = APIRouter(prefix="/api", tags=["pricing"])


@router.post("/price", response_model=PriceResponse)
def get_price(req: PriceRequest):
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
        model = ModelRegistry.get_price_model()
        encoders = ModelRegistry.get_price_encoders()
        feature_cols = ModelRegistry.get_price_feature_cols()
        price, confidence = predict(
            car,
            model=model if model else None,
            encoders=encoders if encoders else None,
            feature_cols=feature_cols if feature_cols else None,
        )
        spread = price * 0.05
        return PriceResponse(
            recommended_price_qar=price,
            price_range_low=round(price - spread, 0),
            price_range_high=round(price + spread, 0),
            confidence_pct=confidence,
            time_to_sell_days=28,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
