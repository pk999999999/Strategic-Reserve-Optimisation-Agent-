from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from pydantic import ValidationError as PydanticValidationError

from app.core.config import Settings, get_settings
from app.core.errors import DataSourceError, NormalizationError
from app.models import DataSourceMode, RawSignal, Signal, TargetType
from app.providers import DataSourceProvider, SimulatedDataSource

__all__ = ["IngestionResult", "SignalIngestionService"]

_CORRIDOR_NAMES: frozenset[str] = frozenset(
    {"strait of hormuz", "red sea", "cape of good hope"}
)

DEFAULT_SOURCE_IDS: Tuple[str, ...] = ("news_feed", "sanctions_feed", "shipping_feed")


@dataclass(frozen=True)
class IngestionResult:
    signals: List[Signal] = field(default_factory=list)
    data_source_modes: Dict[str, DataSourceMode] = field(default_factory=dict)


class SignalIngestionService:
    def __init__(
        self,
        primary: Optional[DataSourceProvider] = None,
        source_ids: Optional[Sequence[str]] = None,
        *,
        fallback: Optional[DataSourceProvider] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        resolved_settings = settings or get_settings()
        self._fallback: DataSourceProvider = fallback or SimulatedDataSource()
        self._source_ids: Tuple[str, ...] = tuple(source_ids or DEFAULT_SOURCE_IDS)

        if primary is None:
            self._primary: DataSourceProvider = self._fallback
            self._primary_mode: DataSourceMode = "simulated"
        else:
            self._primary = primary
            self._primary_mode = (
                "live" if resolved_settings.data_source_mode == "live" else "simulated"
            )

    @property
    def source_ids(self) -> Tuple[str, ...]:
        return self._source_ids

    def refresh(self) -> IngestionResult:
        signals: List[Signal] = []
        modes: Dict[str, DataSourceMode] = {}

        for source_id in self._source_ids:
            raw_signals, mode = self._fetch_source(source_id)
            modes[source_id] = mode
            for raw in raw_signals:
                signals.append(self._normalize(raw, source_id, mode))

        return IngestionResult(signals=signals, data_source_modes=modes)

    def _fetch_source(
        self, source_id: str
    ) -> Tuple[List[RawSignal], DataSourceMode]:
        try:
            return list(self._primary.fetch_signals(source_id)), self._primary_mode
        except DataSourceError:
            if self._primary is self._fallback:
                raise
            return list(self._fallback.fetch_signals(source_id)), "simulated"

    def _normalize(
        self, raw: RawSignal, source_id: str, mode: DataSourceMode
    ) -> Signal:
        target, target_type = self._resolve_target(raw.hinted_target)
        if target is None or target_type is None:
            raise NormalizationError(
                "Raw signal from source "
                f"'{source_id}' has no resolvable target (hinted_target="
                f"{raw.hinted_target!r}); cannot normalize into a Signal. "
                f"Offending signal: source={raw.source!r}, "
                f"timestamp={raw.timestamp.isoformat()}, text={raw.text!r}"
            )

        try:
            return Signal(
                id=self._signal_id(raw),
                source=raw.source,
                timestamp=raw.timestamp,
                text_summary=raw.text,
                target=target,
                target_type=target_type,
                raw_severity=raw.raw_severity,
                data_source_mode=mode,
            )
        except PydanticValidationError as exc:
            raise NormalizationError(
                "Raw signal from source "
                f"'{source_id}' failed normalization: {exc.errors()!r}. "
                f"Offending signal: source={raw.source!r}, "
                f"timestamp={raw.timestamp.isoformat()}, "
                f"raw_severity={raw.raw_severity!r}, text={raw.text!r}"
            ) from exc

    @staticmethod
    def _resolve_target(
        hinted_target: Optional[str],
    ) -> Tuple[Optional[str], Optional[TargetType]]:
        if hinted_target is None:
            return None, None
        cleaned = hinted_target.strip()
        if not cleaned:
            return None, None
        if cleaned.lower() in _CORRIDOR_NAMES:
            return cleaned, "corridor"
        return cleaned, "country"

    @staticmethod
    def _signal_id(raw: RawSignal) -> str:
        basis = f"{raw.source}|{raw.timestamp.isoformat()}|{raw.text}"
        digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:12]
        return f"sig_{digest}"
