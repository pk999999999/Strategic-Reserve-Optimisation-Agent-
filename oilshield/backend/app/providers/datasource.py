from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence

from app.core.errors import DataSourceError
from app.models import RawSignal

__all__ = ["SimulatedDataSource", "LiveDataSource"]

_DEFAULT_SIGNALS_PATH = Path(__file__).resolve().parent.parent / "data" / "signals.json"


class SimulatedDataSource:
    def __init__(self, signals_path: Optional[Path] = None) -> None:
        self._signals_path = Path(signals_path) if signals_path else _DEFAULT_SIGNALS_PATH
        self._feeds: Optional[Dict[str, List[dict]]] = None

    def _load_feeds(self) -> Dict[str, List[dict]]:
        if self._feeds is None:
            try:
                raw = self._signals_path.read_text(encoding="utf-8")
                data = json.loads(raw)
            except FileNotFoundError as exc:
                raise DataSourceError(
                    f"Bundled signals dataset not found at {self._signals_path}"
                ) from exc
            except json.JSONDecodeError as exc:
                raise DataSourceError(
                    f"Bundled signals dataset is not valid JSON: {exc}"
                ) from exc
            if not isinstance(data, dict):
                raise DataSourceError(
                    "Bundled signals dataset must be an object keyed by source id"
                )
            self._feeds = data
        return self._feeds

    def fetch_signals(self, source_id: str) -> List[RawSignal]:
        feeds = self._load_feeds()
        if source_id not in feeds:
            known = ", ".join(sorted(feeds)) or "<none>"
            raise DataSourceError(
                f"Unknown source_id '{source_id}'. Known sources: {known}"
            )
        return [RawSignal.model_validate(record) for record in feeds[source_id]]


_DEFAULT_GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

_DEFAULT_QUERIES: Dict[str, str] = {
    "news_feed": "oil OR crude OR petroleum",
    "sanctions_feed": "oil sanctions OR oil embargo OR price cap",
    "shipping_feed": "oil tanker OR strait OR shipping lane",
}

_LIVE_BASE_SEVERITY: float = 25.0
_LIVE_SEVERITY_KEYWORDS: Dict[str, float] = {
    "shutdown": 35.0,
    "blockade": 35.0,
    "closure": 30.0,
    "seize": 30.0,
    "seized": 30.0,
    "attack": 30.0,
    "missile": 30.0,
    "strike": 25.0,
    "sanction": 25.0,
    "embargo": 25.0,
    "war": 20.0,
    "conflict": 20.0,
    "disruption": 20.0,
    "escalate": 20.0,
    "tension": 18.0,
    "reroute": 15.0,
    "diversion": 15.0,
    "congestion": 15.0,
    "delay": 12.0,
}


def _clamp_0_100(value: float) -> float:
    return max(0.0, min(100.0, value))


class LiveDataSource:
    def __init__(
        self,
        *,
        queries: Optional[Mapping[str, str]] = None,
        known_targets: Optional[Sequence[str]] = None,
        base_url: str = _DEFAULT_GDELT_URL,
        timeout_seconds: float = 5.0,
        max_records: int = 25,
        client: Optional[object] = None,
    ) -> None:
        self._queries: Dict[str, str] = dict(queries or _DEFAULT_QUERIES)
        self._known_targets: List[str] = [t for t in (known_targets or []) if t]
        self._base_url = base_url
        self._timeout_seconds = timeout_seconds
        self._max_records = max_records
        self._client = client

    def fetch_signals(self, source_id: str) -> List[RawSignal]:
        import httpx

        query = self._queries.get(source_id, source_id)
        params = {
            "query": query,
            "format": "json",
            "mode": "artlist",
            "maxrecords": str(self._max_records),
            "sort": "datedesc",
        }

        try:
            if self._client is not None:
                response = self._client.get(
                    self._base_url, params=params, timeout=self._timeout_seconds
                )
            else:
                with httpx.Client(timeout=self._timeout_seconds) as client:
                    response = client.get(self._base_url, params=params)
            response.raise_for_status()
            payload = response.json()
        except DataSourceError:
            raise
        except Exception as exc:
            raise DataSourceError(
                f"Live data source '{source_id}' failed: {exc}"
            ) from exc

        return self._shape(payload, source_id)

    def _shape(self, payload: object, source_id: str) -> List[RawSignal]:
        if not isinstance(payload, dict):
            raise DataSourceError(
                f"Live data source '{source_id}' returned an unexpected payload shape"
            )
        articles = payload.get("articles", [])
        if not isinstance(articles, list):
            raise DataSourceError(
                f"Live data source '{source_id}' returned no article list"
            )

        signals: List[RawSignal] = []
        for article in articles:
            if not isinstance(article, dict):
                continue
            text = (article.get("title") or "").strip()
            if not text:
                continue
            source = (article.get("domain") or "gdelt").strip() or "gdelt"
            timestamp = self._parse_timestamp(article.get("seendate"))
            signals.append(
                RawSignal(
                    source=source,
                    timestamp=timestamp,
                    text=text,
                    raw_severity=self._heuristic_severity(text),
                    hinted_target=self._match_target(text),
                )
            )
        return signals

    def _match_target(self, text: str) -> Optional[str]:
        lowered = text.lower()
        for candidate in self._known_targets:
            if candidate.lower() in lowered:
                return candidate
        return None

    @staticmethod
    def _heuristic_severity(text: str) -> float:
        lowered = text.lower()
        severity = _LIVE_BASE_SEVERITY
        for keyword, weight in _LIVE_SEVERITY_KEYWORDS.items():
            if keyword in lowered:
                severity += weight
        return _clamp_0_100(severity)

    @staticmethod
    def _parse_timestamp(value: object) -> datetime:
        if isinstance(value, str) and value:
            for fmt in ("%Y%m%dT%H%M%SZ", "%Y-%m-%dT%H:%M:%SZ"):
                try:
                    return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
        return datetime.now(timezone.utc)
