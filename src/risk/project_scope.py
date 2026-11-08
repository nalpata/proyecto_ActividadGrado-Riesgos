"""Identidad documental del proyecto, separada del contenedor de la sesión."""

from typing import Any

import pandas as pd

from src.risk.extract_documentary_items import evidence_is_verbatim
from src.risk.project_resolution import (
    ASSIGNED_STATUSES, assign_chunks, resolve_project, validate_project_catalog, normalize_text,
    find_project_mentions,
)


def subdivision_assignment(project_id: str | None, catalog: dict, evidence: str, context: str = "") -> dict:
    project = next((p for p in catalog["projects"] if p["project_id"] == project_id), {})
    subdivisions = project.get("subdivisions", [])
    if not subdivisions:
        return {"detected_subdivision_id": None, "subdivision_status": "NOT_APPLICABLE"}
    subcatalog = {"projects": subdivisions}
    validate_project_catalog(subcatalog)
    ids = {m["project_id"] for m in find_project_mentions(evidence, subcatalog)}
    if not ids:
        ids = {m["project_id"] for m in find_project_mentions(context, subcatalog)}
    return {"detected_subdivision_id": next(iter(ids)) if len(ids) == 1 else None,
            "subdivision_status": "ASSIGNED_EXPLICIT" if len(ids) == 1 else "AMBIGUOUS" if ids else "PENDING_NO_EVIDENCE"}


def validate_scope(project_id: str, catalog: dict) -> dict:
    validate_project_catalog(catalog)
    required = {"unassigned_project_id", "multi_project_id"}
    if not required.issubset(catalog):
        raise ValueError("El catálogo requiere identificadores para pendientes y multiproyecto")
    ids = {str(p["project_id"]) for p in catalog["projects"]}
    if project_id not in ids:
        raise ValueError("El proyecto activo no existe en el catálogo documental")
    if catalog["unassigned_project_id"] in ids or catalog["multi_project_id"] in ids:
        raise ValueError("Los identificadores reservados no pueden ser proyectos")
    if catalog["unassigned_project_id"] == catalog["multi_project_id"]:
        raise ValueError("Pendientes y multiproyecto requieren identificadores distintos")
    return catalog


def canonical_project_id(value: str, catalog: dict) -> str:
    validate_project_catalog(catalog)
    requested = normalize_text(value)
    matches = {str(p["project_id"]) for p in catalog["projects"]
               if requested in {normalize_text(x) for x in
                   [p["project_id"], p["display_name"], *p["aliases"]]}}
    if len(matches) != 1:
        raise ValueError("El proyecto seleccionado no se identifica de forma única en el catálogo")
    project_id = matches.pop()
    validate_scope(project_id, catalog)
    return project_id


def annotate_chunks(chunks: list[dict], project_id: str, catalog: dict | None) -> dict:
    """Añade identidad detectada sin modificar texto, vectores ni chunk_id."""
    if catalog is None:
        for chunk in chunks:
            chunk.update(detected_project_id=None, project_assignment_status="USER_DECLARED_UNVERIFIED")
        return {"mode": "USER_DECLARED_UNVERIFIED", "chunks_total": len(chunks),
                "chunks_active_project": None, "chunks_excluded_or_pending": None}
    validate_scope(project_id, catalog)
    tagged = assign_chunks(pd.DataFrame(chunks), catalog)
    active = 0
    for chunk, assignment in zip(chunks, tagged.to_dict("records"), strict=True):
        ids = [value for value in assignment["project_ids"].split("|") if value]
        assigned = assignment["project_assignment_status"] in {
            "ASSIGNED_CHUNK_EXPLICIT", "ASSIGNED_FILENAME_EXPLICIT",
        } and len(ids) == 1
        chunk["detected_project_id"] = ids[0] if assigned else None
        chunk["project_assignment_status"] = assignment["project_assignment_status"]
        chunk["detected_project_ids"] = ids
        chunk.update(subdivision_assignment(chunk["detected_project_id"], catalog, chunk["chunk_text"]))
        active += int(assigned and ids[0] == project_id)
    return {"mode": "DOCUMENT_EVIDENCE", "chunks_total": len(chunks),
            "chunks_active_project": active, "chunks_excluded_or_pending": len(chunks) - active}


def scope_signals(items: pd.DataFrame, chunks: pd.DataFrame, project_id: str,
                  catalog: dict | None) -> tuple[pd.DataFrame, dict]:
    """Resuelve cada señal con cita verificada; nunca usa títulos generados para asignar."""
    result = items.copy()
    if catalog is None:
        result["detected_project_id"] = None
        result["project_assignment_status"] = "USER_DECLARED_UNVERIFIED"
        result["project_scope_included"] = True
        return result, {"mode": "USER_DECLARED_UNVERIFIED", "signals_total": len(result),
                        "signals_active_project": len(result), "signals_excluded_or_pending": 0}
    validate_scope(project_id, catalog)
    lookup = chunks.set_index("chunk_id")
    if not lookup.index.is_unique:
        raise ValueError("Los identificadores de fragmento deben ser únicos")
    assignments = []
    for row in result.itertuples(index=False):
        source = lookup.loc[row.source_chunk_id] if row.source_chunk_id in lookup.index else None
        quote = str(getattr(row, "evidence_quote", "") or "")
        if source is None or not quote or not evidence_is_verbatim(quote, str(source.chunk_text)):
            assignment = {"project_id": catalog["unassigned_project_id"],
                          "project_assignment_status": "PENDING_UNVERIFIED_EVIDENCE",
                          "project_assignment_basis": "missing_or_unverified_quote"}
        else:
            assignment = resolve_project("", quote, source.chunk_text, source.filename, catalog)
        assignments.append({
            "detected_project_id": assignment["project_id"],
            "project_assignment_status": assignment["project_assignment_status"],
            "project_assignment_basis": assignment["project_assignment_basis"],
            "project_scope_included": assignment["project_id"] == project_id
                and assignment["project_assignment_status"] in ASSIGNED_STATUSES,
            **(subdivision_assignment(assignment["project_id"], catalog, quote,
                                     str(source.chunk_text) if source is not None else "")
                if assignment["project_assignment_status"] in ASSIGNED_STATUSES else
                {"detected_subdivision_id": None, "subdivision_status": "PENDING_PROJECT"}),
        })
    for column in assignments[0] if assignments else []:
        result[column] = [a[column] for a in assignments]
    included = int(result.project_scope_included.sum()) if len(result) else 0
    return result, {"mode": "DOCUMENT_EVIDENCE", "signals_total": len(result),
                    "signals_active_project": included,
                    "signals_excluded_or_pending": len(result) - included}
