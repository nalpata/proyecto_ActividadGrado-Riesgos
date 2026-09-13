"""Modelo reproducible del Índice Compuesto de Riesgo PIRD."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional


EXPOSURE_WEIGHTS = {"severity": 0.40, "probability": 0.25, "recurrence": 0.20, "persistence": 0.15}
RELIABILITY_WEIGHTS = {"evidence": 0.60, "confidence": 0.40}
LEVEL_THRESHOLDS = [(25.0, "BAJO"), (50.0, "MEDIO"), (75.0, "ALTO"), (101.0, "CRITICO")]


@dataclass(frozen=True)
class PIRDInputs:
    severity: Optional[float]
    probability: Optional[float]
    recurrence: Optional[float]
    persistence: Optional[float]
    evidence: Optional[float]
    confidence: Optional[float]


def validate_level(value: Optional[float], name: str) -> None:
    if value is not None and not 1 <= float(value) <= 5:
        raise ValueError(f"{name} debe estar entre 1 y 5")


def normalize(value: float) -> float:
    """Convierte una rúbrica de 1 a 5 en escala de 0 a 1."""
    return (float(value) - 1.0) / 4.0


def risk_level(score: float) -> str:
    for upper, label in LEVEL_THRESHOLDS:
        if score < upper:
            return label
    raise ValueError("score debe estar entre 0 y 100")


def calculate_pird(inputs: PIRDInputs, exposure_weights=None, reliability_weights=None) -> dict:
    """Calcula PIRD solo cuando están disponibles los seis componentes."""
    values = asdict(inputs)
    for name, value in values.items():
        validate_level(value, name)
    missing = [name for name, value in values.items() if value is None]
    if missing:
        return {
            **values, "score_status": "PENDIENTE_ENRIQUECIMIENTO",
            "missing_components": missing, "exposure_index": None,
            "reliability_index": None, "pird": None, "risk_level": None,
        }

    ew = exposure_weights or EXPOSURE_WEIGHTS
    rw = reliability_weights or RELIABILITY_WEIGHTS
    if abs(sum(ew.values()) - 1.0) > 1e-9 or abs(sum(rw.values()) - 1.0) > 1e-9:
        raise ValueError("Los pesos de cada índice deben sumar 1")
    normalized = {name: normalize(value) for name, value in values.items()}
    exposure = sum(normalized[name] * weight for name, weight in ew.items())
    reliability = sum(normalized[name] * weight for name, weight in rw.items())
    score = round(100 * exposure * (0.70 + 0.30 * reliability), 2)
    return {
        **values, "score_status": "CALCULADO", "missing_components": [],
        "exposure_index": round(100 * exposure, 2),
        "reliability_index": round(100 * reliability, 2),
        "pird": score, "risk_level": risk_level(score),
        "component_contributions": {
            name: round(100 * normalized[name] * weight, 2) for name, weight in ew.items()
        },
    }
