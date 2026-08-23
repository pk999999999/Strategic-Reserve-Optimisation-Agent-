from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional

from app.models import (
    ExtractedSignal,
    ImpactResult,
    PipelineResult,
    ProcurementOption,
    RiskScore,
    Signal,
)
from app.services.extractor import LLMExtractor
from app.services.ingestion import SignalIngestionService
from app.services.recommender import ProcurementRecommender
from app.services.scoring import RiskScoringEngine
from app.services.simulator import ScenarioSimulator

__all__ = ["PipelineOrchestrator"]

logger = logging.getLogger(__name__)

_DEFAULT_SCENARIO_ID = "hormuz_partial_closure"

_CORRIDOR_SCENARIO: Dict[str, str] = {
    "strait of hormuz": "hormuz_partial_closure",
    "red sea": "red_sea_shutdown",
}


class PipelineOrchestrator:
    def __init__(
        self,
        ingestion: SignalIngestionService,
        extractor: LLMExtractor,
        scoring: RiskScoringEngine,
        simulator: ScenarioSimulator,
        recommender: ProcurementRecommender,
    ) -> None:
        self._ingestion = ingestion
        self._extractor = extractor
        self._scoring = scoring
        self._simulator = simulator
        self._recommender = recommender

    def run(self, scenario_id: Optional[str] = None) -> PipelineResult:
        start = time.monotonic()

        signals: List[Signal] = []
        extracted: List[ExtractedSignal] = []
        risk_scores: List[RiskScore] = []
        impact: Optional[ImpactResult] = None
        recommendations: List[ProcurementOption] = []
        data_source_modes: Dict[str, str] = {}
        stage_status: Dict[str, str] = {}

        try:
            ingestion_result = self._ingestion.refresh()
            signals = list(ingestion_result.signals)
            data_source_modes = {
                source_id: str(mode)
                for source_id, mode in ingestion_result.data_source_modes.items()
            }
            stage_status["ingestion"] = "ok"
        except Exception as exc:  # noqa: BLE001
            stage_status["ingestion"] = f"error: {exc}"
            logger.exception("Pipeline ingestion stage failed")

        try:
            extracted = self._extractor.extract_batch(signals)
            stage_status["extraction"] = "ok"
        except Exception as exc:  # noqa: BLE001
            stage_status["extraction"] = f"error: {exc}"
            logger.exception("Pipeline extraction stage failed")

        try:
            risk_scores = self._scoring.ranked(extracted)
            stage_status["scoring"] = "ok"
        except Exception as exc:  # noqa: BLE001
            stage_status["scoring"] = f"error: {exc}"
            logger.exception("Pipeline scoring stage failed")

        try:
            selected_id = scenario_id or self._auto_select_scenario(risk_scores)
            scenario = self._simulator.get_scenario(selected_id)
            impact = self._simulator.run(scenario)
            stage_status["scenario"] = "ok"
        except Exception as exc:  # noqa: BLE001
            stage_status["scenario"] = f"error: {exc}"
            logger.exception("Pipeline scenario stage failed")

        try:
            recommendations = self._recommender.recommend()
            stage_status["procurement"] = "ok"
        except Exception as exc:  # noqa: BLE001
            stage_status["procurement"] = f"error: {exc}"
            logger.exception("Pipeline procurement stage failed")

        linked_actions = self._build_linked_actions(risk_scores, recommendations)
        latency_ms = max(0, int((time.monotonic() - start) * 1000))

        return PipelineResult(
            signals=signals,
            risk_scores=risk_scores,
            impact=impact,
            recommendations=recommendations,
            linked_actions=linked_actions,
            latency_ms=latency_ms,
            data_source_modes=data_source_modes,
        )

    @staticmethod
    def _scenario_for_corridor(corridor_name: str) -> str:
        return _CORRIDOR_SCENARIO.get(
            corridor_name.strip().lower(), _DEFAULT_SCENARIO_ID
        )

    def _auto_select_scenario(self, risk_scores: List[RiskScore]) -> str:
        for score in risk_scores:
            if score.target_type == "corridor" and score.band == "high":
                return self._scenario_for_corridor(score.target)
        return _DEFAULT_SCENARIO_ID

    def _build_linked_actions(
        self,
        risk_scores: List[RiskScore],
        recommendations: List[ProcurementOption],
    ) -> List[dict]:
        top_option_id = recommendations[0].id if recommendations else None

        actions: List[dict] = []
        for score in risk_scores:
            if score.target_type != "corridor" or score.band != "high":
                continue
            actions.append(
                {
                    "corridor": score.target,
                    "risk_score": score.score,
                    "recommended_scenario_id": self._scenario_for_corridor(
                        score.target
                    ),
                    "recommended_option_id": top_option_id,
                }
            )
        return actions
