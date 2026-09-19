from src.agents.risk_graph import (
    FINAL_RETRIEVAL_CONFIGURATION,
    RiskGraphDependencies,
    run_risk_graph,
)


def candidate(item_id="ITEM_00001", watch=1, evidence=1, verified=1):
    return {
        "item_id": item_id,
        "source_doc_id": "DOC_01",
        "source_filename": "documento_prueba.pdf",
        "source_page": 1,
        "source_chunk_id": "CHUNK_01",
        "title": "Retraso documentado",
        "statement": "Existe un retraso pendiente.",
        "evidence_quote": "El entregable continúa pendiente después de la fecha acordada.",
        "evidence_verified": verified,
        "calibrated_type": "HECHO_OCURRIDO",
        "calibrated_watch": watch,
        "calibrated_evidence_sufficient": evidence,
        "calibrated_category": "Cronograma",
        "calibrated_confidence": 0.9,
        "calibrated_justification": "La evidencia confirma el retraso.",
    }


def dependencies(candidates=None, profile=None):
    return RiskGraphDependencies(
        retriever=lambda question, document_ids: [{"chunk_id": "CHUNK_01", "score": 0.91, "chunk_text": "evidencia"}],
        extractor=lambda chunks: candidates if candidates is not None else [candidate()],
        profiler=lambda signals: profile or {"profile_status": "PROVISIONAL", "signals_total": len(signals)},
    )


def test_complete_graph_executes_four_stages():
    state = run_risk_graph(dependencies(), "¿Qué retrasos requieren vigilancia?", request_id="REQ-1")
    assert state["status"] == "COMPLETED"
    assert [step["stage"] for step in state["execution_trace"]] == [
        "retrieval", "risk_extraction", "risk_validation", "risk_profile"
    ]
    assert len(state["validated_signals"]) == 1
    assert state["risk_profile"]["profile_status"] == "PROVISIONAL"


def test_no_evidence_stops_after_retrieval():
    deps = RiskGraphDependencies(retriever=lambda question, document_ids: [], extractor=lambda chunks: [])
    state = run_risk_graph(deps, "Pregunta sin evidencia")
    assert state["status"] == "NO_EVIDENCE"
    assert [step["stage"] for step in state["execution_trace"]] == ["retrieval"]


def test_deterministic_validator_rejects_insufficient_evidence():
    state = run_risk_graph(dependencies(candidates=[candidate(evidence=0)]), "Pregunta")
    assert state["status"] == "NO_VALIDATED_SIGNALS"
    assert state["validation_decisions"][0]["validation_reason"] == "EVIDENCIA_INSUFICIENTE"
    assert "risk_profile" not in state


def test_node_error_is_recorded_without_private_payload():
    def broken_extractor(chunks):
        raise RuntimeError("fallo controlado")

    deps = RiskGraphDependencies(
        retriever=lambda question, document_ids: [{"chunk_id": "C1", "chunk_text": "privado"}],
        extractor=broken_extractor,
    )
    state = run_risk_graph(deps, "Pregunta")
    assert state["status"] == "ERROR"
    assert state["errors"][0]["stage"] == "risk_extraction"
    assert "privado" not in str(state["errors"])


def test_frozen_retrieval_configuration_excludes_discarded_methods():
    assert FINAL_RETRIEVAL_CONFIGURATION["hyde"] is False
    assert FINAL_RETRIEVAL_CONFIGURATION["reranking"] is False
    assert FINAL_RETRIEVAL_CONFIGURATION["embedding_model"] == "BAAI/bge-m3"
