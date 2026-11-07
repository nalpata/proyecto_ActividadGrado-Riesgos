from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.pipeline.end_to_end import BgeM3Retriever, OpenAIRagAnswerer
from src.frontend.visualizations import filter_categories


def chunks():
    return [{"rank": i, "doc_id": f"D{i}", "filename": f"doc{i}.pdf", "page": 1,
             "chunk_id": f"C{i}", "score": .9, "chunk_text": "Evidencia"} for i in [1, 2]]


def client(answer):
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=lambda **kwargs: SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=answer))], usage=None))))


@pytest.mark.parametrize("answer", ["Una afirmación sin cita", "Respuesta [9]", "No tengo evidencia."])
def test_generated_answer_requires_existing_source_reference(answer):
    result = OpenAIRagAnswerer(client=client(answer))("pregunta", chunks())
    assert not result["evidence_available"]
    assert result["response_status"] == "NO_EVIDENCE"
    assert result["sources"] == []


def test_generated_answer_exposes_only_cited_sources():
    result = OpenAIRagAnswerer(client=client("Hecho documentado [2]."))("pregunta", chunks())
    assert result["evidence_available"]
    assert [row["rank"] for row in result["sources"]] == [2]


def test_project_filter_precedes_top_k(tmp_path):
    frame = pd.DataFrame([
        {"doc_id": "OTHER", "chunk_id": "X", "filename": "other.pdf", "page": 1,
         "chunk_text": "Otro proyecto", "embedding": [1., 0.]},
        {"doc_id": "ACTIVE", "chunk_id": "A", "filename": "active.pdf", "page": 1,
         "chunk_text": "Proyecto activo", "embedding": [.8, .2]},
    ])
    path = tmp_path / "vectors.parquet"
    frame.to_parquet(path)
    encoder = SimpleNamespace(encode=lambda *a, **kw: np.array([[1., 0.]]))
    scoped = BgeM3Retriever(path, top_k=1, encoder=encoder, allowed_chunk_ids={"A"})
    assert scoped("consulta", [])[0]["doc_id"] == "ACTIVE"
    empty = BgeM3Retriever(path, encoder=encoder, allowed_chunk_ids=set())
    assert empty("consulta", []) == []


def test_filters_handle_no_data_and_explicit_empty_selection():
    assert filter_categories([]).empty
    rows = [{"category": "Calidad", "category_score": 30, "category_level": "MEDIO",
             "scoring_coverage": 1, "scored_signals": 1, "total_signals": 1}]
    assert filter_categories(rows, selected_categories=[]).empty
    assert filter_categories(rows, selected_levels=[]).empty
    assert len(filter_categories(rows)) == 1
