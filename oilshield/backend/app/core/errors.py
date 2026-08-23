from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

__all__ = [
    "OilShieldError",
    "DataSourceError",
    "LLMError",
    "NormalizationError",
    "ValidationError",
    "ScenarioLoadError",
    "oilshield_error_handler",
    "register_error_handlers",
]


class OilShieldError(Exception):
    module: str = "backend"
    code: str = "OILSHIELD_ERROR"
    http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(
        self,
        message: str,
        *,
        module: str | None = None,
        code: str | None = None,
        http_status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if module is not None:
            self.module = module
        if code is not None:
            self.code = code
        if http_status is not None:
            self.http_status = http_status

    def to_envelope(self) -> dict[str, dict[str, str]]:
        return {
            "error": {
                "module": self.module,
                "message": self.message,
                "code": self.code,
            }
        }


class DataSourceError(OilShieldError):
    module = "signal_ingestion"
    code = "DATA_SOURCE_ERROR"
    http_status = status.HTTP_502_BAD_GATEWAY


class LLMError(OilShieldError):
    module = "llm_extractor"
    code = "LLM_ERROR"
    http_status = status.HTTP_502_BAD_GATEWAY


class NormalizationError(OilShieldError):
    module = "signal_ingestion"
    code = "NORMALIZATION_ERROR"
    http_status = status.HTTP_422_UNPROCESSABLE_ENTITY


class ValidationError(OilShieldError):
    module = "scenario_simulator"
    code = "VALIDATION_ERROR"
    http_status = status.HTTP_400_BAD_REQUEST


class ScenarioLoadError(OilShieldError):
    module = "scenario_simulator"
    code = "SCENARIO_LOAD_ERROR"
    http_status = status.HTTP_400_BAD_REQUEST


async def oilshield_error_handler(
    _request: Request, exc: OilShieldError
) -> JSONResponse:
    return JSONResponse(status_code=exc.http_status, content=exc.to_envelope())


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(OilShieldError, oilshield_error_handler)
