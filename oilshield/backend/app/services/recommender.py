from __future__ import annotations

import json
from pathlib import Path
from typing import List

from app.core.constants import (
    MIN_COMPAT,
    PRICE_CEILING,
    PRICE_FLOOR,
    W_AVAIL,
    W_COMPAT,
    W_CONGEST,
    W_PRICE,
)
from app.models import ProcurementOption

__all__ = ["ProcurementRecommender"]

_DEFAULT_OPTIONS_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "procurement_options.json"
)

_OPTIONS_KEY = "procurement_options"


def _clamp(value: float, low: float, high: float) -> float:
    if value < low:
        return low
    if value > high:
        return high
    return value


class ProcurementRecommender:
    def __init__(self, options_path: Path | None = None) -> None:
        self._options_path: Path = (
            options_path if options_path is not None else _DEFAULT_OPTIONS_PATH
        )

    def recommend(self) -> List[ProcurementOption]:
        scored: List[ProcurementOption] = []
        for raw in self._load_raw_options():
            if float(raw["grade_compatibility"]) < MIN_COMPAT:
                continue
            scored.append(self._score_option(raw))

        scored.sort(key=lambda option: option.recommendation_score, reverse=True)
        return scored

    def _load_raw_options(self) -> List[dict]:
        with self._options_path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        return list(payload[_OPTIONS_KEY])

    def _score_option(self, raw: dict) -> ProcurementOption:
        spot_price = float(raw["spot_price_usd_bbl"])
        availability = float(raw["tanker_availability"])
        congestion = float(raw["port_congestion"])
        compatibility = float(raw["grade_compatibility"])

        price_score = _clamp(
            (PRICE_CEILING - spot_price) / (PRICE_CEILING - PRICE_FLOOR), 0.0, 1.0
        )
        avail_score = availability
        congest_score = 1.0 - congestion
        compat_score = compatibility

        recommendation_score = 100.0 * (
            W_PRICE * price_score
            + W_AVAIL * avail_score
            + W_CONGEST * congest_score
            + W_COMPAT * compat_score
        )
        recommendation_score = _clamp(recommendation_score, 0.0, 100.0)

        rationale = self._build_rationale(
            supplier_country=str(raw["supplier_country"]),
            crude_grade=str(raw["crude_grade"]),
            spot_price=spot_price,
            price_score=price_score,
            avail_score=avail_score,
            congest_score=congest_score,
            compat_score=compat_score,
        )

        return ProcurementOption(
            id=str(raw["id"]),
            supplier_country=str(raw["supplier_country"]),
            crude_grade=str(raw["crude_grade"]),
            tanker_route=str(raw["tanker_route"]),
            spot_price_usd_bbl=spot_price,
            tanker_availability=availability,
            port_congestion=congestion,
            grade_compatibility=compatibility,
            recommendation_score=recommendation_score,
            rationale=rationale,
        )

    @staticmethod
    def _build_rationale(
        *,
        supplier_country: str,
        crude_grade: str,
        spot_price: float,
        price_score: float,
        avail_score: float,
        congest_score: float,
        compat_score: float,
    ) -> str:
        attributes = {
            "price": (price_score, f"an attractive spot price near ${spot_price:.0f}/bbl"),
            "availability": (avail_score, "strong tanker availability"),
            "congestion": (congest_score, "low port congestion"),
            "compatibility": (compat_score, "high refinery grade compatibility"),
        }
        ranked = sorted(attributes.values(), key=lambda item: item[0], reverse=True)

        strongest_phrase = ranked[0][1]
        second_phrase = ranked[1][1]

        weakest_score, weakest_desc = ranked[-1]
        weak_phrases = {
            "an attractive spot price near ${:.0f}/bbl".format(spot_price): (
                "a higher spot price"
            ),
            "strong tanker availability": "tighter tanker availability",
            "low port congestion": "heavier port congestion",
            "high refinery grade compatibility": "weaker grade compatibility",
        }

        lead = (
            f"{crude_grade} from {supplier_country} scores well on "
            f"{strongest_phrase} and {second_phrase}"
        )
        if weakest_score < 0.6:
            caveat = weak_phrases.get(weakest_desc, "some weaker attributes")
            return f"{lead}, though it is held back by {caveat}."
        return f"{lead}, with no major weaknesses across its attributes."
