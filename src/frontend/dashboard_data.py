"""Carga segura del contrato congelado que consume el front."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.pipeline.backend_contract import BACKEND_SCHEMA_VERSION, validate_backend_snapshot

NAVIGATION = (
    "Portada", "Proyectos y documentos", "Resumen ejecutivo", "Radar de riesgos", "Timeline", "Riesgos priorizados",
    "Perfil del proyecto", "Pregunte a sus documentos", "Metodología y métricas",
)

SUPPORTED_DOCUMENT_TYPES = ("pdf", "docx")
DEMO_PROJECT = "Interventoría técnica · Proyecto demostrativo"


def load_front_snapshot(path: Path) -> dict[str, Any]:
    """Carga y valida el único contrato permitido para la estructura pública."""

    snapshot_path = Path(path)
    if not snapshot_path.exists():
        raise FileNotFoundError(f"No se encontró el contrato del backend: {snapshot_path}")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    validate_backend_snapshot(snapshot)
    if snapshot["schema_version"] != BACKEND_SCHEMA_VERSION:
        raise ValueError("El front no soporta esta versión del contrato")
    return snapshot
