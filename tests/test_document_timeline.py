import pandas as pd
import pytest

from src.frontend.document_timeline import build_document_timeline


CATALOG = {"projects": [
    {"project_id": "A", "display_name": "Alpha", "aliases": ["Alpha"]},
    {"project_id": "B", "display_name": "Beta", "aliases": ["Beta"]},
]}


def test_counts_documents_once_and_preserves_invalid_dates_as_missing():
    chunks = pd.DataFrame([
        {"filename": "acta_20260105.pdf", "chunk_text": "Alpha"},
        {"filename": "acta_20260105.pdf", "chunk_text": "Alpha segunda página"},
        {"filename": "acta_20260120.docx", "chunk_text": "Beta"},
        {"filename": "acta_20140105.pdf", "chunk_text": "Alpha"},
        {"filename": "sin_fecha.pdf", "chunk_text": "Alpha"},
    ])
    timeline = build_document_timeline(chunks)
    assert timeline["documents_total"] == 4
    assert timeline["documents_dated"] == 2
    assert timeline["documents_undated"] == 2
    assert timeline["monthly_counts"] == [{"month": "2026-01", "documents": 2}]
    assert sum(r["document_date"] is None for r in timeline["documents"]) == 2


def test_project_mentions_allow_shared_documents_without_implying_exclusive_ownership():
    chunks = pd.DataFrame([
        {"filename": "acta_20260105.pdf", "chunk_text": "Alpha y Beta"},
        {"filename": "acta_20260205.pdf", "chunk_text": "Solo Beta"},
    ])
    timeline = build_document_timeline(chunks, "A", CATALOG)
    assert timeline["documents_total"] == 1
    assert timeline["scope"] == "DOCUMENT_MENTIONS_PROJECT"
    assert timeline["monthly_counts"] == [{"month": "2026-01", "documents": 1}]
    with pytest.raises(ValueError, match="reconocido"):
        build_document_timeline(chunks, "UNKNOWN", CATALOG)


def test_empty_scope_does_not_fall_back_to_consolidated_documents():
    timeline = build_document_timeline(pd.DataFrame([
        {"filename": "acta_20260105.pdf", "chunk_text": "Solo Beta"},
    ]), "A", CATALOG)
    assert timeline["documents_total"] == 0
    assert timeline["monthly_counts"] == []
    assert build_document_timeline(pd.DataFrame(columns=["filename", "chunk_text"]), "A", CATALOG)["documents_total"] == 0


def test_month_precision_does_not_display_an_invented_day():
    timeline = build_document_timeline(pd.DataFrame([
        {"filename": "acta_202601.pdf", "chunk_text": "Alpha"},
    ]))
    assert timeline["documents"][0]["document_date"] == "2026-01"
    assert timeline["documents"][0]["date_precision"] == "MONTH"
    assert timeline["monthly_counts"] == [{"month": "2026-01", "documents": 1}]
