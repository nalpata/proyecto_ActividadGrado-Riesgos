from copy import deepcopy

import numpy as np
import pytest

from src.frontend.chat_service import ConversationalRagService
from src.retrieval.session_retriever import SessionRetriever


class Encoder:
    def encode(self, texts, **kwargs):
        return np.array([[1.0, 0.0] for _ in texts])


def ingestion(project="P"):
    return {"project_id": project, "chunks": [
        {"project_id": project, "doc_id": "D1", "chunk_id": "C1", "filename": "acta.docx",
         "page": 1, "chunk_text": "Compromiso pendiente", "embedding": np.array([1., 0.])},
        {"project_id": project, "doc_id": "D2", "chunk_id": "C2", "filename": "informe.docx",
         "page": 1, "chunk_text": "Actividad finalizada", "embedding": np.array([0., 1.])},
    ]}


def test_session_ranks_only_memory_documents_and_respects_document_filter():
    retriever = SessionRetriever(ingestion(), Encoder(), top_k=1)
    assert retriever("pendientes", [])[0]["chunk_id"] == "C1"
    assert retriever("pendientes", ["D2"])[0]["chunk_id"] == "C2"
    assert retriever("pendientes", ["HISTORICAL-DOC"]) == []
    assert retriever("", []) == []


def test_session_rejects_cross_project_chunks():
    data = ingestion()
    data["chunks"][1]["project_id"] = "OTHER"
    with pytest.raises(ValueError, match="otro proyecto"):
        SessionRetriever(data, Encoder())


def test_sessions_do_not_share_index_or_fall_back_to_historical_files():
    first = SessionRetriever(ingestion("A"), Encoder())
    second_data = ingestion("B")
    second_data["chunks"] = [second_data["chunks"][1]]
    second = SessionRetriever(second_data, Encoder())
    assert {r["chunk_id"] for r in first("consulta", [])} == {"C1", "C2"}
    assert {r["chunk_id"] for r in second("consulta", [])} == {"C2"}


def test_session_chat_passes_local_evidence_and_returns_sources():
    def answer(question, chunks):
        assert len(chunks) == 1
        assert chunks[0]["chunk_text"] == "Compromiso pendiente"
        return {"answer": "El compromiso sigue pendiente [1].", "evidence_available": True,
                "sources": chunks}
    service = ConversationalRagService(SessionRetriever(ingestion(), Encoder(), top_k=1), answer)
    result = service.ask("¿Qué está pendiente?")
    assert result["evidence_available"]
    assert result["sources"][0]["filename"] == "acta.docx"
    assert "chunk_text" not in result["sources"][0]


@pytest.mark.parametrize("vector", [[0., 0.], [float("nan"), 1.]])
def test_session_rejects_invalid_vectors(vector):
    data = deepcopy(ingestion())
    data["chunks"][0]["embedding"] = vector
    with pytest.raises(ValueError, match="inválidos"):
        SessionRetriever(data, Encoder())
