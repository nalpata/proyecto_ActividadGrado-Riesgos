"""Construye timeline y persistencia sin inventar fechas ni componentes PIRD."""

from __future__ import annotations

import argparse
import calendar
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import normalize

from src.risk.semantic_clustering import semantic_recurrence


MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


def _valid_date(year: int, month: int, day: int) -> pd.Timestamp | None:
    if not 2020 <= year <= 2030:
        return None
    try:
        return pd.Timestamp(year=year, month=month, day=day)
    except ValueError:
        return None


def infer_document_date(filename: str) -> dict:
    """Extrae fecha del nombre sin interpretar números contractuales como fechas."""
    name = str(filename)
    for token in re.findall(r"(?<!\d)(\d{8})(?!\d)", name):
        if token.startswith("20"):
            date = _valid_date(int(token[:4]), int(token[4:6]), int(token[6:8]))
            if date is not None:
                return {"document_date": date, "date_precision": "DAY", "date_source": "FILENAME_YYYYMMDD", "date_warning": None}
        else:
            date = _valid_date(int(token[4:]), int(token[2:4]), int(token[:2]))
            if date is not None:
                return {"document_date": date, "date_precision": "DAY", "date_source": "FILENAME_DDMMYYYY", "date_warning": None}
    lower = name.lower()
    for month_name, month in MONTHS.items():
        match = re.search(rf"{month_name}\s+(\d{{1,2}})\s+(20\d{{2}})", lower)
        if match:
            date = _valid_date(int(match.group(2)), month, int(match.group(1)))
            if date is not None:
                return {"document_date": date, "date_precision": "DAY", "date_source": "FILENAME_MONTH_NAME", "date_warning": None}
    for token in re.findall(r"(?<!\d)(20\d{4})(?!\d)", name):
        year, month = int(token[:4]), int(token[4:6])
        if 1 <= month <= 12:
            return {"document_date": pd.Timestamp(year=year, month=month, day=1), "date_precision": "MONTH", "date_source": "FILENAME_YYYYMM", "date_warning": "Fecha normalizada al primer día del mes"}
    suspicious = re.findall(r"(?<!\d)(\d{8})(?!\d)", name)
    warning = f"Token de fecha fuera del rango permitido: {suspicious[0]}" if suspicious else "No se encontró fecha documental"
    return {"document_date": pd.NaT, "date_precision": None, "date_source": "UNAVAILABLE", "date_warning": warning}


def persistence_level(days: int, dated_document_count: int) -> int:
    if days < 0 or dated_document_count < 1:
        raise ValueError("Persistencia requiere días no negativos y al menos un documento")
    if dated_document_count == 1 or days == 0:
        return 1
    if days <= 30:
        return 2
    if days <= 90:
        return 3
    if days <= 180:
        return 4
    return 5


