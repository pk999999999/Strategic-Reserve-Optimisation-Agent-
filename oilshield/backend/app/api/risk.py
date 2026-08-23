from __future__ import annotations

from typing import Any, Dict, List, Tuple

from fastapi import APIRouter, Depends

from app.api.deps import get_ingestion_service, get_llm_extractor, get_risk_scoring_engine
from app.models import RiskScore, Signal
from app.services import LLMExtractor, RiskScoringEngine, SignalIngestionService

router = APIRouter(prefix="/risk", tags=["risk"])


def _compute(
    ingestion: SignalIngestionService,
    extractor: LLMExtractor,
    scoring: RiskScoringEngine,
) -> Tuple[List[RiskScore], Dict[str, Signal], Dict[str, str]]:
    result = ingestion.refresh()
    signals_by_id: Dict[str, Signal] = {signal.id: signal for signal in result.signals}
    extracted = extractor.extract_batch(result.signals)
    ranked = scoring.ranked(extracted)
    return ranked, signals_by_id, dict(result.data_source_modes)


@router.get("/scores")
def get_risk_scores(
    ingestion: SignalIngestionService = Depends(get_ingestion_service),
    extractor: LLMExtractor = Depends(get_llm_extractor),
    scoring: RiskScoringEngine = Depends(get_risk_scoring_engine),
) -> Dict[str, Any]:
    ranked, _signals_by_id, modes = _compute(ingestion, extractor, scoring)
    return {
        "risk_scores": [score.model_dump(mode="json") for score in ranked],
        "data_source_modes": modes,
    }


@router.get("/{target}/signals")
def get_target_signals(
    target: str,
    ingestion: SignalIngestionService = Depends(get_ingestion_service),
    extractor: LLMExtractor = Depends(get_llm_extractor),
    scoring: RiskScoringEngine = Depends(get_risk_scoring_engine),
) -> Dict[str, Any]:
    ranked, signals_by_id, modes = _compute(ingestion, extractor, scoring)

    requested = target.strip().lower()
    matched = next(
        (score for score in ranked if score.target.strip().lower() == requested),
        None,
    )

    resolved_name = matched.target if matched is not None else target
    contributing: List[Signal] = []
    if matched is not None:
        contributing = [
            signals_by_id[signal_id]
            for signal_id in matched.contributing_signal_ids
            if signal_id in signals_by_id
        ]

    return {
        "target": resolved_name,
        "signals": [signal.model_dump(mode="json") for signal in contributing],
        "data_source_modes": modes,
    }
