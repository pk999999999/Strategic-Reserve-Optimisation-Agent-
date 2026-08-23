from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends

from app.api.deps import get_pipeline_orchestrator
from app.services import PipelineOrchestrator

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/run")
def run_pipeline(
    body: Optional[Dict[str, Any]] = Body(default=None),
    orchestrator: PipelineOrchestrator = Depends(get_pipeline_orchestrator),
) -> Dict[str, Any]:
    scenario_id: Optional[str] = None
    if body is not None:
        scenario_id = body.get("scenario_id")

    result = orchestrator.run(scenario_id)
    return result.model_dump(mode="json")
