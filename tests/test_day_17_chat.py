from src.frontend.chat_service import ConversationalRagService, append_history, normalize_question, public_sources


def test_question_is_normalized_and_limited():
    assert normalize_question("  ¿Qué   ocurrió?  ") == "¿Qué ocurrió?"
    try:
        normalize_question(" ")
        raise AssertionError("Debía rechazar la pregunta vacía")
    except ValueError:
        pass


def test_chat_uses_retrieval_and_returns_only_public_source_metadata():
    chunks = [{"rank": 1, "filename": "demo.pdf", "page": 3, "score": 0.91, "chunk_text": "privado", "chunk_id": "C1"}]
    service = ConversationalRagService(
        retriever=lambda question, document_ids: chunks,
        answerer=lambda question, evidence: {
            "answer": "Existe un retraso [1].", "evidence_available": True,
            "sources": evidence, "model": "test-model",
        },
    )
    result = service.ask("¿Qué retrasos existen?")
    assert result["evidence_available"] is True
    assert result["sources"] == [{"rank": 1, "filename": "demo.pdf", "page": 3, "score": 0.91}]
    assert "chunk_text" not in str(result["sources"])


def test_chat_returns_controlled_no_evidence_response():
    service = ConversationalRagService(
        retriever=lambda question, document_ids: [],
        answerer=lambda question, chunks: {
            "answer": "No se encontró evidencia documental suficiente para responder.",
            "evidence_available": False, "sources": [],
        },
    )
    result = service.ask("Pregunta sin soporte")
    assert result["response_status"] == "NO_EVIDENCE"
    assert result["sources"] == []


def test_chat_failure_does_not_expose_exception_message():
    def fail(question, document_ids):
        raise RuntimeError("contenido privado")

    result = ConversationalRagService(fail, lambda question, chunks: {} ).ask("¿Qué ocurrió?")
    assert result["response_status"] == "ERROR"
    assert "contenido privado" not in result["answer"]
    assert result["sources"] == []


def test_history_is_bounded_and_drops_private_fields():
    history = []
    for index in range(25):
        history = append_history(history, {
            "question": f"Q{index}", "answer": "A", "evidence_available": True,
            "response_status": "COMPLETED",
            "sources": [{"rank": 1, "filename": "a.pdf", "page": 1, "score": 0.8, "chunk_text": "privado"}],
        })
    assert len(history) == 20
    assert history[0]["question"] == "Q5"
    assert "chunk_text" not in str(history)


def test_public_sources_assigns_missing_rank_without_text():
    assert public_sources([{"filename": "a.pdf", "chunk_text": "x"}]) == [
        {"rank": 1, "filename": "a.pdf", "page": None, "score": None}
    ]
