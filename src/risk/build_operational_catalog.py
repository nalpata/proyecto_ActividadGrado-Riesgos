"""Construye el catálogo operativo de señales de riesgo para radar y front.

Combina los resultados del validador v2 con una muestra adjudicada por una
persona. La decisión humana final prevalece únicamente para los registros
revisados; los demás conservan la decisión del validador. El script no elimina
registros silenciosamente: marca candidatos similares y selecciona un registro
primario por grupo para evitar doble conteo en el radar.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd


REQUIRED_VALIDATOR_COLUMNS = {
    "risk_id", "source_doc_id", "source_filename", "source_page",
    "source_chunk_id", "risk_name", "risk_category", "severity",
    "probability", "risk_score", "risk_description", "evidence",
    "recommended_action", "validator_is_valid",
    "validator_evidence_sufficient", "validator_corrected_category",
    "validator_confidence",
}


def read_table(path: Path, sheet_name: str | int = 0) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path, sheet_name=sheet_name)
    raise ValueError(f"Formato no soportado: {path}")


def normalize_binary(value):
    if pd.isna(value) or str(value).strip() == "":
        return pd.NA
    text = str(value).strip().lower()
    if text in {"1", "1.0", "si", "sí", "true", "valido", "válido"}:
        return 1
    if text in {"0", "0.0", "no", "false", "invalido", "inválido"}:
        return 0
    return pd.NA


def normalize_text(value) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def load_human_decisions(path: Path) -> pd.DataFrame:
    human = read_table(path)
    decision_candidates = ["human_final", "decision_final", "control_humano_valido"]
    decision_column = next((c for c in decision_candidates if c in human.columns), None)
    if decision_column is None:
        raise ValueError(
            "La muestra adjudicada debe incluir human_final, decision_final "
            "o control_humano_valido."
        )
    if "risk_id" not in human.columns:
        raise ValueError("La muestra adjudicada no contiene risk_id.")
    result = human[["risk_id", decision_column]].copy()
    result["human_final"] = result[decision_column].map(normalize_binary)
    result = result[result["human_final"].notna()][["risk_id", "human_final"]]
    result["human_final"] = result["human_final"].astype(int)
    return result.drop_duplicates("risk_id", keep="last")


def apply_decisions(results: pd.DataFrame, human: pd.DataFrame) -> pd.DataFrame:
    catalog = results.merge(human, on="risk_id", how="left", validate="one_to_one")
    catalog["decision_source"] = catalog["human_final"].notna().map(
        {True: "human_adjudication", False: "validator_v2"}
    )
    human_final = catalog["human_final"].astype("Int64")
    validator_final = catalog["validator_is_valid"].map(normalize_binary).astype("Int64")
    catalog["final_is_valid"] = human_final.combine_first(validator_final)
    catalog["final_category"] = catalog["validator_corrected_category"].fillna(
        catalog["risk_category"]
    )
    # Una decisión humana positiva prevalece aunque el agente haya considerado
    # insuficiente la evidencia. Para decisiones automáticas se exigen ambas.
    catalog["operational_inclusion"] = (
        ((catalog["decision_source"] == "human_adjudication") & (catalog["final_is_valid"] == 1))
        | (
            (catalog["decision_source"] == "validator_v2")
            & (catalog["final_is_valid"] == 1)
            & (catalog["validator_evidence_sufficient"].map(normalize_binary) == 1)
        )
    ).astype(int)
    catalog["priority_level"] = pd.cut(
        pd.to_numeric(catalog["risk_score"], errors="coerce").fillna(0),
        bins=[-1, 2, 4, 6, float("inf")],
        labels=["Baja", "Media", "Alta", "Crítica"],
    ).astype(str)
    catalog["needs_review"] = (
        (catalog["decision_source"] == "validator_v2")
        & (
            (pd.to_numeric(catalog["validator_confidence"], errors="coerce") < 0.85)
            | (catalog["validator_evidence_sufficient"].map(normalize_binary) != 1)
        )
    ).astype(int)
    return catalog


def mark_similar_records(catalog: pd.DataFrame, threshold: float = 0.92) -> pd.DataFrame:
    catalog = catalog.copy()
    catalog["duplicate_group"] = ""
    catalog["operational_is_primary"] = catalog["operational_inclusion"].astype(int)
    active = catalog[catalog["operational_inclusion"] == 1]
    group_number = 0
    for (_, _), group in active.groupby(["source_doc_id", "final_category"], dropna=False):
        indexes = list(group.index)
        used: set[int] = set()
        for position, left in enumerate(indexes):
            if left in used:
                continue
            cluster = [left]
            left_text = normalize_text(
                f"{catalog.at[left, 'risk_description']} {catalog.at[left, 'evidence']}"
            )
            for right in indexes[position + 1:]:
                if right in used:
                    continue
                right_text = normalize_text(
                    f"{catalog.at[right, 'risk_description']} {catalog.at[right, 'evidence']}"
                )
                if SequenceMatcher(None, left_text, right_text).ratio() >= threshold:
                    cluster.append(right)
                    used.add(right)
            if len(cluster) > 1:
                group_number += 1
                label = f"DUP_{group_number:03d}"
                ordered = sorted(
                    cluster,
                    key=lambda idx: (
                        int(catalog.at[idx, "risk_score"]),
                        float(catalog.at[idx, "validator_confidence"]),
                    ),
                    reverse=True,
                )
                catalog.loc[cluster, "duplicate_group"] = label
                catalog.loc[ordered[1:], "operational_is_primary"] = 0
            used.add(left)
    return catalog


def build_radar(catalog: pd.DataFrame) -> pd.DataFrame:
    active = catalog[
        (catalog["operational_inclusion"] == 1)
        & (catalog["operational_is_primary"] == 1)
    ].copy()
    if active.empty:
        return pd.DataFrame(columns=["category", "risk_count", "mean_score", "max_score", "radar_score"])
    radar = (
        active.groupby("final_category", as_index=False)
        .agg(
            risk_count=("risk_id", "count"),
            mean_score=("risk_score", "mean"),
            max_score=("risk_score", "max"),
            high_or_critical=("priority_level", lambda s: int(s.isin(["Alta", "Crítica"]).sum())),
        )
        .rename(columns={"final_category": "category"})
    )
    # Puntaje explicable 0-100: combina intensidad media (70 %) y máxima (30 %).
    radar["radar_score"] = (
        100 * (0.70 * radar["mean_score"] / 9 + 0.30 * radar["max_score"] / 9)
    ).round(1).clip(0, 100)
    radar["mean_score"] = radar["mean_score"].round(2)
    return radar.sort_values(["radar_score", "risk_count"], ascending=False)


def build_catalog(
    validator_path: Path,
    adjudicated_path: Path,
    output_dir: Path,
    similarity_threshold: float = 0.92,
) -> dict:
    results = read_table(validator_path)
    missing = REQUIRED_VALIDATOR_COLUMNS - set(results.columns)
    if missing:
        raise ValueError(f"Faltan columnas del validador: {sorted(missing)}")
    human = load_human_decisions(adjudicated_path)
    unknown = sorted(set(human["risk_id"]) - set(results["risk_id"]))
    if unknown:
        raise ValueError(f"Hay risk_id adjudicados que no existen en el validador: {unknown}")
    catalog = mark_similar_records(apply_decisions(results, human), similarity_threshold)
    radar = build_radar(catalog)
    output_dir.mkdir(parents=True, exist_ok=True)

    export_columns = [
        "risk_id", "source_doc_id", "source_filename", "source_page", "source_chunk_id",
        "risk_name", "risk_category", "final_category", "severity", "probability",
        "risk_score", "priority_level", "risk_description", "evidence", "recommended_action",
        "validator_is_valid", "validator_evidence_sufficient", "validator_confidence",
        "human_final", "decision_source", "final_is_valid", "operational_inclusion",
        "needs_review", "duplicate_group", "operational_is_primary",
    ]
    catalog[export_columns].to_csv(
        output_dir / "operational_risk_catalog.csv", index=False, encoding="utf-8-sig"
    )
    radar.to_csv(output_dir / "radar_by_category.csv", index=False, encoding="utf-8-sig")
    catalog[catalog["needs_review"] == 1][export_columns].to_csv(
        output_dir / "risk_review_queue.csv", index=False, encoding="utf-8-sig"
    )
    summary = {
        "total_candidates": int(len(catalog)),
        "human_adjudicated": int((catalog["decision_source"] == "human_adjudication").sum()),
        "validator_only": int((catalog["decision_source"] == "validator_v2").sum()),
        "operational_included": int(catalog["operational_inclusion"].sum()),
        "operational_excluded": int((catalog["operational_inclusion"] == 0).sum()),
        "primary_signals_for_radar": int(catalog["operational_is_primary"].sum()),
        "possible_duplicate_rows": int((catalog["duplicate_group"] != "").sum()),
        "review_queue": int(catalog["needs_review"].sum()),
        "similarity_threshold": similarity_threshold,
        "decision_rule": "human_final overrides validator_v2 only for adjudicated risk_id",
        "radar_formula": "100 * (0.70 * mean_score/9 + 0.30 * max_score/9)",
        "academic_limitation": (
            "Las decisiones no adjudicadas son automáticas; el catálogo es insumo de un "
            "prototipo académico y requiere supervisión humana para uso operativo real."
        ),
    }
    (output_dir / "operational_catalog_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validator-results", required=True, type=Path)
    parser.add_argument("--adjudicated-sample", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--similarity-threshold", type=float, default=0.92)
    args = parser.parse_args()
    summary = build_catalog(
        args.validator_results,
        args.adjudicated_sample,
        args.output_dir,
        args.similarity_threshold,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
