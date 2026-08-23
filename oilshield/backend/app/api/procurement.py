from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.api.deps import get_procurement_recommender
from app.services import ProcurementRecommender

router = APIRouter(prefix="/procurement", tags=["procurement"])


@router.post("/recommend")
def recommend_procurement(
    recommender: ProcurementRecommender = Depends(get_procurement_recommender),
) -> Dict[str, Any]:
    recommendations = recommender.recommend()
    return {
        "recommendations": [
            option.model_dump(mode="json") for option in recommendations
        ],
    }
