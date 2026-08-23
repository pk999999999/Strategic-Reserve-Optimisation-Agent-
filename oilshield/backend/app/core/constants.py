from typing import Final

TOTAL_IMPORT_KBD: Final[float] = 5000.0
K_REF: Final[float] = 0.8
K_PRICE: Final[float] = 1.5
K_GDP: Final[float] = 0.5
DRAWDOWN_DIVISOR: Final[float] = 2.0

W_PRICE: Final[float] = 0.35
W_AVAIL: Final[float] = 0.20
W_CONGEST: Final[float] = 0.15
W_COMPAT: Final[float] = 0.30

assert abs((W_PRICE + W_AVAIL + W_CONGEST + W_COMPAT) - 1.0) < 1e-9, (
    "Procurement weights must sum to 1.0"
)

PRICE_FLOOR: Final[float] = 40.0
PRICE_CEILING: Final[float] = 120.0
MIN_COMPAT: Final[float] = 0.4

RISK_BAND_LOW_MAX: Final[float] = 33.0
RISK_BAND_ELEVATED_MAX: Final[float] = 66.0
