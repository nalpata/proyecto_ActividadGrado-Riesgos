"""Alcance por fecha documental explícita, antes del top-k semántico.

No reescribe la consulta ni cambia embeddings o ranking. Una fecha de entrega
o compromiso no identifica por sí sola la fecha de un acta.
"""
from __future__ import annotations

from datetime import date
import re
from typing import Any, Callable


DATE_TOKEN = r"(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/\-]\d{1,2}[/\-]\d{4})"
DOCUMENT_REFERENCE = re.compile(
    rf"\b(?:actas?|documentos?|informes?)\s+(?:del?|con\s+fecha|de\s+fecha)\s+"
    rf"({DATE_TOKEN})(?:\s+(?:y|e)\s+({DATE_TOKEN}))?", re.IGNORECASE)


def _date_token(value: str) -> str | None:
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return date.fromisoformat(value).isoformat()
        day, month, year = map(int, re.split(r"[/\-]", value))
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def requested_document_dates(question: str) -> set[str] | None:
    """None: sin referencia; conjunto vacío: referencia con fecha inválida."""
    matches = list(DOCUMENT_REFERENCE.finditer(str(question)))
    if not matches:
        return None
    values = [value for match in matches for value in match.groups() if value]
    dates = [_date_token(value) for value in values]
    return {value for value in dates if value} if all(dates) else set()


def filename_document_date(filename: str) -> str | None:
    """Solo una fecha no ambigua codificada en el nombre; no infiere del contenido."""
    dates = set()
    for token in re.findall(r"(?<!\d)(\d{8})(?!\d)", str(filename)):
        try:
            dates.add(date(int(token[:4]), int(token[4:6]), int(token[6:])).isoformat())
        except ValueError:
            continue
    return next(iter(dates)) if len(dates) == 1 else None


class DocumentReferenceScopedRetriever:
    def __init__(self, retriever: Callable, documents: list[dict[str, Any]]):
        self.retriever = retriever
        self.documents = documents

    def __call__(self, question: str, document_ids: list[str]) -> list[dict[str, Any]]:
        dates = requested_document_dates(question)
        if dates is None:
            return self.retriever(question, document_ids)
        allowed = {str(document["doc_id"]) for document in self.documents
                   if document.get("doc_id") and
                   filename_document_date(document.get("filename", "")) in dates}
        if document_ids:
            allowed.intersection_update(map(str, document_ids))
        if not allowed:
            return []  # Never turn an empty requested scope into an unrestricted search.
        return self.retriever(question, sorted(allowed))
