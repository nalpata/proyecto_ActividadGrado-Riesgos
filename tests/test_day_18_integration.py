from pathlib import Path

from src.frontend.chat_service import FinalPipelineChatService
from src.pipeline.end_to_end import EndToEndPipeline


ROOT = Path(__file__).resolve().parents[1]


def build_pipeline(retriever, answerer):
    return EndToEndPipeline(
        retriever=retriever,
        extractor=lambda chunks: (_ for _ in ()).throw(AssertionError("Q&A no debe recalcular riesgos")),
        profiler=lambda signals: (_ for _ in ()).throw(AssertionError("Q&A no debe recalcular el PIRD")),
        answerer=answerer,
    )


def test_final_pipeline_qa_runs_retrieval_and_answer_without_recalculating_radar():
    chunks = [{
        "rank": 1, "filename": "demo.pdf", "page": 2, "score": 0.91,
        "doc_id": "D1", "chunk_id": "C1", "chunk_text": "Evidencia sintética",
    }]
    pipeline = build_pipeline(
        retriever=lambda question, document_ids: chunks,
        answerer=lambda question, evidence: {
            "answer": "Existe un retraso [1].",
            "evidence_available": True,
            "response_status": "COMPLETED",
            "sources": evidence,
        },
    )

    result = pipeline.run_qa("¿Qué retrasos existen?", "REQ-D18")

    assert result["execution"]["status"] == "COMPLETED"
    assert [item["stage"] for item in result["execution"]["trace"]] == ["retrieval", "rag_answer"]
    assert result["qa_result"]["answer"] == "Existe un retraso [1]."


def test_final_pipeline_chat_returns_public_sources_only():
    chunks = [{
        "rank": 1, "filename": "demo.pdf", "page": 2, "score": 0.91,
        "doc_id": "D1", "chunk_id": "C1", "chunk_text": "contenido privado",
    }]
    pipeline = build_pipeline(
        retriever=lambda question, document_ids: chunks,
        answerer=lambda question, evidence: {
            "answer": "Respuesta trazable [1].", "evidence_available": True,
            "response_status": "COMPLETED", "sources": evidence,
        },
    )

    result = FinalPipelineChatService(pipeline).ask("¿Qué ocurrió?")

    assert result["sources"] == [{"rank": 1, "filename": "demo.pdf", "page": 2, "score": 0.91}]
    assert "contenido privado" not in str(result)
    assert "chunk_id" not in str(result)


def test_final_pipeline_qa_controls_failures_without_exposing_details():
    def fail(question, document_ids):
        raise RuntimeError("detalle documental privado")

    pipeline = build_pipeline(fail, lambda question, evidence: {})
    result = FinalPipelineChatService(pipeline).ask("¿Qué ocurrió?")

    assert result["response_status"] == "ERROR"
    assert result["sources"] == []
    assert "detalle documental privado" not in result["answer"]


def test_day_18_interface_has_clickable_demonstration_questions_and_no_old_pending_copy():
    source = (ROOT / "app/streamlit_app.py").read_text(encoding="utf-8")

    assert "DEMONSTRATION_QUESTIONS" in source
    assert "demo-question-" in source
    assert "se conectarán al pipeline en el Día 18" not in source

