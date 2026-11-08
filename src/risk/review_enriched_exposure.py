"""Aplica cuarentenas documentadas a propuestas nuevas; conserva la línea base."""

import json
from pathlib import Path

import pandas as pd

from src.risk.enrich_missing_exposure import prepare_cases, normalize_response, validate_response, apply_assessments

from src.risk.pird import PIRDInputs, calculate_pird
from src.risk.project_resolution import build_public_project_snapshot


def reconcile_checkpoint(baseline: pd.DataFrame, chunks: pd.DataFrame, catalog: dict, checkpoint: Path):
    """Reproduce propuestas desde respuestas guardadas, sin cliente ni nuevas llamadas."""
    cases = prepare_cases(baseline, chunks, catalog)
    lookup = {c["item_id"]: c for c in cases}
    seen, records = set(), []
    for line in checkpoint.read_text(encoding="utf-8").splitlines():
        saved = json.loads(line)
        ids = saved["ids"]
        if len(set(ids)) != len(ids) or not set(ids).issubset(lookup) or seen.intersection(ids):
            raise ValueError("IDs del checkpoint no conciliados")
        group = [lookup[i] for i in ids]
        if "raw_response" in saved:
            try:
                raw = json.loads(saved["raw_response"]).get("assessments")
            except (ValueError, AttributeError, TypeError):
                raw = None
            records.extend(normalize_response(raw, group))
        else:
            validate_response(saved["assessments"], group)
            records.extend(saved["assessments"])
        seen.update(ids)
    if seen != set(lookup):
        raise ValueError("Checkpoint incompleto para la cola original")
    return apply_assessments(baseline, cases, records, catalog)


def apply_quality_review(baseline: pd.DataFrame, proposed: pd.DataFrame, audit: pd.DataFrame,
                         policy: dict, catalog: dict, original_snapshot: dict):
    old = baseline.set_index("item_id").sort_index()
    result = proposed.set_index("item_id").sort_index().copy(deep=True)
    if not old.index.equals(result.index) or not old.index.is_unique:
        raise ValueError("Las señales no concilian con la línea base")
    reviewed = audit.copy(deep=True)
    reviewed["model_gate_accepted"] = reviewed.accepted
    reviewed["quality_review_decision"] = "NOT_QUARANTINED_NOT_EXPERT_VALIDATED"
    reviewed["quality_review_reason"] = ""
    seen, changed = set(), set()
    for decision in policy["decisions"]:
        item, component = decision["item_id"], decision["component"]
        key = (item, component)
        if component not in {"severity", "probability"} or key in seen or not decision["review_reason"].strip():
            raise ValueError("Decisión de cuarentena inválida o duplicada")
        if item not in result.index or pd.notna(old.at[item, component]):
            raise ValueError("La cuarentena solo puede afectar componentes nuevos")
        mask = (reviewed.item_id == item) & (reviewed.component == component)
        if mask.sum() != 1 or not bool(reviewed.loc[mask, "accepted"].iloc[0]):
            raise ValueError("La propuesta no tiene una aceptación única")
        value = result.at[item, component]
        if pd.isna(value) or value != decision["model_value"] or reviewed.loc[mask, "quote"].iloc[0] != decision["model_quote"]:
            raise ValueError("La cuarentena no corresponde a la propuesta registrada")
        result.at[item, component] = old.at[item, component]
        result.at[item, component + "_supported"] = old.at[item, component + "_supported"]
        reviewed.loc[mask, "accepted"] = False
        reviewed.loc[mask, "quality_review_decision"] = decision["review_code"]
        reviewed.loc[mask, "quality_review_reason"] = decision["review_reason"]
        seen.add(key); changed.add(item)
    for item in changed:
        row = result.loc[item]
        level = lambda col: None if pd.isna(row[col]) else float(row[col])
        score = calculate_pird(PIRDInputs(level("severity"), level("probability"), level("recurrence_level"),
            level("persistence_level"), 5.0 if int(row.calibrated_evidence_sufficient) == 1 else None,
            1.0 + 4.0 * float(row.calibrated_confidence)))
        for column, key in [("pird", "pird"), ("pird_status", "score_status"), ("pird_level", "risk_level"),
                            ("exposure_index", "exposure_index"), ("reliability_index", "reliability_index")]:
            result.at[item, column] = score[key]
        result.at[item, "pird_missing_components"] = ",".join(score["missing_components"])
    for component in ("severity", "probability"):
        present = old[component].notna()
        pd.testing.assert_series_equal(old.loc[present, component], result.loc[present, component], check_dtype=False)
    scored = old.pird.notna()
    pd.testing.assert_series_equal(old.loc[scored, "pird"], result.loc[scored, "pird"], check_dtype=False)
    output = result.reset_index()
    snapshot = build_public_project_snapshot(output, catalog)
    snapshot["catalog_sha256"] = original_snapshot["catalog_sha256"]
    snapshot["scope_status"] = "PROJECT_CONTEXT_ENRICHED_QUALITY_REVIEWED"
    snapshot["method"] = {**original_snapshot.get("method", {}),
        "exposure_enrichment_version": "EXPOSURE-CONTEXT-1", "runner_version": "1.1",
        "quality_review_policy": policy["policy"], "quality_review_role": "ASSISTANT_NOT_EXPERT",
        "model_gate_accepted_components": int(audit.accepted.sum()),
        "quarantined_components": len(seen), "retained_new_components": int(reviewed.accepted.sum()),
        "expert_validation_of_new_values": False, "historical_scores_preserved": int(scored.sum())}
    for project in snapshot["projects"]:
        project["profile"]["project_scope_status"] = "DOCUMENT_EVIDENCE"
        if project["profile"]["global_pird"] is None:
            project["profile"]["global_level"] = "PENDIENTE"
    return output, reviewed, snapshot
