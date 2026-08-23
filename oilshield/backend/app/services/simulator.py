from __future__ import annotations

import math
from typing import Dict, List, Optional

from app.core.constants import (
    DRAWDOWN_DIVISOR,
    K_GDP,
    K_PRICE,
    K_REF,
    TOTAL_IMPORT_KBD,
)
from app.core.errors import ScenarioLoadError, ValidationError
from app.models import (
    ImpactPoint,
    ImpactResult,
    SavedScenario,
    Scenario,
    ScenarioAssumption,
)
from app.providers import JsonFileScenarioRepository, ScenarioRepository
from app.providers.storage import CURRENT_SCENARIO_VERSION

__all__ = ["ScenarioSimulator"]

KEY_CLOSURE_PCT = "corridor_closure_pct"
KEY_PRODUCTION_CUT = "production_cut_kbd"
KEY_DURATION_DAYS = "duration_days"
KEY_IMPORT_SHARE = "corridor_import_share"
KEY_SPR_START = "spr_start_days"

_HORMUZ_IMPORT_SHARE = 0.62
_RED_SEA_IMPORT_SHARE = 0.14
_DEFAULT_SPR_START = 9.5


def _clamp(value: float, low: float, high: float) -> float:
    if value < low:
        return low
    if value > high:
        return high
    return value


def _is_real_number(value: object) -> bool:
    if isinstance(value, bool):
        return False
    if not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))


