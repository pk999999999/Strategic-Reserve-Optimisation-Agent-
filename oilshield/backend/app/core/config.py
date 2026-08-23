from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, field_validator

DataSourceMode = Literal["live", "simulated"]
LLMProviderName = Literal["groq", "gemini", "deterministic"]

ENV_DATA_SOURCE_MODE = "DATA_SOURCE_MODE"
ENV_LLM_PROVIDER = "LLM_PROVIDER"
ENV_GROQ_API_KEY = "GROQ_API_KEY"
ENV_GEMINI_API_KEY = "GEMINI_API_KEY"
ENV_LLM_TIMEOUT_SECONDS = "LLM_TIMEOUT_SECONDS"

DEFAULT_DATA_SOURCE_MODE: DataSourceMode = "simulated"
DEFAULT_LLM_PROVIDER: LLMProviderName = "deterministic"
DEFAULT_LLM_TIMEOUT_SECONDS: float = 3.0


class Settings(BaseModel):
    data_source_mode: DataSourceMode = DEFAULT_DATA_SOURCE_MODE
    llm_provider: LLMProviderName = DEFAULT_LLM_PROVIDER
    groq_api_key: str | None = None
    gemini_api_key: str | None = None
    llm_timeout_seconds: float = Field(
        default=DEFAULT_LLM_TIMEOUT_SECONDS,
        gt=0,
    )

    model_config = {"frozen": True}

    @field_validator("data_source_mode", "llm_provider", mode="before")
    @classmethod
    def _normalize_enum(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("groq_api_key", "gemini_api_key", mode="before")
    @classmethod
    def _blank_key_is_none(cls, value: object) -> object:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value


def _load_from_environ(environ: dict[str, str] | None = None) -> Settings:
    env = os.environ if environ is None else environ

    raw: dict[str, object] = {}
    if ENV_DATA_SOURCE_MODE in env:
        raw["data_source_mode"] = env[ENV_DATA_SOURCE_MODE]
    if ENV_LLM_PROVIDER in env:
        raw["llm_provider"] = env[ENV_LLM_PROVIDER]
    if ENV_GROQ_API_KEY in env:
        raw["groq_api_key"] = env[ENV_GROQ_API_KEY]
    if ENV_GEMINI_API_KEY in env:
        raw["gemini_api_key"] = env[ENV_GEMINI_API_KEY]
    if ENV_LLM_TIMEOUT_SECONDS in env:
        raw["llm_timeout_seconds"] = env[ENV_LLM_TIMEOUT_SECONDS]

    return Settings(**raw)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return _load_from_environ()
