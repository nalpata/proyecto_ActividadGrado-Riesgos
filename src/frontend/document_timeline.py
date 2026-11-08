"""Cronología documental con fechas trazables y sin imputaciones."""

import pandas as pd

from src.risk.build_risk_timeline import infer_document_date
from src.risk.project_resolution import find_project_mentions, validate_project_catalog


def build_document_timeline(chunks: pd.DataFrame, project_id: str | None = None,
                            catalog: dict | None = None) -> dict:
    if not {"filename", "chunk_text"}.issubset(chunks.columns):
        raise ValueError("La cronología requiere nombre de documento y texto de los fragmentos")
    selected = chunks.copy()
    if project_id is not None:
        if catalog is None:
            raise ValueError("La cronología por proyecto requiere un catálogo")
        validate_project_catalog(catalog)
        if project_id not in {p["project_id"] for p in catalog["projects"]}:
            raise ValueError("Proyecto no reconocido en la cronología")
        mask = selected.apply(lambda row: project_id in {
            mention["project_id"] for mention in find_project_mentions(
                str(row["chunk_text"]) + " " + str(row["filename"]), catalog)}, axis=1) if not selected.empty else pd.Series(False, index=selected.index)
        selected = selected[mask]
    records = []
    for filename in selected.filename.drop_duplicates().astype(str):
        date = infer_document_date(filename)
        records.append({
            "filename": filename,
            "document_date": date["document_date"].strftime("%Y-%m" if date["date_precision"] == "MONTH" else "%Y-%m-%d") if pd.notna(date["document_date"]) else None,
            "date_source": date["date_source"], "date_precision": date["date_precision"],
            "date_warning": date["date_warning"],
        })
    records.sort(key=lambda r: (r["document_date"] is None, r["document_date"] or "", r["filename"]))
    dated = [r for r in records if r["document_date"] is not None]
    counts = pd.Series([r["document_date"][:7] for r in dated], dtype="object").value_counts().sort_index()
    return {
        "documents_total": len(records), "documents_dated": len(dated),
        "documents_undated": len(records) - len(dated),
        "monthly_counts": [{"month": month, "documents": int(count)} for month, count in counts.items()],
        "documents": records,
        "scope": "DOCUMENT_MENTIONS_PROJECT" if project_id is not None else "PROVIDED_DOCUMENTS",
    }
