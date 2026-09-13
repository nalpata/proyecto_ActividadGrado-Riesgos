"""Aplica la puerta final de validación a elementos documentales calibrados."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "item_id", "source_doc_id", "source_filename", "source_page", "source_chunk_id",
    "title", "statement", "evidence_quote", "evidence_verified",
    "calibrated_type", "calibrated_watch", "calibrated_evidence_sufficient",
    "calibrated_category", "calibrated_confidence", "calibrated_justification",
}


def validate_row(row: pd.Series) -> dict:
    """Devuelve una decisión determinista y explicable para un elemento."""
    evidence = str(row.get("evidence_quote", "") or "").strip()
    verified = int(row.get("evidence_verified", 0) or 0) == 1
    sufficient = int(row.get("calibrated_evidence_sufficient", 0) or 0) == 1
    watch = int(row.get("calibrated_watch", 0) or 0) == 1
    confidence = float(row.get("calibrated_confidence", 0) or 0)

    if not evidence or not verified:
        accepted, reason = 0, "EVIDENCIA_AUSENTE_O_NO_VERIFICADA"
    elif not sufficient:
        accepted, reason = 0, "EVIDENCIA_INSUFICIENTE"
    elif not watch:
        accepted, reason = 0, "NO_REQUIERE_VIGILANCIA"
    else:
        accepted, reason = 1, "ACEPTADO"

    confidence_band = "ALTA" if confidence >= 0.80 else "MEDIA" if confidence >= 0.60 else "BAJA"
    return {
        "validation_decision": "ACEPTADO" if accepted else "RECHAZADO",
        "validation_accepted": accepted,
        "validation_reason": reason,
        "validation_confidence": confidence,
        "validation_confidence_band": confidence_band,
        "validation_justification": str(row.get("calibrated_justification", "") or "").strip(),
    }


def validate_catalog(items: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    missing = sorted(REQUIRED_COLUMNS - set(items.columns))
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {', '.join(missing)}")
    if items["item_id"].duplicated().any():
        raise ValueError("item_id contiene duplicados")

    decisions = pd.DataFrame([validate_row(row) for _, row in items.iterrows()])
    result = pd.concat([items.reset_index(drop=True), decisions], axis=1)
    accepted = int(result.validation_accepted.sum())
    reasons = result.validation_reason.value_counts().to_dict()
    confidence = result.validation_confidence_band.value_counts().to_dict()
    summary = {
        "items_received": int(len(result)),
        "items_accepted": accepted,
        "items_rejected": int(len(result) - accepted),
        "acceptance_rate": round(accepted / len(result), 4) if len(result) else 0,
        "rejection_rate": round((len(result) - accepted) / len(result), 4) if len(result) else 0,
        "decision_reasons": {str(k): int(v) for k, v in reasons.items()},
        "confidence_bands": {str(k): int(v) for k, v in confidence.items()},
        "decision_rule": "Aceptar solo cuando vigilancia=1, evidencia_suficiente=1 y evidencia verificada presente",
        "confidence_policy": "La confianza se informa, pero no actúa como umbral de rechazo",
    }
    return result, summary


def run(input_csv: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    items = pd.read_csv(input_csv)
    result, summary = validate_catalog(items)
    result.to_csv(output_dir / "validation_decisions.csv", index=False, encoding="utf-8-sig")
    result[result.validation_accepted == 1].to_csv(
        output_dir / "validated_surveillance_catalog.csv", index=False, encoding="utf-8-sig"
    )
    result[result.validation_accepted == 0].to_csv(
        output_dir / "validation_rejections.csv", index=False, encoding="utf-8-sig"
    )
    (output_dir / "validation_agent_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.input, args.output_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
