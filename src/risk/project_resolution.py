"""Resuelve el proyecto de cada señal y publica únicamente agregados seguros."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from src.risk.pird import risk_level


PUBLIC_SCHEMA_VERSION = "1.0.0"
ASSIGNED_STATUSES = {
    "ASSIGNED_SIGNAL_EXPLICIT",
    "ASSIGNED_CONTEXT_NEAREST",
    "ASSIGNED_CHUNK_EXPLICIT",
    "ASSIGNED_FILENAME_EXPLICIT",
}


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text).casefold().strip()


def validate_project_catalog(catalog: dict[str, Any]) -> dict[str, Any]:
    """Valida un catálogo recibido desde archivo privado, secreto o memoria."""

    projects = catalog.get("projects", [])
    if not projects:
        raise ValueError("El catálogo de proyectos está vacío")
    project_ids = [str(item.get("project_id", "")).strip() for item in projects]
    if any(not value for value in project_ids) or len(project_ids) != len(set(project_ids)):
        raise ValueError("Los project_id deben existir y ser únicos")
    aliases: dict[str, str] = {}
    for project in projects:
        if not project.get("display_name") or not project.get("aliases"):
            raise ValueError("Cada proyecto requiere display_name y aliases")
        for alias in project["aliases"]:
            normalized = normalize_text(alias)
            owner = aliases.get(normalized)
            if owner and owner != project["project_id"]:
                raise ValueError(f"Alias ambiguo en el catálogo: {alias}")
            aliases[normalized] = project["project_id"]
    return catalog


def load_project_catalog(path: Path) -> dict[str, Any]:
    return validate_project_catalog(json.loads(Path(path).read_text(encoding="utf-8")))


def _alias_patterns(catalog: dict[str, Any]) -> list[tuple[str, re.Pattern[str]]]:
    patterns: list[tuple[str, re.Pattern[str]]] = []
    for project in catalog["projects"]:
        for alias in sorted(project["aliases"], key=len, reverse=True):
            normalized = normalize_text(alias)
            expression = r"(?<![a-z0-9])" + re.escape(normalized).replace(r"\ ", r"\s+") + r"(?![a-z0-9])"
            patterns.append((project["project_id"], re.compile(expression)))
    return patterns


def find_project_mentions(text: Any, catalog: dict[str, Any]) -> list[dict[str, Any]]:
    normalized = normalize_text(text)
    mentions: list[dict[str, Any]] = []
    for project_id, pattern in _alias_patterns(catalog):
        for match in pattern.finditer(normalized):
            mentions.append({"project_id": project_id, "start": match.start(), "end": match.end()})
    return sorted(mentions, key=lambda item: (item["start"], item["project_id"]))


def _unique_projects(mentions: Iterable[dict[str, Any]]) -> list[str]:
    return sorted({str(item["project_id"]) for item in mentions})


def _result(project_id: str, project_ids: list[str], status: str, confidence: float, basis: str) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "project_ids": "|".join(project_ids),
        "project_assignment_status": status,
        "project_assignment_confidence": confidence,
        "project_assignment_basis": basis,
    }


def resolve_project(
    signal_text: Any,
    evidence_text: Any,
    chunk_text: Any,
    filename: Any,
    catalog: dict[str, Any],
) -> dict[str, Any]:
    """Asigna solo con evidencia explícita y conserva ambigüedad como pendiente."""

    pending = str(catalog["unassigned_project_id"])
    multi = str(catalog["multi_project_id"])
    local_mentions = find_project_mentions(f"{signal_text or ''} {evidence_text or ''}", catalog)
    local_projects = _unique_projects(local_mentions)
    if len(local_projects) == 1:
        return _result(local_projects[0], local_projects, "ASSIGNED_SIGNAL_EXPLICIT", 1.0, "signal_or_evidence")
    if len(local_projects) > 1:
        return _result(multi, local_projects, "MULTI_PROJECT_SIGNAL", 1.0, "signal_or_evidence")

    chunk_normalized = normalize_text(chunk_text)
    chunk_mentions = find_project_mentions(chunk_text, catalog)
    chunk_projects = _unique_projects(chunk_mentions)
    evidence_normalized = normalize_text(evidence_text)
    anchor = chunk_normalized.find(evidence_normalized) if evidence_normalized else -1
    if anchor >= 0 and chunk_mentions:
        distances = []
        for mention in chunk_mentions:
            if mention["end"] <= anchor:
                distance = anchor - mention["end"]
            elif mention["start"] >= anchor + len(evidence_normalized):
                distance = mention["start"] - (anchor + len(evidence_normalized))
            else:
                distance = 0
            distances.append((distance, mention["project_id"]))
        best_distance = min(value[0] for value in distances)
        nearest = sorted({project for distance, project in distances if distance <= best_distance + 20})
        if len(nearest) == 1 and best_distance <= 800:
            return _result(nearest[0], nearest, "ASSIGNED_CONTEXT_NEAREST", 0.9, "nearest_chunk_mention")
        if len(nearest) > 1 and best_distance <= 800:
            return _result(multi, nearest, "AMBIGUOUS_CONTEXT", 0.0, "nearest_chunk_mention_tie")

    if len(chunk_projects) == 1:
        return _result(chunk_projects[0], chunk_projects, "ASSIGNED_CHUNK_EXPLICIT", 0.8, "single_project_in_chunk")
    if len(chunk_projects) > 1:
        return _result(multi, chunk_projects, "AMBIGUOUS_CONTEXT", 0.0, "multiple_projects_in_chunk")

    filename_projects = _unique_projects(find_project_mentions(filename, catalog))
    if len(filename_projects) == 1:
        return _result(filename_projects[0], filename_projects, "ASSIGNED_FILENAME_EXPLICIT", 0.7, "dedicated_filename")
    return _result(pending, [], "PENDING_NO_EVIDENCE", 0.0, "no_explicit_project")


def assign_projects(signals: pd.DataFrame, chunks: pd.DataFrame, catalog: dict[str, Any]) -> pd.DataFrame:
    required_signals = {"item_id", "source_chunk_id", "source_filename"}
    required_chunks = {"chunk_id", "chunk_text"}
    if not required_signals.issubset(signals.columns):
        raise ValueError(f"Faltan columnas de señales: {sorted(required_signals - set(signals.columns))}")
    if not required_chunks.issubset(chunks.columns):
        raise ValueError(f"Faltan columnas de chunks: {sorted(required_chunks - set(chunks.columns))}")
    chunk_text = chunks.drop_duplicates("chunk_id").set_index("chunk_id")["chunk_text"].fillna("").astype(str)
    assignments = []
    for row in signals.itertuples(index=False):
        row_data = row._asdict()
        signal_text = " ".join(str(row_data.get(field) or "") for field in ("title", "statement", "calibrated_justification"))
        evidence = row_data.get("evidence_quote", "")
        chunk = chunk_text.get(str(row_data["source_chunk_id"]), "")
        assignments.append(resolve_project(signal_text, evidence, chunk, row_data["source_filename"], catalog))
    return pd.concat([signals.reset_index(drop=True), pd.DataFrame(assignments)], axis=1)


def assign_chunks(chunks: pd.DataFrame, catalog: dict[str, Any]) -> pd.DataFrame:
    required = {"chunk_id", "filename", "chunk_text"}
    if not required.issubset(chunks.columns):
        raise ValueError(f"Faltan columnas de chunks: {sorted(required - set(chunks.columns))}")
    rows = []
    for row in chunks.itertuples(index=False):
        projects = _unique_projects(find_project_mentions(row.chunk_text, catalog))
        status = "ASSIGNED_CHUNK_EXPLICIT" if len(projects) == 1 else "AMBIGUOUS_CONTEXT" if len(projects) > 1 else "PENDING_NO_EVIDENCE"
        if not projects:
            projects = _unique_projects(find_project_mentions(row.filename, catalog))
            if len(projects) == 1:
                status = "ASSIGNED_FILENAME_EXPLICIT"
        rows.append({
            "chunk_id": row.chunk_id,
            "project_ids": "|".join(projects),
            "project_assignment_status": status,
        })
    return pd.DataFrame(rows)


def _project_profile(frame: pd.DataFrame) -> dict[str, Any]:
    valid = frame[frame["pird_status"] == "CALCULADO"].copy()
    totals = frame.groupby("calibrated_category", dropna=False).size().rename("total_signals")
    grouped = valid.groupby("calibrated_category", dropna=False)["pird"]
    categories = pd.DataFrame({
        "scored_signals": grouped.size(),
        "mean_pird": grouped.mean(),
        "p90_pird": grouped.quantile(0.90),
    }).join(totals, how="right").reset_index().rename(columns={"calibrated_category": "category"})
    categories["scored_signals"] = categories["scored_signals"].fillna(0).astype(int)
    categories["scoring_coverage"] = categories["scored_signals"] / categories["total_signals"]
    categories["category_score"] = 0.70 * categories["mean_pird"] + 0.30 * categories["p90_pird"]
    categories["category_level"] = categories["category_score"].map(lambda value: risk_level(value) if pd.notna(value) else None)
    categories = categories.sort_values("category_score", ascending=False, na_position="last")
    category_records = []
    for row in categories.itertuples(index=False):
        category_records.append({
            "category": str(row.category),
            "total_signals": int(row.total_signals),
            "scored_signals": int(row.scored_signals),
            "scoring_coverage": round(float(row.scoring_coverage), 4),
            "category_score": round(float(row.category_score), 4) if pd.notna(row.category_score) else None,
            "category_level": row.category_level,
        })
    calculable = categories[categories["category_score"].notna()]
    global_score = round(float(0.70 * calculable["category_score"].mean() + 0.30 * calculable["category_score"].max()), 2) if not calculable.empty else None
    total = len(frame)
    scored = len(valid)
    level_distribution = [
        {"pird_level": level, "signal_count": int((valid["pird_level"] == level).sum()), "percentage_of_scored": round(100 * float((valid["pird_level"] == level).sum()) / scored, 2) if scored else 0.0}
        for level in ("BAJO", "MEDIO", "ALTO", "CRITICO")
    ]
    temporal = {
        "signals": int(total),
        "source_documents": int(frame["source_doc_id"].nunique()),
        "signals_with_document_date": int(frame["document_date"].notna().sum()),
        "temporal_role_counts": {str(k): int(v) for k, v in frame["temporal_role"].fillna("PENDIENTE_FECHA").value_counts().items()},
        "persistence_level_counts": {str(int(k)): int(v) for k, v in frame["persistence_level"].dropna().value_counts().sort_index().items()},
        "privacy": "Individual dates, source names and signals are not published",
    }
    return {
        "profile": {
            "profile_status": "PROVISIONAL",
            "signals_total": int(total),
            "signals_scored": int(scored),
            "signals_pending": int(total - scored),
            "scoring_coverage": round(scored / total, 4) if total else 0.0,
            "global_pird": global_score,
            "global_level": risk_level(global_score) if global_score is not None else None,
            "top_categories": calculable.head(3)["category"].astype(str).tolist(),
            "critical_signals": int((valid["pird_level"] == "CRITICO").sum()),
            "high_signals": int((valid["pird_level"] == "ALTO").sum()),
        },
        "categories": category_records,
        "level_distribution": level_distribution,
        "timeline": temporal,
    }


def build_public_project_snapshot(tagged: pd.DataFrame, catalog: dict[str, Any]) -> dict[str, Any]:
    assigned = tagged[tagged["project_assignment_status"].isin(ASSIGNED_STATUSES)].copy()
    projects = []
    for project in catalog["projects"]:
        subset = assigned[assigned["project_id"] == project["project_id"]]
        aggregate = _project_profile(subset) if not subset.empty else {
            "profile": {"profile_status": "PENDIENTE", "signals_total": 0, "signals_scored": 0, "signals_pending": 0, "scoring_coverage": 0.0, "global_pird": None, "global_level": None, "top_categories": [], "critical_signals": 0, "high_signals": 0},
            "categories": [], "level_distribution": [],
            "timeline": {"signals": 0, "source_documents": 0, "signals_with_document_date": 0, "temporal_role_counts": {}, "persistence_level_counts": {}, "privacy": "Individual dates, source names and signals are not published"},
        }
        projects.append({"project_id": project["project_id"], "display_name": project["display_name"], **aggregate})
    counts = tagged["project_assignment_status"].value_counts().to_dict()
    total = len(tagged)
    return {
        "schema_version": PUBLIC_SCHEMA_VERSION,
        "scope_status": "PROVISIONAL_PROJECT_DISCRIMINATION",
        "catalog": [{"project_id": item["project_id"], "display_name": item["display_name"]} for item in catalog["projects"]],
        "assignment": {
            "signals_total": int(total),
            "signals_assigned_single_project": int(len(assigned)),
            "signals_pending_or_ambiguous": int(total - len(assigned)),
            "assignment_coverage": round(len(assigned) / total, 4) if total else 0.0,
            "status_counts": {str(k): int(v) for k, v in sorted(counts.items())},
        },
        "projects": projects,
        "data_policy": {
            "aggregate_only": True,
            "contains_source_text": False,
            "contains_individual_signals": False,
            "assignment_rule": "Explicit project evidence only; ambiguous and missing cases remain pending.",
        },
    }


def validate_public_project_snapshot(snapshot: dict[str, Any]) -> None:
    required = {"schema_version", "scope_status", "catalog", "assignment", "projects", "data_policy"}
    if not required.issubset(snapshot):
        raise ValueError("El snapshot público por proyecto está incompleto")
    assignment = snapshot["assignment"]
    if int(assignment["signals_total"]) != int(assignment["signals_assigned_single_project"]) + int(assignment["signals_pending_or_ambiguous"]):
        raise ValueError("La asignación por proyecto no concilia")
    if snapshot["data_policy"].get("contains_source_text") is not False or snapshot["data_policy"].get("contains_individual_signals") is not False:
        raise ValueError("El snapshot por proyecto no puede publicar evidencia ni señales individuales")
    total_projects = sum(int(item["profile"]["signals_total"]) for item in snapshot["projects"])
    if total_projects != int(assignment["signals_assigned_single_project"]):
        raise ValueError("Los totales de proyectos no concilian con las señales asignadas")


def run(signals_csv: Path, chunks_csv: Path, catalog_json: Path, public_output: Path, private_output: Path | None = None) -> dict[str, Any]:
    catalog = load_project_catalog(catalog_json)
    signals = pd.read_csv(signals_csv)
    chunks = pd.read_csv(chunks_csv)
    tagged = assign_projects(signals, chunks, catalog)
    snapshot = build_public_project_snapshot(tagged, catalog)
    validate_public_project_snapshot(snapshot)
    public_output.parent.mkdir(parents=True, exist_ok=True)
    public_output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    if private_output is not None:
        private_output.parent.mkdir(parents=True, exist_ok=True)
        tagged.to_csv(private_output, index=False, encoding="utf-8-sig")
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--signals-csv", required=True, type=Path)
    parser.add_argument("--chunks-csv", required=True, type=Path)
    parser.add_argument("--catalog-json", required=True, type=Path)
    parser.add_argument("--public-output", required=True, type=Path)
    parser.add_argument("--private-output", type=Path)
    args = parser.parse_args()
    snapshot = run(args.signals_csv, args.chunks_csv, args.catalog_json, args.public_output, args.private_output)
    print(json.dumps(snapshot["assignment"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
