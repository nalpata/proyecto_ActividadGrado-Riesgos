import json

import numpy as np
import pandas as pd

from src.pipeline.end_to_end import (
    BgeM3Retriever,
    CalibratedCatalogExtractor,
    EndToEndPipeline,
    JsonCheckpointStore,
    OpenAIRagAnswerer,
    PublishedProfileLoader,
    public_execution_summary,
)


class FakeEncoder:
    def encode(self, texts, **kwargs):
        return np.asarray([[1.0, 0.0] for _ in texts], dtype=np.float32)


def calibrated_candidate():
    return {
        "item_id": "I1", "source_doc_id": "D1", "source_filename": "demo.pdf",
        "source_page": 1, "source_chunk_id": "C1", "title": "Demora",
        "statement": "La entrega está demorada.", "evidence_quote": "La entrega continúa pendiente.",
        "evidence_verified": 1, "calibrated_type": "HECHO_OCURRIDO",
        "calibrated_watch": 1, "calibrated_evidence_sufficient": 1,
        "calibrated_category": "Cronograma", "calibrated_confidence": 0.9,
        "calibrated_justification": "Demora explícita.",
    }


def test_bge_retriever_uses_existing_embeddings_and_document_filter(tmp_path):
    frame = pd.DataFrame({
        "doc_id": ["D1", "D2"], "filename": ["a.pdf", "b.pdf"], "page": [1, 2],
        "chunk_id": ["C1", "C2"], "chunk_text": ["uno", "dos"],
        "embedding": [np.asarray([1.0, 0.0]), np.asarray([0.0, 1.0])],
    })
    path = tmp_path / "embeddings.parquet"
    frame.to_parquet(path)
    retriever = BgeM3Retriever(path, top_k=2, encoder=FakeEncoder())
    result = retriever("pregunta", ["D2"])
    assert [item["doc_id"] for item in result] == ["D2"]
    assert result[0]["chunk_id"] == "C2"


def test_end_to_end_output_and_checkpoint_resume(tmp_path):
    calls = {"answerer": 0}

    def retriever(question, document_ids):
        return [{"rank": 1, "score": 0.9, "doc_id": "D1", "filename": "demo.pdf", "page": 1,
                 "chunk_id": "C1", "chunk_text": "Evidencia sintética"}]

    def answerer(question, chunks):
        calls["answerer"] += 1
        return {"answer": "Respuesta [1]", "evidence_available": True, "sources": [{"chunk_id": "C1"}]}

    pipeline = EndToEndPipeline(
        retriever= retriever,
        extractor=lambda chunks: [calibrated_candidate()],
        profiler=lambda signals: {"profile_status": "PROVISIONAL", "global_pird": 52.16,
                                  "scoring_coverage": 0.5732},
        answerer=answerer,
        checkpoint_store=JsonCheckpointStore(tmp_path / "checkpoints"),
    )
    first = pipeline.run("¿Qué ocurrió?", "REQ-13")
    resumed = pipeline.run("¿Qué ocurrió?", "REQ-13")
    assert first["execution"]["status"] == "COMPLETED"
    assert first["qa_result"]["evidence_available"] is True
    assert first["risk_result"]["validated_signals_count"] == 1
    assert resumed["execution"]["resumed_from_checkpoint"] is True
    assert calls["answerer"] == 1


def test_private_catalog_and_published_profile_adapters(tmp_path):
    catalog_path = tmp_path / "calibrated.csv"
    pd.DataFrame([calibrated_candidate()]).to_csv(catalog_path, index=False)
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps({"profile_status": "PROVISIONAL", "global_pird": 52.16}))
    categories_path = tmp_path / "categories.csv"
    pd.DataFrame({"category": ["Cronograma"], "score": [55.33]}).to_csv(categories_path, index=False)

    candidates = CalibratedCatalogExtractor(catalog_path)([{"chunk_id": "C1"}])
    profile = PublishedProfileLoader(profile_path, categories_path)(candidates)
    assert len(candidates) == 1
    assert profile["global_pird"] == 52.16
    assert profile["validated_signals_in_request"] == 1
    assert profile["profile_source"] == "frozen_day_11_aggregate"


def test_rag_answerer_handles_no_evidence_without_api_key():
    result = OpenAIRagAnswerer()("Pregunta sin soporte", [])
    assert result["evidence_available"] is False
    assert result["sources"] == []
    assert "No se encontró evidencia" in result["answer"]


def test_public_summary_excludes_answer_sources_and_private_signals(tmp_path):
    result = {
        "request_id": "REQ", "qa_result": {"answer": "privada", "evidence_available": True,
        "sources": [{"chunk_text": "privado"}]},
        "risk_result": {"validated_signals_count": 2, "profile": {"profile_status": "PROVISIONAL"}},
        "execution": {"status": "COMPLETED", "trace": [{"stage": "retrieval"}], "elapsed_seconds": 1.2},
    }
    summary = public_execution_summary(result)
    serialized = json.dumps(summary)
    assert "privada" not in serialized and "privado" not in serialized
    assert summary["source_count"] == 1
    assert summary["private_payload_included"] is False
