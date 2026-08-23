from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from app.api.deps import get_ingestion_service
from app.services import SignalIngestionService

router = APIRouter(prefix="/signals", tags=["signals"])


@router.post("/refresh")
def refresh_signals(
    ingestion: SignalIngestionService = Depends(get_ingestion_service),
) -> Dict[str, Any]:
    result = ingestion.refresh()
    signals: List[Dict[str, Any]] = [
        signal.model_dump(mode="json") for signal in result.signals
    ]
    return {
        "signals": signals,
        "data_source_modes": dict(result.data_source_modes),
    }
