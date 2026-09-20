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
PIRD_LEVELS = ("BAJO", "MEDIO", "ALTO", "CRITICO")


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


def build_session_project_view(analysis: dict[str, Any], display_name: str) -> dict[str, Any]:
    """Convierte el resultado privado del 19B en agregados seguros para las vistas del 19C."""

    required = {"project_id", "summary", "classification", "timeline", "categories", "private"}
    if not required.issubset(analysis):
        raise ValueError("El análisis de sesión está incompleto")
    summary = analysis["summary"]
    required_summary = {
        "signals_validated", "signals_scored", "signals_pending", "scoring_coverage",
        "global_pird", "global_level", "profile_status",
    }
    if not required_summary.issubset(summary):
        raise ValueError("El resumen de riesgos de sesión está incompleto")

    categories = []
    category_fields = (
        "category", "category_score", "category_level", "scoring_coverage",
        "scored_signals", "total_signals",
    )
    for value in analysis.get("categories", []):
        if not set(category_fields).issubset(value):
            raise ValueError("Una categoría de sesión está incompleta")
        categories.append({field: value[field] for field in category_fields})

    counts = {level: 0 for level in PIRD_LEVELS}
    for value in analysis.get("private", {}).get("scored_signals", []):
        level = value.get("pird_level")
        if value.get("pird_status") == "CALCULADO" and level in counts:
            counts[level] += 1
    scored_total = sum(counts.values())
    distribution = [
        {
            "pird_level": level,
            "signal_count": counts[level],
            "percentage_of_scored": round(100 * counts[level] / scored_total, 2) if scored_total else 0.0,
        }
        for level in PIRD_LEVELS
    ]

    top_categories = [
        value["category"] for value in sorted(
            (item for item in categories if item["category_score"] is not None),
            key=lambda item: float(item["category_score"]), reverse=True,
        )[:3]
    ]
    profile = {
        "profile_status": summary["profile_status"],
        "signals_total": int(summary["signals_validated"]),
        "signals_scored": int(summary["signals_scored"]),
        "signals_pending": int(summary["signals_pending"]),
        "scoring_coverage": float(summary["scoring_coverage"]),
        "global_pird": summary["global_pird"],
        "global_level": summary["global_level"] or "PENDIENTE",
        "top_categories": top_categories,
        "critical_signals": counts["CRITICO"],
        "high_signals": counts["ALTO"],
        "calibration_status": analysis["classification"].get("calibration_status", "UNKNOWN"),
        "privacy": "Session aggregates only; source text and individual signals are not rendered.",
    }

    timeline = analysis.get("timeline", {})
    public_timeline = {
        "signals": int(timeline.get("signals", 0)),
        "source_documents": int(timeline.get("source_documents", 0)),
        "signals_with_document_date": int(timeline.get("signals_with_document_date", 0)),
        "signals_without_document_date": int(timeline.get("signals_without_document_date", 0)),
        "signals_with_persistence": int(timeline.get("signals_with_persistence", 0)),
        "temporal_role_counts": {
            str(key): int(value) for key, value in timeline.get("temporal_role_counts", {}).items()
        },
        "persistence_level_counts": {
            str(key): int(value) for key, value in timeline.get("persistence_level_counts", {}).items()
        },
        "privacy": "Document names, dates and individual signals are not rendered.",
    }
    return {
        "project_id": str(analysis["project_id"]),
        "display_name": str(display_name),
        "source": "SESSION_DAY_19B",
        "profile": profile,
        "categories": categories,
        "level_distribution": distribution,
        "timeline": public_timeline,
        "data_policy": {"contains_source_text": False, "contains_individual_signals": False},
    }
