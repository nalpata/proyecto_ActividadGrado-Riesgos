from pathlib import Path

import pandas as pd

from src.frontend.dashboard_data import load_project_scope_summary

from src.risk.project_resolution import (
    assign_projects,
    build_public_project_snapshot,
    resolve_project,
    validate_public_project_snapshot,
)


CATALOG = {
    "projects": [
        {"project_id": "ALPHA", "display_name": "Alpha", "aliases": ["Alpha"]},
        {"project_id": "BETA", "display_name": "Beta", "aliases": ["Beta"]},
    ],
    "unassigned_project_id": "PENDIENTE_PROYECTO",
    "multi_project_id": "MULTIPROYECTO",
}

ROOT = Path(__file__).resolve().parents[1]


def test_explicit_signal_assignment_wins():
    result = resolve_project("Retraso del proyecto Alpha", "entrega pendiente", "", "acta.pdf", CATALOG)
    assert result["project_id"] == "ALPHA"
    assert result["project_assignment_status"] == "ASSIGNED_SIGNAL_EXPLICIT"


def test_multiple_projects_are_not_forced_to_one():
    result = resolve_project("Comparación entre Alpha y Beta", "", "", "acta.pdf", CATALOG)
    assert result["project_id"] == "MULTIPROYECTO"
    assert result["project_assignment_status"] == "MULTI_PROJECT_SIGNAL"


def test_false_header_and_missing_evidence_stay_pending():
    result = resolve_project("Rol dentro del Proyecto Asistencia", "", "", "acta.pdf", CATALOG)
    assert result["project_id"] == "PENDIENTE_PROYECTO"
    assert result["project_assignment_status"] == "PENDING_NO_EVIDENCE"


def test_nearest_context_resolves_multi_project_chunk():
    chunk = "Proyecto Alpha: avance estable. Proyecto Beta: existe un atraso confirmado en pruebas."
    result = resolve_project("Existe un atraso", "atraso confirmado en pruebas", chunk, "acta.pdf", CATALOG)
    assert result["project_id"] == "BETA"
    assert result["project_assignment_status"] == "ASSIGNED_CONTEXT_NEAREST"


def _signals():
    return pd.DataFrame([
        {"item_id": "I1", "source_chunk_id": "C1", "source_filename": "acta.pdf", "source_doc_id": "D1", "title": "Riesgo Alpha", "statement": "demora", "evidence_quote": "demora", "calibrated_justification": "", "calibrated_category": "Cronograma", "pird_status": "CALCULADO", "pird": 60.0, "pird_level": "ALTO", "document_date": "2026-01-01", "temporal_role": "APARICION", "persistence_level": 2},
        {"item_id": "I2", "source_chunk_id": "C2", "source_filename": "acta.pdf", "source_doc_id": "D2", "title": "Sin proyecto", "statement": "demora", "evidence_quote": "demora", "calibrated_justification": "", "calibrated_category": "Calidad", "pird_status": "PENDIENTE_ENRIQUECIMIENTO", "pird": None, "pird_level": None, "document_date": None, "temporal_role": "PENDIENTE_FECHA", "persistence_level": None},
    ])


def test_public_snapshot_reconciles_and_contains_only_aggregates():
    chunks = pd.DataFrame([
        {"chunk_id": "C1", "chunk_text": "Alpha presenta demora", "filename": "acta.pdf"},
        {"chunk_id": "C2", "chunk_text": "No se identifica iniciativa", "filename": "acta.pdf"},
    ])
    tagged = assign_projects(_signals(), chunks, CATALOG)
    snapshot = build_public_project_snapshot(tagged, CATALOG)
    validate_public_project_snapshot(snapshot)
    assert snapshot["assignment"]["signals_total"] == 2
    assert snapshot["assignment"]["signals_assigned_single_project"] == 1
    assert snapshot["projects"][0]["profile"]["global_pird"] == 60.0
    serialized = str(snapshot)
    assert "demora" not in serialized
    assert "I1" not in serialized


def test_academic_demo_is_synthetic_reconciled_and_has_four_projects():
    demo = load_project_scope_summary(ROOT / "results/day_18/academic_project_demo.json")
    assert demo["scope_status"] == "SYNTHETIC_ACADEMIC_DEMONSTRATION"
    assert demo["data_policy"]["synthetic"] is True
    assert len(demo["projects"]) == 4
    assert demo["assignment"]["signals_assigned_single_project"] == 100
    assert sum(item["profile"]["signals_total"] for item in demo["projects"]) == 100
    assert all("Demostración sintética" in item["display_name"] for item in demo["projects"])


def test_academic_demo_contains_no_confidential_payload_fields():
    demo = load_project_scope_summary(ROOT / "results/day_18/academic_project_demo.json")
    serialized = str(demo).lower()
    forbidden = ("evidence_quote", "chunk_text", "source_filename", "document_name", "item_id")
    assert all(field not in serialized for field in forbidden)
