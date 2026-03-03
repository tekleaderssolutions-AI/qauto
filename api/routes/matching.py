"""POST /api/match — Buyer-listing matching."""
from fastapi import APIRouter, Query
from api.schemas import MatchRequest
from api.cache import cache
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from ml.buyer_matcher import get_matches_for_buyer, get_ready_buyers, get_matches_for_all_ready_buyers

router = APIRouter(prefix="/api", tags=["matching"])


@router.get("/match/ready-buyers")
@cache(ttl=3600, key_prefix="match")
def ready_buyers(limit: int = Query(20, le=100)):
    return get_ready_buyers(limit)


@router.post("/match")
@cache(ttl=3600, key_prefix="match_buyer")
def match_buyer(req: MatchRequest):
    if req.customer_id:
        matches = get_matches_for_buyer(req.customer_id, top_n=req.top_n)
        return {"customer_id": req.customer_id, "matches": matches}
    return {"matches": [], "message": "Provide customer_id"}


@router.get("/match/dashboard")
@cache(ttl=3600, key_prefix="match")
def match_dashboard(top_per_buyer: int = Query(3, le=10)):
    return get_matches_for_all_ready_buyers(top_per_buyer)
