"""Adaptador de diagnóstico independiente de instancias de chat ya cacheadas."""

from dataclasses import dataclass
from typing import Any
import uuid

from src.frontend.chat_service import normalize_question, public_sources


ERROR_TYPES = {
    "AuthenticationError", "PermissionDeniedError", "RateLimitError", "APIConnectionError",
    "APITimeoutError", "BadRequestError", "NotFoundError", "InternalServerError",
    "ModuleNotFoundError", "ImportError", "FileNotFoundError", "RuntimeError",
    "ValueError", "TypeError", "KeyError", "OSError", "MemoryError", "AttributeError",
    "UnexpectedError",
}
STAGES = {"retrieval", "rag_answer", "assistant_qa"}


def diagnostic_code(execution: dict) -> str | None:
    errors = execution.get("errors") or []
    if not errors:
        return None
    stage = errors[0].get("stage")
    kind = errors[0].get("error_type")
    return f"{stage if stage in STAGES else 'assistant_qa'}/{kind if kind in ERROR_TYPES else 'UnexpectedError'}"


@dataclass
class RuntimeChatService:
    pipeline: Any

    def ask(self, question: str, document_ids: list[str] | None = None) -> dict:
        normalized = normalize_question(question)
        result = self.pipeline.run_qa(normalized, f"CHAT-{uuid.uuid4().hex}", list(document_ids or []))
        qa = result.get("qa_result", {})
        execution = result.get("execution", {})
        sources = public_sources(qa.get("sources", []))
        return {
            "question": normalized,
            "answer": str(qa.get("answer") or "El modelo no produjo una respuesta."),
            "evidence_available": bool(qa.get("evidence_available")) and bool(sources),
            "response_status": qa.get("response_status") or execution.get("status", "ERROR"),
            "sources": sources,
            "diagnostic_code": diagnostic_code(execution),
            "retrieved_sources": public_sources(qa.get("retrieved_sources", [])),
            "model": qa.get("model"),
            "usage": qa.get("usage", {}),
        }


def append_runtime_history(history: list[dict], exchange: dict) -> list[dict]:
    code = exchange.get("diagnostic_code")
    allowed = {f"{stage}/{kind}" for stage in STAGES for kind in ERROR_TYPES}
    safe = {
        "question": exchange.get("question", ""), "answer": exchange.get("answer", ""),
        "response_status": exchange.get("response_status"),
        "evidence_available": bool(exchange.get("evidence_available")),
        "sources": public_sources(exchange.get("sources", [])),
        "retrieved_sources": public_sources(exchange.get("retrieved_sources", [])),
        "diagnostic_code": code if code in allowed else None,
    }
    return [*history, safe][-20:]
