"""Catálogo aprobado y conciliación reproducible del índice documental."""

import hashlib
import json
from pathlib import Path

import pandas as pd

from src.risk.project_resolution import assign_chunks, validate_project_catalog


def load_catalog(path: Path, override: str | dict | None = None) -> dict:
    payload = (json.loads(override) if isinstance(override, str) else override) if override else json.loads(path.read_text(encoding="utf-8"))
    return validate_project_catalog(payload)


def reconcile_chunks(chunks: pd.DataFrame, catalog: dict) -> tuple[pd.DataFrame, dict]:
    validate_project_catalog(catalog)
    if chunks.chunk_id.duplicated().any():
        raise ValueError("La conciliación requiere identificadores de fragmento únicos")
    assignments = assign_chunks(chunks, catalog)
    assigned = assignments.project_assignment_status.isin({"ASSIGNED_CHUNK_EXPLICIT", "ASSIGNED_FILENAME_EXPLICIT"})
    counts = assignments.loc[assigned].groupby("project_ids").size().to_dict()
    summary = {
        "catalog_sha256": hashlib.sha256(json.dumps(catalog, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
        "chunks_total": len(chunks), "documents_total": int(chunks.filename.nunique()),
        "chunks_single_project": int(assigned.sum()),
        "chunks_ambiguous": int((assignments.project_assignment_status == "AMBIGUOUS_CONTEXT").sum()),
        "chunks_pending": int((~assigned & (assignments.project_assignment_status != "AMBIGUOUS_CONTEXT")).sum()),
        "projects": [{"project_id": p["project_id"], "display_name": p["display_name"],
                      "chunks_single_project": int(counts.get(p["project_id"], 0))} for p in catalog["projects"]],
        "status": "AUTOMATIC_ASSIGNMENT_PENDING_HUMAN_REVIEW",
        "unit": "chunks_not_risk_signals",
    }
    return assignments, summary
