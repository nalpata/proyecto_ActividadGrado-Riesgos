from types import SimpleNamespace

from src.frontend.runtime_chat import RuntimeChatService, append_runtime_history


def test_runtime_exposes_diagnostic_from_legacy_pipeline_and_keeps_it_in_history():
    pipeline = SimpleNamespace(run_qa=lambda *args: {
        "qa_result": {"answer": "Error controlado", "sources": [], "response_status": "ERROR"},
        "execution": {"status": "ERROR", "errors": [{
            "stage": "assistant_qa", "error_type": "AttributeError", "message": "private credential"}]},
    })
    result = RuntimeChatService(pipeline).ask("Consulta")
    assert result["diagnostic_code"] == "assistant_qa/AttributeError"
    history = append_runtime_history([], result)
    assert history[0]["diagnostic_code"] == result["diagnostic_code"]
    assert "private credential" not in str(history)


def test_runtime_filters_unknown_diagnostics_and_private_source_payloads():
    result = append_runtime_history([], {"diagnostic_code": "private", "sources": [
        {"rank": 1, "filename": "a.pdf", "chunk_text": "private text"}]})[0]
    assert result["diagnostic_code"] is None
    assert "private text" not in str(result)
