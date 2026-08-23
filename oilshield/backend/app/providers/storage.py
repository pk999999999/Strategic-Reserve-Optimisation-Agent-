from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import closing
from pathlib import Path
from typing import Final

from pydantic import ValidationError as PydanticValidationError

from app.core.errors import ScenarioLoadError
from app.models import SavedScenario

__all__ = [
    "CURRENT_SCENARIO_VERSION",
    "MIN_SUPPORTED_SCENARIO_VERSION",
    "JsonFileScenarioRepository",
    "SqliteScenarioRepository",
]

CURRENT_SCENARIO_VERSION: Final[int] = 1
MIN_SUPPORTED_SCENARIO_VERSION: Final[int] = 1

_DATA_DIR: Final[Path] = Path(__file__).resolve().parent.parent / "data"
_DEFAULT_JSON_DIR: Final[Path] = _DATA_DIR / ".scenarios"
_DEFAULT_SQLITE_PATH: Final[Path] = _DATA_DIR / "scenarios.db"


def _new_id() -> str:
    return uuid.uuid4().hex


def _is_version_compatible(version: object) -> bool:
    return (
        isinstance(version, int)
        and not isinstance(version, bool)
        and MIN_SUPPORTED_SCENARIO_VERSION <= version <= CURRENT_SCENARIO_VERSION
    )


def _deserialize(payload: str, *, scenario_id: str) -> SavedScenario:
    try:
        raw = json.loads(payload)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ScenarioLoadError(
            f"Saved scenario '{scenario_id}' is malformed and could not be parsed: {exc}"
        ) from exc

    if not isinstance(raw, dict):
        raise ScenarioLoadError(
            f"Saved scenario '{scenario_id}' is malformed: expected an object, "
            f"got {type(raw).__name__}."
        )

    if not _is_version_compatible(raw.get("version")):
        raise ScenarioLoadError(
            f"Saved scenario '{scenario_id}' has an incompatible version "
            f"{raw.get('version')!r}; this build supports versions "
            f"{MIN_SUPPORTED_SCENARIO_VERSION}..{CURRENT_SCENARIO_VERSION}."
        )

    try:
        return SavedScenario.model_validate(raw)
    except PydanticValidationError as exc:
        raise ScenarioLoadError(
            f"Saved scenario '{scenario_id}' failed to deserialize: {exc}"
        ) from exc


class JsonFileScenarioRepository:
    def __init__(self, storage_dir: Path | str | None = None) -> None:
        self._dir = Path(storage_dir) if storage_dir is not None else _DEFAULT_JSON_DIR
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, scenario_id: str) -> Path:
        return self._dir / f"{scenario_id}.json"

    def save(self, record: SavedScenario) -> str:
        scenario_id = _new_id()
        payload = record.model_dump_json()
        path = self._path_for(scenario_id)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(path)
        return scenario_id

    def load(self, scenario_id: str) -> SavedScenario:
        path = self._path_for(scenario_id)
        try:
            payload = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise ScenarioLoadError(
                f"No saved scenario found for id '{scenario_id}'."
            ) from exc
        except OSError as exc:
            raise ScenarioLoadError(
                f"Saved scenario '{scenario_id}' could not be read: {exc}"
            ) from exc
        return _deserialize(payload, scenario_id=scenario_id)


class SqliteScenarioRepository:
    _TABLE: Final[str] = "saved_scenarios"

    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else _DEFAULT_SQLITE_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._db_path))

    def _ensure_schema(self) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._TABLE} (
                    id       TEXT PRIMARY KEY,
                    version  INTEGER NOT NULL,
                    payload  TEXT NOT NULL
                )
                """
            )

    def save(self, record: SavedScenario) -> str:
        scenario_id = _new_id()
        payload = record.model_dump_json()
        with closing(self._connect()) as conn, conn:
            conn.execute(
                f"""
                INSERT INTO {self._TABLE} (id, version, payload)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    version = excluded.version,
                    payload = excluded.payload
                """,
                (scenario_id, record.version, payload),
            )
        return scenario_id

    def load(self, scenario_id: str) -> SavedScenario:
        try:
            with closing(self._connect()) as conn:
                cursor = conn.execute(
                    f"SELECT payload FROM {self._TABLE} WHERE id = ?",
                    (scenario_id,),
                )
                row = cursor.fetchone()
        except sqlite3.Error as exc:
            raise ScenarioLoadError(
                f"Saved scenario '{scenario_id}' could not be read: {exc}"
            ) from exc

        if row is None:
            raise ScenarioLoadError(
                f"No saved scenario found for id '{scenario_id}'."
            )
        return _deserialize(row[0], scenario_id=scenario_id)
