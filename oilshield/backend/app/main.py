from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.pipeline import router as pipeline_router
from app.api.risk import router as risk_router
from app.api.procurement import router as procurement_router
from app.api.scenarios import router as scenarios_router
from app.api.signals import router as signals_router
from app.core.errors import register_error_handlers

app = FastAPI(
    title="OilShield Command Center API",
    description=(
        "Backend for the OilShield integrated resilience command center: "
        "live risk radar, disruption scenario simulator, and adaptive "
        "procurement recommendations for India's crude oil supply chain."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

app.include_router(signals_router)
app.include_router(risk_router)
app.include_router(scenarios_router)
app.include_router(procurement_router)
app.include_router(pipeline_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "oilshield-backend"}
