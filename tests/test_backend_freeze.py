import json

import pytest

from src.pipeline.backend_contract import (
    BACKEND_SCHEMA_VERSION,
    build_backend_snapshot,
    validate_backend_snapshot,
    write_backend_snapshot,
)
from src.pipeline.end_to_end import EndToEndPipeline, JsonlErrorLogger, OpenAIRagAnswerer


ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


def test_public_backend_snapshot_reconciles_and_is_private(tmp_path):
    snapshot = build_backend_snapshot(
        ROOT / "results/day_11/intelligent_risk_profile.json",
        ROOT / "results/day_11/category_profile.csv",
        ROOT / "results/day_11/pird_level_distribution.csv",
        ROOT / "results/day_11/weight_sensitivity.csv",
        ROOT / "results/day_13/smoke_test_summary.json",
    )
    output = tmp_path / "backend_snapshot.json"
    write_backend_snapshot(snapshot, output)
    stored = json.loads(output.read_text(encoding="utf-8"))
    assert stored["schema_version"] == BACKEND_SCHEMA_VERSION
    assert stored["contract_status"] == "FROZEN"
    assert stored["profile"]["signals_total"] == 649
    assert stored["profile"]["signals_scored"] == 372
    assert stored["profile"]["signals_pending"] == 277
    serialized = json.dumps(stored).lower()
    assert "chunk_text" not in serialized and "evidence_quote" not in serialized


def test_snapshot_rejects_broken_reconciliation():
    snapshot = {
        "schema_version": BACKEND_SCHEMA_VERSION,
        "profile": {"profile_status": "PROVISIONAL", "signals_total": 3,
                    "signals_scored": 2, "signals_pending": 0, "scoring_coverage": 0.6667},
        "categories": [{"total_signals": 3, "scored_signals": 2}],
        "level_distribution": [{"signal_count": 2}],
        "sensitivity": [],
        "runtime": {"private_payload_included": False},
    }
    with pytest.raises(ValueError, match="No concilia"):
        validate_backend_snapshot(snapshot)


def test_empty_model_response_has_explicit_status():
    class EmptyCompletions:
        def create(self, **kwargs):
            message = type("Message", (), {"content": ""})()
            choice = type("Choice", (), {"message": message})()
            usage = type("Usage", (), {})()
            return type("Response", (), {"choices": [choice], "usage": usage})()

    client = type("Client", (), {"chat": type("Chat", (), {"completions": EmptyCompletions()})()})()
    result = OpenAIRagAnswerer(client=client)("pregunta", [{
        "rank": 1, "filename": "demo.pdf", "page": 1, "chunk_id": "C1",
        "chunk_text": "texto", "doc_id": "D1", "score": 0.9,
    }])
    assert result["response_status"] == "EMPTY_MODEL_RESPONSE"
    assert result["evidence_available"] is False
    assert result["answer"]


def test_answer_failure_is_returned_and_logged_without_payload(tmp_path):
    def fail_answerer(question, chunks):
        raise TimeoutError("servicio no disponible")

    pipeline = EndToEndPipeline(
        retriever=lambda question, document_ids: [],
        extractor=lambda chunks: [],
        profiler=lambda signals: {},
        answerer=fail_answerer,
        error_logger=JsonlErrorLogger(tmp_path / "errors.jsonl"),
    )
    result = pipeline.run("pregunta privada", "REQ-ERROR", resume=False)
    assert result["execution"]["status"] == "ERROR"
    assert result["qa_result"]["response_status"] == "ERROR"
    log = (tmp_path / "errors.jsonl").read_text(encoding="utf-8")
    assert "rag_answer" in log
    assert "pregunta privada" not in log
