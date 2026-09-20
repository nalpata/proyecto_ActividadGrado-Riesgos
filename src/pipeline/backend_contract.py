"""Contrato público y estable del backend congelado en el Día 14."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


BACKEND_SCHEMA_VERSION = "1.0.0"


def _records(path: Path) -> list[dict[str, Any]]:
    if not Path(path).exists():
        raise FileNotFoundError(f"No existe el agregado requerido: {path}")
    return pd.read_csv(path).where(pd.notna, None).to_dict("records")


def validate_backend_snapshot(snapshot: dict[str, Any]) -> None:
    """Valida conciliaciones y campos que el front puede considerar estables."""

    required = {"schema_version", "profile", "categories", "level_distribution", "sensitivity", "runtime"}
    missing = required - set(snapshot)
    if missing:
        raise ValueError(f"Faltan secciones del contrato: {sorted(missing)}")
    if snapshot["schema_version"] != BACKEND_SCHEMA_VERSION:
        raise ValueError("Versión de contrato no soportada")

    profile = snapshot["profile"]
    if profile.get("profile_status") != "PROVISIONAL":
        raise ValueError("El perfil congelado debe conservar el estado PROVISIONAL")
    total = int(profile["signals_total"])
    scored = int(profile["signals_scored"])
    pending = int(profile["signals_pending"])
    if total != scored + pending:
        raise ValueError("No concilia signals_total = signals_scored + signals_pending")

    distributed = sum(int(row["signal_count"]) for row in snapshot["level_distribution"])
    if distributed != scored:
        raise ValueError("La distribución PIRD no concilia con signals_scored")
    expected_coverage = scored / total if total else 0.0
    if abs(float(profile["scoring_coverage"]) - expected_coverage) > 0.0001:
        raise ValueError("La cobertura no concilia con señales totales y puntuadas")

    category_total = sum(int(row["total_signals"]) for row in snapshot["categories"])
    category_scored = sum(int(row["scored_signals"]) for row in snapshot["categories"])
    if category_total != total or category_scored != scored:
        raise ValueError("El perfil por categoría no concilia con el perfil global")

    runtime = snapshot["runtime"]
    if runtime.get("private_payload_included") is not False:
        raise ValueError("El contrato público no puede incluir payload privado")


def build_backend_snapshot(
    profile_path: Path,
    categories_path: Path,
    distribution_path: Path,
    sensitivity_path: Path,
    runtime_summary_path: Path,
) -> dict[str, Any]:
    """Construye el único snapshot agregado que consumirá el front."""

    profile = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    runtime = json.loads(Path(runtime_summary_path).read_text(encoding="utf-8"))
    snapshot = {
        "schema_version": BACKEND_SCHEMA_VERSION,
        "contract_status": "FROZEN",
        "profile": profile,
        "categories": _records(categories_path),
        "level_distribution": _records(distribution_path),
        "sensitivity": _records(sensitivity_path),
        "runtime": runtime,
        "data_policy": {
            "aggregate_only": True,
            "contains_source_text": False,
            "contains_individual_signals": False,
            "null_policy": "No imputar componentes faltantes; conservar pendiente/null.",
        },
    }
    validate_backend_snapshot(snapshot)
    return snapshot


def write_backend_snapshot(snapshot: dict[str, Any], output_path: Path) -> None:
    """Escritura atómica para impedir snapshots parciales."""

    validate_backend_snapshot(snapshot)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
