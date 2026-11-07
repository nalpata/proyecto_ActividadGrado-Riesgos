from src.frontend.chat_service import FinalPipelineChatService, append_history, public_diagnostic
from src.pipeline.end_to_end import EndToEndPipeline


def test_diagnostic_distinguishes_retrieval_from_generation_without_leaking_message():
    def fail(*args):
        raise RuntimeError("private detail with secret")

    for retriever, answerer, expected in [
        (fail, lambda *a: {}, "retrieval/RuntimeError"),
        (lambda *a: [{"chunk_text": "private evidence"}], fail, "rag_answer/RuntimeError"),
    ]:
        pipeline = EndToEndPipeline(retriever, lambda *a: [], lambda *a: {}, answerer)
        result = FinalPipelineChatService(pipeline).ask("consulta")
        assert result["diagnostic_code"] == expected
        assert "private detail" not in str(result)
        assert "secret" not in str(result)
        assert append_history([], result)[0]["diagnostic_code"] == expected


def test_diagnostic_rejects_unknown_types_stages_and_history_payloads():
    assert public_diagnostic({"errors": [{"stage": "private document", "error_type": "secret", "message": "key"}]}) == "assistant_qa/UnexpectedError"
    assert public_diagnostic({}) is None
    assert append_history([], {"diagnostic_code": "secret"})[0]["diagnostic_code"] is None
