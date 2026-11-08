import copy
import hashlib
import json
from pathlib import Path

import fitz
import pandas as pd
import pytest

from src.risk.verified_document_dates import verify_document_dates
from src.risk.recompute_historical_projects import recompute_projects
from test_recompute_historical_projects import fixture


def source(tmp_path):
    path = tmp_path / "acta.pdf"
    doc = fitz.open()
    doc.new_page().insert_text((40, 60), "Fecha de reunion: 17 de abril de 2024")
    doc.save(path)
    doc.close()
    return {"version": "DOCUMENT-DATES-1", "documents": [{
        "filename": path.name, "date_observed": "2024-04-17", "date_precision": "DAY",
        "source_page": 1, "source_quote": "17 de abril de 2024",
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}]}


@pytest.mark.parametrize("field,value", [
    ("source_sha256", "0" * 64), ("source_quote", "18 de abril de 2024"),
    ("date_observed", "2024-04-18"), ("source_page", 2),
    ("filename", "../acta.pdf"), ("date_precision", "MONTH"),
])
def test_invalid_source_cannot_supply_dates(tmp_path, field, value):
    manifest = source(tmp_path)
    manifest["documents"][0][field] = value
    with pytest.raises(ValueError):
        verify_document_dates(manifest, tmp_path)


def test_duplicate_source_rejected(tmp_path):
    manifest = source(tmp_path)
    manifest["documents"].append(copy.deepcopy(manifest["documents"][0]))
    with pytest.raises(ValueError, match="duplicada"):
        verify_document_dates(manifest, tmp_path)


def test_verified_date_recovers_score_without_mutating_exposure_or_other_projects(tmp_path):
    manifest = source(tmp_path)
    dates = verify_document_dates(manifest, tmp_path)
    args = list(fixture())
    # Alpha has no dated neighbor inside its project. Beta must not supply one.
    for frame in (args[0], args[1]):
        frame.loc[0, "source_filename"] = "acta.pdf"
    args[4].loc[0, "filename"] = "acta.pdf"
    original_items = args[0].copy(deep=True)
    baseline, _ = recompute_projects(*args)
    enriched, _ = recompute_projects(*args, verified_dates=dates)
    assert baseline.iloc[0].pird_status != "CALCULADO"
    assert enriched.iloc[0].pird_status == "CALCULADO"
    assert enriched.iloc[0].persistence_level == 1
    assert enriched.iloc[0].document_date == pd.Timestamp("2024-04-17")
    assert enriched.iloc[0].severity == baseline.iloc[0].severity
    assert enriched.iloc[0].probability == baseline.iloc[0].probability
    assert enriched.iloc[1].pird == baseline.iloc[1].pird
    pd.testing.assert_frame_equal(args[0], original_items)


def test_published_manifest_matches_original_pdfs():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "config/document_dates_verified.json").read_text())
    assert len(verify_document_dates(manifest, root / "data/raw/corpus_actualizado")) == 3


def test_dates_complete_corpus_chronology_without_transferring_to_new_session():
    from src.frontend.document_timeline import build_document_timeline
    root = Path(__file__).resolve().parents[1]
    dates = verify_document_dates(json.loads((root / "config/document_dates_verified.json").read_text()),
                                  root / "data/raw/corpus_actualizado")
    chunks = pd.read_csv(root / "data/processed/chunks/chunks_recursive.csv")
    original = build_document_timeline(chunks)
    enriched = build_document_timeline(chunks, verified_dates=dates)
    assert original["documents_total"] == enriched["documents_total"] == 36
    assert original["documents_dated"] == 30
    assert enriched["documents_dated"] == 33
    session = pd.DataFrame([{"filename": "Solicitud cambio apoyo gerencia.pdf", "chunk_text": "Otro archivo"}])
    assert build_document_timeline(session)["documents_undated"] == 1
