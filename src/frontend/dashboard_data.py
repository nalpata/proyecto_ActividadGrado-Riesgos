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


def load_public_timeline_summary(path: Path) -> dict[str, Any]:
    """Carga únicamente conteos temporales agregados aprobados para publicación."""

    summary_path = Path(path)
    if not summary_path.exists():
        raise FileNotFoundError(f"No se encontró el resumen temporal: {summary_path}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    required = {"signals", "source_documents", "temporal_role_counts", "persistence_level_counts", "privacy"}
    if not required.issubset(summary):
        raise ValueError("El resumen temporal público está incompleto")
    if "not published" not in summary["privacy"]:
        raise ValueError("El resumen temporal no declara su política de privacidad")
    return summary


def load_project_scope_summary(path: Path) -> dict[str, Any]:
    """Carga la discriminación agregada por proyecto sin señales individuales."""

    summary_path = Path(path)
    if not summary_path.exists():
        raise FileNotFoundError(f"No se encontró el resumen por proyecto: {summary_path}")
    return validate_project_scope_summary(json.loads(summary_path.read_text(encoding="utf-8")))


def validate_project_scope_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Valida agregados privados recibidos en tiempo de ejecución."""

    required = {"schema_version", "scope_status", "catalog", "assignment", "projects", "data_policy"}
    if not required.issubset(summary):
        raise ValueError("El resumen por proyecto está incompleto")
    assignment = summary["assignment"]
    if int(assignment["signals_total"]) != int(assignment["signals_assigned_single_project"]) + int(assignment["signals_pending_or_ambiguous"]):
        raise ValueError("El resumen por proyecto no concilia")
    if summary["data_policy"].get("contains_source_text") is not False:
        raise ValueError("El resumen por proyecto no cumple la política de privacidad")
    if summary["data_policy"].get("contains_individual_signals") is not False:
        raise ValueError("El resumen por proyecto no puede contener señales individuales")
    project_total = sum(int(item["profile"]["signals_total"]) for item in summary["projects"])
    if project_total != int(assignment["signals_assigned_single_project"]):
        raise ValueError("Los proyectos no concilian con las señales asignadas")
    return summary


def project_by_name(summary: dict[str, Any], display_name: str) -> dict[str, Any] | None:
    return next((item for item in summary["projects"] if item["display_name"] == display_name), None)
