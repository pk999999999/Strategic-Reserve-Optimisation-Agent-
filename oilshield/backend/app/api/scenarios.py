from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends

from app.api.deps import get_scenario_simulator
from app.models import Scenario
from app.services import ScenarioSimulator

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


def _apply_overrides(
    simulator: ScenarioSimulator,
    scenario: Scenario,
    overrides: Optional[Dict[str, Any]],
) -> Scenario:
    configured = scenario
    if overrides:
        for key, value in overrides.items():
            configured = simulator.apply_assumption(configured, key, value)
    return configured


def _extract_overrides(body: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not body:
        return None
    if "assumptions" in body and isinstance(body["assumptions"], dict):
        return body["assumptions"]
    return {k: v for k, v in body.items() if k not in {"id", "scenario_id"}}


@router.get("")
def list_scenarios(
    simulator: ScenarioSimulator = Depends(get_scenario_simulator),
) -> Dict[str, Any]:
    scenarios = simulator.list_scenarios()
    return {
        "scenarios": [scenario.model_dump(mode="json") for scenario in scenarios],
    }


@router.post("/{scenario_id}/run")
def run_scenario(
    scenario_id: str,
    body: Optional[Dict[str, Any]] = Body(default=None),
    simulator: ScenarioSimulator = Depends(get_scenario_simulator),
) -> Dict[str, Any]:
    scenario = simulator.get_scenario(scenario_id)
    overrides = _extract_overrides(body)
    configured = _apply_overrides(simulator, scenario, overrides)

    impact = simulator.run(configured)
    return {
        "impact": impact.model_dump(mode="json"),
        "assumptions_used": [
            assumption.model_dump(mode="json")
            for assumption in impact.assumptions_used
        ],
    }


@router.post("/save")
def save_scenario(
    body: Dict[str, Any] = Body(...),
    simulator: ScenarioSimulator = Depends(get_scenario_simulator),
) -> Dict[str, str]:
    scenario_id = body.get("id") or body.get("scenario_id")
    scenario = simulator.get_scenario(scenario_id)
    overrides = _extract_overrides(body)
    configured = _apply_overrides(simulator, scenario, overrides)

    saved_id = simulator.save(configured)
    return {"id": saved_id}


@router.get("/saved/{scenario_id}")
def load_saved_scenario(
    scenario_id: str,
    simulator: ScenarioSimulator = Depends(get_scenario_simulator),
) -> Dict[str, Any]:
    scenario = simulator.load(scenario_id)
    return {"scenario": scenario.model_dump(mode="json")}
