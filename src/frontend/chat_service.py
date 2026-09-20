"""Adaptador seguro del asistente documental del Día 17."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

MAX_QUESTION_LENGTH = 1000
MAX_HISTORY_ITEMS = 20
PUBLIC_SOURCE_FIELDS = ("rank", "filename", "page", "score")


def normalize_question(question: str) -> str:
    """Valida una pregunta antes de enviarla al pipeline."""

    normalized = " ".join(str(question).split())
    if not normalized:
        raise ValueError("Escriba una pregunta antes de consultar.")
    if len(normalized) > MAX_QUESTION_LENGTH:
        raise ValueError(f"La pregunta no puede superar {MAX_QUESTION_LENGTH} caracteres.")
    return normalized


def public_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Reduce las fuentes a metadatos mostrables; excluye chunks y texto."""

    cleaned: list[dict[str, Any]] = []
    for source in sources:
        item = {field: source.get(field) for field in PUBLIC_SOURCE_FIELDS}
        if item["rank"] is None:
            item["rank"] = len(cleaned) + 1
        cleaned.append(item)
    return cleaned


@dataclass
class ConversationalRagService:
    """Ejecuta Q&A sobre retrieval directo y devuelve un contrato apto para UI."""

    retriever: Callable[[str, list[str]], list[dict[str, Any]]]
    answerer: Callable[[str, list[dict[str, Any]]], dict[str, Any]]

    def ask(self, question: str, document_ids: list[str] | None = None) -> dict[str, Any]:
        normalized = normalize_question(question)
        try:
            chunks = self.retriever(normalized, list(document_ids or []))
            result = self.answerer(normalized, chunks)
        except Exception as exc:
            return {
                "question": normalized,
                "answer": "No fue posible completar la consulta. Intente nuevamente.",
                "evidence_available": False,
                "response_status": "ERROR",
                "sources": [],
                "error_type": type(exc).__name__,
            }

        sources = public_sources(result.get("sources", []))
        evidence_available = bool(result.get("evidence_available")) and bool(sources)
        answer = str(result.get("answer") or "El modelo no produjo una respuesta.").strip()
        return {
            "question": normalized,
            "answer": answer,
            "evidence_available": evidence_available,
            "response_status": result.get("response_status", "COMPLETED" if evidence_available else "NO_EVIDENCE"),
            "sources": sources,
            "model": result.get("model"),
            "usage": result.get("usage", {}),
        }


def append_history(history: list[dict[str, Any]], exchange: dict[str, Any]) -> list[dict[str, Any]]:
    """Conserva una ventana acotada sin almacenar los chunks recuperados."""

    safe_exchange = {
        "question": exchange.get("question", ""),
        "answer": exchange.get("answer", ""),
        "evidence_available": bool(exchange.get("evidence_available")),
        "response_status": exchange.get("response_status"),
        "sources": public_sources(exchange.get("sources", [])),
    }
    return [*history, safe_exchange][-MAX_HISTORY_ITEMS:]