class ScenarioSimulator:
    def __init__(self, repository: Optional[ScenarioRepository] = None) -> None:
        self._repository: ScenarioRepository = (
            repository if repository is not None else JsonFileScenarioRepository()
        )
        self._catalog: Dict[str, Scenario] = {
            scenario.id: scenario for scenario in self._build_catalog()
        }

    def list_scenarios(self) -> List[Scenario]:
        return [scenario.model_copy(deep=True) for scenario in self._catalog.values()]

    def get_scenario(self, scenario_id: str) -> Scenario:
        scenario = self._catalog.get(scenario_id)
        if scenario is None:
            raise ValidationError(
                f"Unknown scenario id '{scenario_id}'. Known ids: "
                f"{sorted(self._catalog)}."
            )
        return scenario.model_copy(deep=True)

    def apply_assumption(
        self, scenario: Scenario, key: str, value: float
    ) -> Scenario:
        updated = scenario.model_copy(deep=True)
        target = next((a for a in updated.assumptions if a.key == key), None)

        if target is None:
            raise ValidationError(
                f"Scenario '{scenario.name}' has no assumption '{key}'."
            )

        if not target.adjustable:
            raise ValidationError(
                f"Assumption '{key}' is not adjustable.",
            )

        if not _is_real_number(value):
            err = ValidationError(
                f"Value {value!r} for '{key}' is not a valid number; "
                f"the valid range is [{target.min_value}, {target.max_value}]."
            )
            err.valid_range = (target.min_value, target.max_value)  # type: ignore[attr-defined]
            err.assumption_key = key  # type: ignore[attr-defined]
            raise err

        numeric = float(value)
        if not (target.min_value <= numeric <= target.max_value):
            err = ValidationError(
                f"Value {numeric} for '{key}' is outside the valid range "
                f"[{target.min_value}, {target.max_value}]."
            )
            err.valid_range = (target.min_value, target.max_value)  # type: ignore[attr-defined]
            err.assumption_key = key  # type: ignore[attr-defined]
            raise err

        target.value = numeric
        return updated

    def run(self, scenario: Scenario) -> ImpactResult:
        share = self._value(scenario, KEY_IMPORT_SHARE, 0.0)
        closure_pct = self._value(scenario, KEY_CLOSURE_PCT, 0.0)
        production_cut = self._value(scenario, KEY_PRODUCTION_CUT, 0.0)
        spr_start = self._value(scenario, KEY_SPR_START, _DEFAULT_SPR_START)

        duration_days = int(self._value(scenario, KEY_DURATION_DAYS, 1.0))
        if duration_days < 1:
            duration_days = 1

        supply_loss_fraction = _clamp(
            share * (closure_pct / 100.0) + production_cut / TOTAL_IMPORT_KBD,
            0.0,
            1.0,
        )

        timeline: List[ImpactPoint] = []
        for day in range(1, duration_days + 1):
            run_rate = _clamp(100.0 - K_REF * supply_loss_fraction * 100.0, 0.0, 100.0)
            fuel_price = 100.0 * (1.0 + K_PRICE * supply_loss_fraction)
            spr = max(
                0.0,
                spr_start - day * supply_loss_fraction / DRAWDOWN_DIVISOR,
            )
            gdp = 100.0 * (
                1.0 - K_GDP * supply_loss_fraction * (day / duration_days)
            )
            timeline.append(
                ImpactPoint(
                    day=day,
                    refinery_run_rate_pct=run_rate,
                    fuel_price_index=fuel_price,
                    spr_days_of_cover=spr,
                    gdp_index=gdp,
                )
            )

        last = timeline[-1]
        summary: Dict[str, float] = {
            "supply_loss_fraction": supply_loss_fraction,
            "refinery_run_rate_pct_end": last.refinery_run_rate_pct,
            "refinery_run_rate_delta_pct": last.refinery_run_rate_pct - 100.0,
            "fuel_price_index_end": last.fuel_price_index,
            "fuel_price_index_delta": last.fuel_price_index - 100.0,
            "spr_days_of_cover_end": last.spr_days_of_cover,
            "spr_days_of_cover_delta": last.spr_days_of_cover - spr_start,
            "gdp_index_end": last.gdp_index,
            "gdp_index_delta": last.gdp_index - 100.0,
        }

        return ImpactResult(
            scenario_id=scenario.id,
            assumptions_used=[a.model_copy(deep=True) for a in scenario.assumptions],
            timeline=timeline,
            summary=summary,
        )

    def save(self, scenario: Scenario) -> str:
        record = SavedScenario(
            version=CURRENT_SCENARIO_VERSION,
            name=scenario.name,
            assumptions=[a.model_copy(deep=True) for a in scenario.assumptions],
        )
        return self._repository.save(record)

    def load(self, scenario_id: str) -> Scenario:
        saved: SavedScenario = self._repository.load(scenario_id)

        template = next(
            (s for s in self._catalog.values() if s.name == saved.name), None
        )
        restored_id = template.id if template is not None else f"loaded-{scenario_id}"
        restored_corridor = template.corridor if template is not None else ""

        return Scenario(
            id=restored_id,
            name=saved.name,
            corridor=restored_corridor,
            assumptions=[a.model_copy(deep=True) for a in saved.assumptions],
        )

    @staticmethod
    def _value(scenario: Scenario, key: str, default: float) -> float:
        for assumption in scenario.assumptions:
            if assumption.key == key:
                return float(assumption.value)
        return default

    def _build_catalog(self) -> List[Scenario]:
        return [
            self._hormuz_partial_closure(),
            self._opec_production_cut(),
            self._red_sea_shutdown(),
        ]

    def _hormuz_partial_closure(self) -> Scenario:
        return Scenario(
            id="hormuz_partial_closure",
            name="Strait of Hormuz partial closure",
            corridor="Strait of Hormuz",
            assumptions=[
                ScenarioAssumption(
                    key=KEY_CLOSURE_PCT,
                    label="Corridor closure",
                    value=50.0,
                    min_value=0.0,
                    max_value=100.0,
                    adjustable=True,
                    unit="%",
                ),
                ScenarioAssumption(
                    key=KEY_IMPORT_SHARE,
                    label="Corridor import share",
                    value=_HORMUZ_IMPORT_SHARE,
                    min_value=0.0,
                    max_value=1.0,
                    adjustable=False,
                    unit="fraction",
                ),
                ScenarioAssumption(
                    key=KEY_PRODUCTION_CUT,
                    label="OPEC+ production cut",
                    value=0.0,
                    min_value=0.0,
                    max_value=5000.0,
                    adjustable=False,
                    unit="kbd",
                ),
                ScenarioAssumption(
                    key=KEY_DURATION_DAYS,
                    label="Duration",
                    value=30.0,
                    min_value=1.0,
                    max_value=180.0,
                    adjustable=True,
                    unit="days",
                ),
                ScenarioAssumption(
                    key=KEY_SPR_START,
                    label="SPR starting days-of-cover",
                    value=_DEFAULT_SPR_START,
                    min_value=0.0,
                    max_value=120.0,
                    adjustable=True,
                    unit="days",
                ),
            ],
        )

    def _opec_production_cut(self) -> Scenario:
        return Scenario(
            id="opec_production_cut",
            name="OPEC+ production cut",
            corridor="Global / OPEC+",
            assumptions=[
                ScenarioAssumption(
                    key=KEY_PRODUCTION_CUT,
                    label="OPEC+ production cut",
                    value=2000.0,
                    min_value=0.0,
                    max_value=5000.0,
                    adjustable=True,
                    unit="kbd",
                ),
                ScenarioAssumption(
                    key=KEY_CLOSURE_PCT,
                    label="Corridor closure",
                    value=0.0,
                    min_value=0.0,
                    max_value=100.0,
                    adjustable=False,
                    unit="%",
                ),
                ScenarioAssumption(
                    key=KEY_IMPORT_SHARE,
                    label="Corridor import share",
                    value=0.0,
                    min_value=0.0,
                    max_value=1.0,
                    adjustable=False,
                    unit="fraction",
                ),
                ScenarioAssumption(
                    key=KEY_DURATION_DAYS,
                    label="Duration",
                    value=60.0,
                    min_value=1.0,
                    max_value=180.0,
                    adjustable=True,
                    unit="days",
                ),
                ScenarioAssumption(
                    key=KEY_SPR_START,
                    label="SPR starting days-of-cover",
                    value=_DEFAULT_SPR_START,
                    min_value=0.0,
                    max_value=120.0,
                    adjustable=True,
                    unit="days",
                ),
            ],
        )

    def _red_sea_shutdown(self) -> Scenario:
        return Scenario(
            id="red_sea_shutdown",
            name="Red Sea shutdown",
            corridor="Red Sea",
            assumptions=[
                ScenarioAssumption(
                    key=KEY_CLOSURE_PCT,
                    label="Corridor closure",
                    value=100.0,
                    min_value=0.0,
                    max_value=100.0,
                    adjustable=True,
                    unit="%",
                ),
                ScenarioAssumption(
                    key=KEY_IMPORT_SHARE,
                    label="Corridor import share",
                    value=_RED_SEA_IMPORT_SHARE,
                    min_value=0.0,
                    max_value=1.0,
                    adjustable=False,
                    unit="fraction",
                ),
                ScenarioAssumption(
                    key=KEY_PRODUCTION_CUT,
                    label="OPEC+ production cut",
                    value=0.0,
                    min_value=0.0,
                    max_value=5000.0,
                    adjustable=False,
                    unit="kbd",
                ),
                ScenarioAssumption(
                    key=KEY_DURATION_DAYS,
                    label="Duration",
                    value=45.0,
                    min_value=1.0,
                    max_value=180.0,
                    adjustable=True,
                    unit="days",
                ),
                ScenarioAssumption(
                    key=KEY_SPR_START,
                    label="SPR starting days-of-cover",
                    value=_DEFAULT_SPR_START,
                    min_value=0.0,
                    max_value=120.0,
                    adjustable=True,
                    unit="days",
                ),
            ],
        )
