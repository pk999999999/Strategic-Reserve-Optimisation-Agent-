from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple, Union

from app.core.constants import RISK_BAND_ELEVATED_MAX, RISK_BAND_LOW_MAX
from app.models import ExtractedSignal, RiskScore
from app.models.risk import RiskBand
from app.models.signals import TargetType

__all__ = ["KnownTarget", "RiskScoringEngine"]


@dataclass(frozen=True)
class KnownTarget:
    name: str
    target_type: TargetType


KnownTargetInput = Union[KnownTarget, Tuple[str, TargetType]]


class RiskScoringEngine:
    def __init__(self, known_targets: Iterable[KnownTargetInput]) -> None:
        self._targets: List[KnownTarget] = []
        self._by_norm: Dict[str, KnownTarget] = {}
        for item in known_targets:
            target = self._coerce(item)
            norm = self._normalize(target.name)
            if not norm or norm in self._by_norm:
                continue
            self._by_norm[norm] = target
            self._targets.append(target)

    @property
    def known_targets(self) -> List[KnownTarget]:
        return list(self._targets)

    def score(self, extracted: Iterable[ExtractedSignal]) -> List[RiskScore]:
        buckets: Dict[str, List[ExtractedSignal]] = {norm: [] for norm in self._by_norm}

        for signal in extracted:
            if not signal.classified or signal.target is None:
                continue
            norm = self._normalize(signal.target)
            bucket = buckets.get(norm)
            if bucket is None:
                continue
            bucket.append(signal)

        results: List[RiskScore] = []
        for norm, target in self._by_norm.items():
            contributing = buckets[norm]
            value = self._aggregate([s.severity for s in contributing])
            results.append(
                RiskScore(
                    target=target.name,
                    target_type=target.target_type,
                    score=value,
                    band=self.classify_band(value),
                    contributing_signal_ids=[s.signal_id for s in contributing],
                )
            )
        return results

    def ranked(self, extracted: Iterable[ExtractedSignal]) -> List[RiskScore]:
        return self.sort_by_score(self.score(extracted))

    @staticmethod
    def sort_by_score(scores: Sequence[RiskScore]) -> List[RiskScore]:
        return sorted(scores, key=lambda r: r.score, reverse=True)

    @staticmethod
    def classify_band(score: float) -> RiskBand:
        if score <= RISK_BAND_LOW_MAX:
            return "low"
        if score <= RISK_BAND_ELEVATED_MAX:
            return "elevated"
        return "high"

    @staticmethod
    def _aggregate(severities: Sequence[float]) -> float:
        product = 1.0
        for severity in severities:
            fraction = severity / 100.0
            if fraction < 0.0:
                fraction = 0.0
            elif fraction > 1.0:
                fraction = 1.0
            product *= 1.0 - fraction
        score = 100.0 * (1.0 - product)
        if score < 0.0:
            return 0.0
        if score > 100.0:
            return 100.0
        return score

    @staticmethod
    def _coerce(item: KnownTargetInput) -> KnownTarget:
        if isinstance(item, KnownTarget):
            return item
        name, target_type = item
        return KnownTarget(name=name, target_type=target_type)

    @staticmethod
    def _normalize(name: str) -> str:
        return name.strip().lower()
