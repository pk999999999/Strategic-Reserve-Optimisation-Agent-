from __future__ import annotations

from typing import Iterable, List, Optional

from app.core.config import get_settings
from app.core.errors import LLMError
from app.models import ExtractedSignal, Signal
from app.providers import DeterministicExtractor, LLMProvider

__all__ = ["LLMExtractor"]

_FALLBACK_CATEGORY = "unknown"


def _default_provider() -> LLMProvider:
    _ = get_settings().llm_provider
    return DeterministicExtractor()


class LLMExtractor:
    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        known_targets: Optional[Iterable[str]] = None,
    ) -> None:
        self._provider: LLMProvider = provider if provider is not None else _default_provider()
        self._known_targets: List[str] = list(known_targets) if known_targets else []
        self._known_lower = frozenset(t.strip().lower() for t in self._known_targets if t)

    @property
    def known_targets(self) -> List[str]:
        return list(self._known_targets)

    def extract(self, signal: Signal) -> ExtractedSignal:
        try:
            extracted = self._provider.extract(signal.text_summary, self._known_targets)
        except (LLMError, TimeoutError):
            extracted = self._fallback(signal)
        return self._attach_traceability(extracted, signal)

    def extract_batch(self, signals: Iterable[Signal]) -> List[ExtractedSignal]:
        return [self.extract(signal) for signal in signals]

    def _fallback(self, signal: Signal) -> ExtractedSignal:
        classifiable = signal.target.strip().lower() in self._known_lower
        return ExtractedSignal(
            signal_id=signal.id,
            source=signal.source,
            timestamp=signal.timestamp,
            target=signal.target if classifiable else None,
            target_type=signal.target_type if classifiable else None,
            risk_category=_FALLBACK_CATEGORY,
            severity=signal.raw_severity,
            classified=classifiable,
        )

    @staticmethod
    def _attach_traceability(
        extracted: ExtractedSignal, signal: Signal
    ) -> ExtractedSignal:
        return extracted.model_copy(
            update={
                "signal_id": signal.id,
                "source": signal.source,
                "timestamp": signal.timestamp,
            }
        )
