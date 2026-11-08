"""Recalcula analítica por proyecto reutilizando señales, vectores y exposición históricos."""

from typing import Any
import hashlib
import json
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.risk.build_intelligent_risk_profile import calculate_item_pird
from src.risk.build_risk_timeline import build_timeline
from src.risk.project_resolution import ASSIGNED_STATUSES, build_public_project_snapshot
from src.risk.project_scope import scope_signals
from src.risk.semantic_clustering import semantic_recurrence


EXPOSURE_COLUMNS = [
    "severity", "severity_supported", "probability", "probability_supported",
    "exposure_evidence_basis", "exposure_justification", "exposure_assessment_confidence",
]


def recompute_projects(items: pd.DataFrame, historical_scored: pd.DataFrame,
                       vector_index: pd.DataFrame, embeddings: np.ndarray,
                       chunks: pd.DataFrame, catalog: dict) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Alinea vectores por item_id y restringe vecindades antes de recalcular R/T/PIRD.

    La exposición S/P se conserva: no hay llamadas LLM ni etiquetas humanas nuevas.
    El snapshot histórico y los objetos de entrada no se modifican.
    """
    expected = set(items.item_id)
    for name, frame in (("items", items), ("histórico", historical_scored), ("vectores", vector_index)):
        if frame.item_id.isna().any() or frame.item_id.duplicated().any() or set(frame.item_id) != expected:
            raise ValueError(f"Identificadores incompletos o duplicados en {name}")
    matrix = np.asarray(embeddings)
    if matrix.ndim != 2 or len(matrix) != len(vector_index) or not np.isfinite(matrix).all():
        raise ValueError("Embeddings incompletos o no finitos")
    if (np.linalg.norm(matrix, axis=1) == 0).any():
        raise ValueError("Los embeddings no pueden ser vectores cero")
    if chunks.chunk_id.duplicated().any() or not items.source_chunk_id.isin(chunks.chunk_id).all():
        raise ValueError("Los fragmentos fuente no se pueden conciliar")
    historical = historical_scored.set_index("item_id").loc[items.item_id].reset_index()
    for column in items.columns:
        if not items[column].fillna("").reset_index(drop=True).equals(historical[column].fillna("").reset_index(drop=True)):
            raise ValueError(f"El histórico no coincide con las señales originales: {column}")
    index = vector_index.set_index("item_id")
    if not index.loc[items.item_id, "source_doc_id"].reset_index(drop=True).equals(items.source_doc_id.reset_index(drop=True)):
        raise ValueError("El índice vectorial no coincide con los documentos fuente")
    positions = pd.Series(np.arange(len(vector_index)), index=vector_index.item_id)
    matrix = matrix[positions.loc[items.item_id].to_numpy()]

    tagged, _ = scope_signals(items, chunks, str(catalog["projects"][0]["project_id"]), catalog)
    tagged["project_id"] = tagged.detected_project_id
    tagged = tagged.drop(columns="project_scope_included")
    assigned_mask = tagged.project_assignment_status.isin(ASSIGNED_STATUSES)
    outputs = []
    for project in catalog["projects"]:
        mask = assigned_mask & (tagged.project_id == project["project_id"])
        subset = tagged.loc[mask].reset_index(drop=True)
        if subset.empty:
            continue
        vectors = matrix[mask.to_numpy()]
        _, recurrence = semantic_recurrence(vectors, subset.source_doc_id, threshold=0.70)
        assignments = pd.DataFrame({"item_id": subset.item_id, "recurrence_level": recurrence})
        timeline, _ = build_timeline(subset, assignments, vectors, threshold=0.70)
        exposure = historical.loc[mask.to_numpy(), ["item_id", *EXPOSURE_COLUMNS]]
        outputs.append(calculate_item_pird(subset, exposure, timeline))
    pending = tagged.loc[~assigned_mask].copy()
    # La pertenencia pendiente no elimina valoraciones históricas sustentadas.
    # Se conservan para trazabilidad, sin habilitar el cálculo de PIRD por proyecto.
    pending = pending.merge(historical[["item_id", *EXPOSURE_COLUMNS]],
                            on="item_id", how="left", validate="one_to_one")
    pending["pird_status"] = "PENDIENTE_ASIGNACION_PROYECTO"
    pending["pird"] = np.nan
    pending["pird_level"] = None
    pending["document_date"] = None
    pending["temporal_role"] = None
    pending["recurrence_level"] = np.nan
    pending["persistence_level"] = np.nan
    outputs.append(pending)
    recomputed = pd.DataFrame.from_records([record for frame in outputs for record in frame.to_dict("records")])
    if len(recomputed) != len(items) or not recomputed.item_id.is_unique:
        raise ValueError("El recálculo no conserva exactamente las señales originales")
    snapshot = build_public_project_snapshot(recomputed, catalog)
    snapshot["scope_status"] = "PROVISIONAL_PROJECT_RECOMPUTED"
    snapshot["catalog_sha256"] = hashlib.sha256(json.dumps(catalog, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    snapshot["method"] = {
        "version": "PROJECT-RECOMPUTE-1",
        "reused": ["signal_classification", "BGE-M3_signal_embeddings", "severity_probability_rubric"],
        "recomputed_within_project": ["semantic_recurrence", "persistence", "PIRD", "category_profile"],
        "similarity_threshold": 0.70, "new_llm_calls": 0,
        "assignment_review": "PENDING_HUMAN_REVIEW",
        "severity_probability_human_gold_standard": False,
        "historical_snapshot_overwritten": False,
    }
    for project in snapshot["projects"]:
        project["profile"]["project_scope_status"] = "DOCUMENT_EVIDENCE"
        if project["profile"]["global_pird"] is None:
            project["profile"]["profile_status"] = "PENDIENTE"
            project["profile"]["global_level"] = "PENDIENTE"
    return recomputed, snapshot


def run(items_csv: Path, historical_csv: Path, vector_index_csv: Path, embeddings_npy: Path,
        chunks_csv: Path, catalog_json: Path, public_output: Path, private_output: Path) -> dict:
    from src.risk.corpus_project_catalog import load_catalog
    paths = {"items": items_csv, "scored": historical_csv, "index": vector_index_csv,
             "embeddings": embeddings_npy, "chunks": chunks_csv, "catalog": catalog_json}
    sources = {p.resolve() for p in paths.values()}
    if private_output.resolve() in sources or public_output.resolve() in sources or private_output.resolve() == public_output.resolve():
        raise ValueError("No se puede sobrescribir un archivo fuente")
    recomputed, snapshot = recompute_projects(
        pd.read_csv(items_csv), pd.read_csv(historical_csv), pd.read_csv(vector_index_csv),
        np.load(embeddings_npy, allow_pickle=False), pd.read_csv(chunks_csv), load_catalog(catalog_json))
    snapshot["provenance"] = {k: hashlib.sha256(path.read_bytes()).hexdigest() for k, path in paths.items()}
    public_output.parent.mkdir(parents=True, exist_ok=True)
    private_output.parent.mkdir(parents=True, exist_ok=True)
    public_output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    recomputed.to_csv(private_output, index=False, encoding="utf-8-sig")
    return snapshot


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("items-csv", "historical-csv", "vector-index-csv", "embeddings-npy", "chunks-csv",
                 "catalog-json", "public-output", "private-output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = vars(parser.parse_args())
    run(**args)