def build_timeline(items: pd.DataFrame, assignments: pd.DataFrame, embeddings: np.ndarray, threshold: float = 0.70) -> tuple[pd.DataFrame, dict]:
    required_items = {"item_id", "source_doc_id", "source_filename", "explicit_date", "calibrated_confidence", "calibrated_evidence_sufficient"}
    required_assignments = {"item_id", "recurrence_level"}
    if missing := required_items.difference(items.columns):
        raise ValueError(f"Faltan columnas en items: {sorted(missing)}")
    if missing := required_assignments.difference(assignments.columns):
        raise ValueError(f"Faltan columnas en assignments: {sorted(missing)}")
    timeline = items.merge(assignments[["item_id", "recurrence_level"]], on="item_id", how="left", validate="one_to_one")
    if timeline.recurrence_level.isna().any() or len(timeline) != len(embeddings):
        raise ValueError("Asignaciones o embeddings incompletos")

    # Recalcula la versión corregida aun si el ZIP del Día 9 contiene la primera salida.
    _, corrected_recurrence = semantic_recurrence(embeddings, timeline.source_doc_id, threshold=threshold)
    timeline["recurrence_level"] = corrected_recurrence

    dates = pd.DataFrame([infer_document_date(value) for value in timeline.source_filename])
    timeline = pd.concat([timeline.reset_index(drop=True), dates], axis=1)
    x = normalize(np.asarray(embeddings), norm="l2")
    similarities = x @ x.T
    docs = timeline.source_doc_id.astype(str).to_numpy()
    date_values = timeline.document_date.to_numpy()

    first_dates, last_dates, spans, dated_counts, levels, roles = [], [], [], [], [], []
    for row in range(len(timeline)):
        mask = (similarities[row] >= threshold) & ((docs != docs[row]) | (np.arange(len(timeline)) == row))
        neighbor_rows = np.where(mask & pd.notna(date_values))[0]
        if not len(neighbor_rows):
            first_dates.append(pd.NaT); last_dates.append(pd.NaT); spans.append(np.nan)
            dated_counts.append(0); levels.append(np.nan); roles.append("PENDIENTE_FECHA")
            continue
        relevant_dates = pd.to_datetime(date_values[neighbor_rows])
        first_date, last_date = relevant_dates.min(), relevant_dates.max()
        days = int((last_date - first_date).days)
        distinct_dated_docs = len(set(docs[neighbor_rows]))
        first_dates.append(first_date); last_dates.append(last_date); spans.append(days)
        dated_counts.append(distinct_dated_docs); levels.append(persistence_level(days, distinct_dated_docs))
        own_date = timeline.document_date.iloc[row]
        if pd.isna(own_date):
            roles.append("SIN_FECHA_PROPIA")
        elif own_date == first_date:
            roles.append("APARICION")
        else:
            roles.append("RECURRENCIA")

    timeline["semantic_family_first_date"] = first_dates
    timeline["semantic_family_last_date"] = last_dates
    timeline["persistence_days"] = spans
    timeline["dated_document_count"] = dated_counts
    timeline["persistence_level"] = levels
    timeline["temporal_role"] = roles
    timeline["escalation_status"] = "PENDIENTE_SEVERIDAD_TEMPORAL"
    timeline["pird_status"] = "PENDIENTE_SEVERIDAD_PROBABILIDAD"

    summary = {
        "signals": int(len(timeline)),
        "source_documents": int(timeline.source_doc_id.nunique()),
        "signals_with_document_date": int(timeline.document_date.notna().sum()),
        "signals_without_document_date": int(timeline.document_date.isna().sum()),
        "documents_with_date": int(timeline.loc[timeline.document_date.notna(), "source_doc_id"].nunique()),
        "documents_without_date": int(timeline.loc[timeline.document_date.isna(), "source_doc_id"].nunique()),
        "signals_with_persistence": int(timeline.persistence_level.notna().sum()),
        "persistence_level_counts": {str(int(k)): int(v) for k, v in timeline.persistence_level.value_counts().sort_index().items()},
        "temporal_role_counts": {str(k): int(v) for k, v in timeline.temporal_role.value_counts().items()},
        "pird_calculated": 0,
        "pird_pending": int(len(timeline)),
        "pird_missing_components": ["severity", "probability"],
        "interpretation": "Persistence is the observed time span of close semantic signals across dated documents. Escalation and PIRD remain pending because standardized temporal severity and probability are unavailable.",
    }
    return timeline, summary


def run(items_csv: Path, assignments_csv: Path, embeddings_npy: Path, output_dir: Path) -> dict:
    items = pd.read_csv(items_csv)
    assignments = pd.read_csv(assignments_csv)
    embeddings = np.load(embeddings_npy)
    timeline, summary = build_timeline(items, assignments, embeddings)
    output_dir.mkdir(parents=True, exist_ok=True)
    private_columns = [
        "item_id", "source_doc_id", "source_filename", "explicit_date", "document_date", "date_precision", "date_source", "date_warning",
        "recurrence_level", "semantic_family_first_date", "semantic_family_last_date", "persistence_days", "dated_document_count",
        "persistence_level", "temporal_role", "escalation_status", "pird_status",
    ]
    timeline[private_columns].to_csv(output_dir / "risk_timeline_private.csv", index=False, encoding="utf-8-sig")
    doc_dates = timeline.groupby(["source_doc_id", "source_filename"], as_index=False).agg(
        document_date=("document_date", "first"), date_precision=("date_precision", "first"),
        date_source=("date_source", "first"), date_warning=("date_warning", "first"), signal_count=("item_id", "size"),
    )
    doc_dates.to_csv(output_dir / "document_date_audit_private.csv", index=False, encoding="utf-8-sig")
    (output_dir / "timeline_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items-csv", required=True, type=Path)
    parser.add_argument("--assignments-csv", required=True, type=Path)
    parser.add_argument("--embeddings-npy", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.items_csv, args.assignments_csv, args.embeddings_npy, args.output_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
