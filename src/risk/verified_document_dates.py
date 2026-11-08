"""Fechas documentales revisadas: cotejo contra bytes y cita del PDF original."""

import hashlib
import re
from pathlib import Path

import pandas as pd

from src.risk.build_risk_timeline import MONTHS, infer_document_date


def _normalize(text: str) -> str:
    return " ".join(text.split()).casefold()


def _quote_dates(quote: str) -> set[str]:
    dates = set()
    for month, number in MONTHS.items():
        patterns = [rf"(\d{{1,2}}) de {month} de (20\d{{2}})",
                    rf"{month} (\d{{1,2}}) de (20\d{{2}})"]
        for pattern in patterns:
            for day, year in re.findall(pattern, _normalize(quote)):
                dates.add(pd.Timestamp(year=int(year), month=number, day=int(day)).strftime("%Y-%m-%d"))
    return dates


def verify_document_dates(manifest: dict, corpus_root: Path) -> dict:
    """Rechaza citas, fechas, páginas o archivos que no coincidan con la fuente.

    El manifiesto contiene fechas documentales revisadas, no fechas de sucesos
    extraídas automáticamente de cualquier mención dentro del documento.
    """
    import fitz

    if manifest.get("version") != "DOCUMENT-DATES-1":
        raise ValueError("Versión de fechas no reconocida")
    verified = {}
    root = corpus_root.resolve()
    for record in manifest["documents"]:
        filename = record["filename"]
        path = (root / filename).resolve()
        if path.parent != root or path.suffix.lower() != ".pdf" or filename in verified:
            raise ValueError("Fuente documental duplicada o fuera del corpus")
        if hashlib.sha256(path.read_bytes()).hexdigest() != record["source_sha256"]:
            raise ValueError(f"Hash documental distinto: {filename}")
        quote = record["source_quote"]
        day = record["date_observed"]
        if not quote.strip() or record["date_precision"] != "DAY" or _quote_dates(quote) != {day}:
            raise ValueError(f"Fecha no sustentada por la cita: {filename}")
        page = record["source_page"]
        with fitz.open(path) as document:
            if not isinstance(page, int) or isinstance(page, bool) or not 1 <= page <= len(document):
                raise ValueError(f"Página documental inválida: {filename}")
            if _normalize(quote) not in _normalize(document[page - 1].get_text()):
                raise ValueError(f"Cita ausente del PDF: {filename}")
        inferred = infer_document_date(filename)
        if pd.notna(inferred["document_date"]):
            raise ValueError(f"La fecha ya inferida requiere conciliación explícita: {filename}")
        verified[filename] = dict(record)
    return verified


def resolve_document_date(filename: str, verified_dates: dict | None = None) -> dict:
    inferred = infer_document_date(filename)
    record = (verified_dates or {}).get(filename)
    if record is None:
        return inferred
    day = record["date_observed"]
    if pd.notna(inferred["document_date"]) or record["date_precision"] != "DAY" or _quote_dates(record["source_quote"]) != {day}:
        raise ValueError("Fecha documental contradictoria o no sustentada")
    return {"document_date": pd.Timestamp(day), "date_precision": "DAY",
            "date_source": "DOCUMENT_BODY_VERIFIED", "date_warning": None}
