import numpy as np
import pandas as pd
import pytest

from src.pipeline.project_risk_processing import process_project_risks
from src.retrieval.session_retriever import SessionRetriever
from src.risk.project_scope import annotate_chunks, scope_signals, validate_scope, canonical_project_id


CATALOG = {
    "projects": [
        {"project_id": "ALPHA", "display_name": "Alpha", "aliases": ["Alpha"]},
        {"project_id": "BETA", "display_name": "Beta", "aliases": ["Beta"]},
    ],
    "unassigned_project_id": "PENDING", "multi_project_id": "MULTI",
}


class Encoder:
    def encode(self, texts, **kwargs):
        return np.tile(np.array([[1., 0.]], dtype=np.float32), (len(texts), 1))


def chunks():
    return [
        {"project_id": "ALPHA", "doc_id": "D1", "chunk_id": "C1", "filename": "acta_20260101.pdf",
         "page": 1, "chunk_text": "Alpha mantiene un retraso confirmado.", "embedding": [1., 0.]},
        {"project_id": "ALPHA", "doc_id": "D2", "chunk_id": "C2", "filename": "acta_20260215.pdf",
         "page": 1, "chunk_text": "Beta mantiene un retraso confirmado.", "embedding": [1., 0.]},
    ]


def items():
    rows = []
    for i, chunk in enumerate(chunks(), 1):
        rows.append({
            "item_id": f"I{i}", "source_doc_id": chunk["doc_id"], "source_chunk_id": chunk["chunk_id"],
            "source_filename": chunk["filename"], "source_page": 1,
            "title": "Título generado Beta", "statement": "Atraso", "evidence_quote": chunk["chunk_text"],
            "evidence_verified": 1, "calibrated_watch": 1, "calibrated_evidence_sufficient": 1,
            "calibrated_type": "HALLAZGO", "calibrated_category": "Cronograma", "calibrated_confidence": .9,
            "calibrated_justification": "Texto generado Beta", "explicit_date": "", "exposure_status": "ABIERTA",
        })
    return pd.DataFrame(rows)


def test_project_assignment_uses_source_not_generated_title():
    tagged, summary = scope_signals(items(), pd.DataFrame(chunks()), "ALPHA", CATALOG)
    assert tagged.detected_project_id.tolist() == ["ALPHA", "BETA"]
    assert tagged.project_scope_included.tolist() == [True, False]
    assert summary["signals_excluded_or_pending"] == 1


def test_unknown_quote_cannot_assign_project_even_with_generated_title():
    frame = items().iloc[:1].copy()
    frame["evidence_quote"] = "Alpha dice algo inexistente en el documento"
    tagged, _ = scope_signals(frame, pd.DataFrame(chunks()), "ALPHA", CATALOG)
    assert not tagged.iloc[0].project_scope_included
    assert tagged.iloc[0].project_assignment_status == "PENDING_UNVERIFIED_EVIDENCE"


def test_ambiguous_chunks_and_other_projects_do_not_enter_session_retrieval():
    data = chunks()
    data.append({**data[0], "chunk_id": "C3", "chunk_text": "Alpha y Beta tienen compromisos pendientes."})
    summary = annotate_chunks(data, "ALPHA", CATALOG)
    assert summary["chunks_active_project"] == 1
    retriever = SessionRetriever({"project_id": "ALPHA", "chunks": data, "project_scope": summary}, Encoder())
    assert [r["chunk_id"] for r in retriever("pendientes", [])] == ["C1"]
    only_other = [data[1]]
    summary = annotate_chunks(only_other, "ALPHA", CATALOG)
    assert SessionRetriever({"project_id": "ALPHA", "chunks": only_other, "project_scope": summary}, Encoder())("consulta", []) == []


def test_missing_catalog_is_explicitly_unverified():
    tagged, summary = scope_signals(items(), pd.DataFrame(chunks()), "ALPHA", None)
    assert summary["mode"] == "USER_DECLARED_UNVERIFIED"
    assert tagged.detected_project_id.isna().all()


def test_pipeline_filters_before_recurrence_persistence_and_pird(monkeypatch):
    import src.pipeline.project_risk_processing as processing

    monkeypatch.setattr(processing, "_extract_items", lambda *a: (items(), {
        "chunks_analyzed": 2, "items_with_verified_evidence": 2, "prompt_tokens": 0, "completion_tokens": 0}))
    monkeypatch.setattr(processing, "_classify_items", lambda frame, *a: (frame, {
        "calibration_status": "PROVISIONAL_NO_PRIVATE_EXAMPLES", "prompt_tokens": 0, "completion_tokens": 0}))
    def assess(frame, client, progress=None):
        assert frame.item_id.tolist() == ["I1"]
        return pd.DataFrame([{"item_id": "I1", "severity": 3, "probability": 4}]), {
            "prompt_tokens": 0, "completion_tokens": 0}
    monkeypatch.setattr(processing, "_assess_exposure", assess)
    result = process_project_risks({"project_id": "ALPHA", "chunks": chunks(), "project_catalog": CATALOG}, None, Encoder())
    assert result["summary"]["signals_validated"] == 1
    assert result["project_scope"]["signals_excluded_or_pending"] == 1
    signal = result["private"]["scored_signals"][0]
    assert signal["detected_project_id"] == "ALPHA"
    assert signal["recurrence_level"] == 1
    assert signal["persistence_level"] == 1
    assert result["summary"]["signals_scored"] == 1


def test_unknown_active_project_is_rejected_before_model_calls():
    with pytest.raises(ValueError, match="catálogo"):
        validate_scope("OTHER", CATALOG)


def test_display_name_resolves_to_canonical_id_without_claiming_document_membership():
    assert canonical_project_id("Alpha", CATALOG) == "ALPHA"
    with pytest.raises(ValueError):
        canonical_project_id("Proyecto desconocido", CATALOG)


def test_no_active_project_signals_leave_profile_pending_without_exposure_calls(monkeypatch):
    import src.pipeline.project_risk_processing as processing
    monkeypatch.setattr(processing, "_extract_items", lambda *a: (items().iloc[1:].copy(), {
        "chunks_analyzed": 1, "items_with_verified_evidence": 1, "prompt_tokens": 0, "completion_tokens": 0}))
    monkeypatch.setattr(processing, "_classify_items", lambda frame, *a: (frame, {
        "calibration_status": "PROVISIONAL_NO_PRIVATE_EXAMPLES", "prompt_tokens": 0, "completion_tokens": 0}))
    def forbidden(*args):
        raise AssertionError("No debe valorar exposición de otro proyecto")
    monkeypatch.setattr(processing, "_assess_exposure", forbidden)
    result = process_project_risks({"project_id": "ALPHA", "chunks": chunks()[1:], "project_catalog": CATALOG}, None, Encoder())
    assert result["summary"]["global_pird"] is None
    assert result["summary"]["signals_validated"] == 0
    assert result["project_scope"]["signals_excluded_or_pending"] == 1

