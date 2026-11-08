import json
from pathlib import Path

import pandas as pd
import pytest

from src.risk.corpus_project_catalog import load_catalog, reconcile_chunks
from src.risk.project_scope import annotate_chunks, scope_signals, subdivision_assignment


ROOT = Path(__file__).resolve().parents[1]


def catalog():
    return load_catalog(ROOT / "config/project_catalog.json")


def test_all_projects_are_considered_before_assigning_datar():
    chunks = pd.DataFrame([
        {"chunk_id": "C1", "filename": "acta.pdf", "chunk_text": "DataR depende de NSGT y PDIS."},
        {"chunk_id": "C2", "filename": "acta.pdf", "chunk_text": "NSGT continúa pendiente."},
    ])
    tagged, summary = reconcile_chunks(chunks, catalog())
    assert tagged.iloc[0].project_assignment_status == "AMBIGUOUS_CONTEXT"
    assert tagged.iloc[1].project_ids == "NSGT"
    assert summary["chunks_single_project"] + summary["chunks_ambiguous"] + summary["chunks_pending"] == 2


def test_multinube_lots_do_not_create_extra_projects_or_duplicate_chunks():
    data = [{"chunk_id": "C1", "filename": "acta.pdf", "chunk_text": "Multinube Lote 1 y Lote 2."}]
    summary = annotate_chunks(data, "MULTINUBE", catalog())
    assert len(catalog()["projects"]) == 5
    assert summary["chunks_active_project"] == 1
    assert data[0]["detected_subdivision_id"] is None
    assert data[0]["subdivision_status"] == "AMBIGUOUS"
    single = subdivision_assignment("MULTINUBE", catalog(), "Lote 2 registra un atraso.", data[0]["chunk_text"])
    assert single["detected_subdivision_id"] == "LOTE_2"
    assert subdivision_assignment("DATAR", catalog(), "Lote 2")["subdivision_status"] == "NOT_APPLICABLE"


def test_quote_preserves_lot_without_expanding_project_scope():
    text = "Multinube: Lote 1 registra un atraso. Lote 2 opera normalmente."
    items = pd.DataFrame([{"source_chunk_id": "C1", "evidence_quote": "Lote 1 registra un atraso."}])
    chunks = pd.DataFrame([{"chunk_id": "C1", "filename": "acta.pdf", "chunk_text": text}])
    tagged, _ = scope_signals(items, chunks, "MULTINUBE", catalog())
    assert tagged.iloc[0].project_scope_included
    assert tagged.iloc[0].detected_subdivision_id == "LOTE_1"


def test_reconciliation_accounts_for_every_baseline_chunk_including_zero_project_evidence():
    chunks = pd.read_csv(ROOT / "data/processed/chunks/chunks_recursive.csv")
    assignments, summary = reconcile_chunks(chunks, catalog())
    assert len(assignments) == len(chunks)
    assert summary["chunks_total"] == sum(summary[k] for k in ("chunks_single_project", "chunks_ambiguous", "chunks_pending"))
    assert {p["project_id"] for p in summary["projects"]} == {"DATAR", "MULTINUBE", "NSGA", "NSGT", "PDIS"}
    assert sum(p["chunks_single_project"] for p in summary["projects"]) == summary["chunks_single_project"]
    with pytest.raises(ValueError, match="únicos"):
        reconcile_chunks(pd.concat([chunks, chunks.iloc[:1]]), catalog())


def test_private_override_remains_available_without_replacing_default_file():
    original = (ROOT / "config/project_catalog.json").read_bytes()
    override = catalog()
    override["projects"] = override["projects"][:1]
    assert len(load_catalog(ROOT / "config/project_catalog.json", json.dumps(override))["projects"]) == 1
    assert (ROOT / "config/project_catalog.json").read_bytes() == original
