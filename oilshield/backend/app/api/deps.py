from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

from app.core.config import get_settings
from app.providers import LiveDataSource, build_llm_provider
from app.services import (
    KnownTarget,
    LLMExtractor,
    PipelineOrchestrator,
    ProcurementRecommender,
    RiskScoringEngine,
    ScenarioSimulator,
    SignalIngestionService,
)

__all__ = [
    "load_known_targets",
    "known_target_names",
    "get_ingestion_service",
    "get_llm_extractor",
    "get_risk_scoring_engine",
    "get_scenario_simulator",
    "get_procurement_recommender",
    "get_pipeline_orchestrator",
]

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_CORRIDORS_PATH = _DATA_DIR / "corridors.json"
_ROUTES_PATH = _DATA_DIR / "routes.json"
_PROCUREMENT_PATH = _DATA_DIR / "procurement_options.json"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_known_targets() -> tuple[KnownTarget, ...]:
    targets: List[KnownTarget] = []
    seen: set[str] = set()

    def add(name: str, target_type: str) -> None:
        cleaned = (name or "").strip()
        key = cleaned.lower()
        if not cleaned or key in seen:
            return
        seen.add(key)
        targets.append(KnownTarget(name=cleaned, target_type=target_type))  # type: ignore[arg-type]

    corridors = _read_json(_CORRIDORS_PATH).get("corridors", [])
    for corridor in corridors:
        add(corridor.get("name", ""), "corridor")

    routes = _read_json(_ROUTES_PATH).get("routes", [])
    for route in routes:
        add(route.get("supplier_country", ""), "country")

    options = _read_json(_PROCUREMENT_PATH).get("procurement_options", [])
    for option in options:
        add(option.get("supplier_country", ""), "country")

    return tuple(targets)


@lru_cache(maxsize=1)
def known_target_names() -> tuple[str, ...]:
    return tuple(target.name for target in load_known_targets())


@lru_cache(maxsize=1)
def get_ingestion_service() -> SignalIngestionService:
    settings = get_settings()
    if settings.data_source_mode == "live":
        primary = LiveDataSource(known_targets=list(known_target_names()))
        return SignalIngestionService(primary=primary, settings=settings)
    return SignalIngestionService()


@lru_cache(maxsize=1)
def get_llm_extractor() -> LLMExtractor:
    return LLMExtractor(
        provider=build_llm_provider(get_settings()),
        known_targets=list(known_target_names()),
    )


@lru_cache(maxsize=1)
def get_risk_scoring_engine() -> RiskScoringEngine:
    return RiskScoringEngine(load_known_targets())


@lru_cache(maxsize=1)
def get_scenario_simulator() -> ScenarioSimulator:
    return ScenarioSimulator()


@lru_cache(maxsize=1)
def get_procurement_recommender() -> ProcurementRecommender:
    return ProcurementRecommender()


@lru_cache(maxsize=1)
def get_pipeline_orchestrator() -> PipelineOrchestrator:
    return PipelineOrchestrator(
        ingestion=get_ingestion_service(),
        extractor=get_llm_extractor(),
        scoring=get_risk_scoring_engine(),
        simulator=get_scenario_simulator(),
        recommender=get_procurement_recommender(),
    )
