"""Procesamiento de riesgos en memoria por proyecto — Día 19B.

Conecta la ingesta del Día 19A con la extracción documental v2, la
clasificación del Día 5, la puerta determinista del Día 6 y el PIRD de los
Días 9–11. No persiste texto, evidencia, embeddings ni resultados privados.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.risk.build_intelligent_risk_profile import (
    MODEL as PROFILE_MODEL,
    SCHEMA as PROFILE_SCHEMA,
    build_profile,
    build_prompt as build_exposure_prompt,
    calculate_item_pird,
    sanitize as sanitize_exposure,
)
from src.risk.build_risk_timeline import build_timeline
from src.risk.calibrate_documentary_classifier import (
    build_prompt as build_calibration_prompt,
    call as call_calibration_model,
    sanitize as sanitize_classification,
)
from src.risk.extract_documentary_items import (
    build_prompt as build_extraction_prompt,
    call_model as call_extraction_model,
    parse_response,
    sanitize_item,
)
from src.risk.run_validation_agent import validate_catalog
from src.risk.semantic_clustering import semantic_recurrence


MAX_ANALYSIS_CHUNKS = 100
CLASSIFICATION_BATCH_SIZE = 10
EXPOSURE_BATCH_SIZE = 10
CALIBRATION_COLUMNS = [
    "title", "statement", "evidence_quote", "human_type", "human_watch",
    "human_evidence", "human_category",
]


def _usage_values(usage: Any) -> tuple[int, int]:
    return (
        int(getattr(usage, "prompt_tokens", 0) or 0),
        int(getattr(usage, "completion_tokens", 0) or 0),
    )


def parse_calibration_examples(raw: Any) -> pd.DataFrame:
    """Valida ejemplos privados sin incluirlos en código ni resultados públicos."""

    if not raw:
        return pd.DataFrame(columns=CALIBRATION_COLUMNS)
    payload = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(payload, list):
        raise ValueError("CALIBRATION_EXAMPLES_JSON debe contener una lista JSON")
    aliases = {
        "evidence": "evidence_quote",
        "correct_type": "human_type",
        "correct_watch": "human_watch",
        "correct_evidence": "human_evidence",
        "correct_category": "human_category",
    }
    frame = pd.DataFrame(payload).rename(columns=aliases)
    missing = set(CALIBRATION_COLUMNS).difference(frame.columns)
    if missing:
        raise ValueError(f"Faltan campos en los ejemplos de calibración: {sorted(missing)}")
    frame = frame[CALIBRATION_COLUMNS].dropna().copy()
    frame["human_watch"] = frame.human_watch.astype(int)
    frame["human_evidence"] = frame.human_evidence.astype(int)
    return frame


def _extract_items(chunks: pd.DataFrame, client: Any) -> tuple[pd.DataFrame, dict]:
    records: list[dict] = []
    prompt_tokens = completion_tokens = returned_items = rejected_evidence = 0
    for _, row in chunks.iterrows():
        raw, usage = call_extraction_model(client, build_extraction_prompt(row))
        parsed = parse_response(raw)
        accepted = [value for value in (sanitize_item(item, row) for item in parsed) if value]
        records.extend(accepted)
        returned_items += len(parsed)
        rejected_evidence += len(parsed) - len(accepted)
        prompt, completion = _usage_values(usage)
        prompt_tokens += prompt
        completion_tokens += completion
    if not records:
        return pd.DataFrame(), {
            "chunks_analyzed": int(len(chunks)), "items_returned": returned_items,
            "items_with_verified_evidence": 0, "items_rejected_evidence": rejected_evidence,
            "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
        }
    items = pd.DataFrame(records).drop_duplicates(
        subset=["source_chunk_id", "item_type", "evidence_quote"]
    ).reset_index(drop=True)
    items.insert(0, "item_id", [f"ITEM_{index:05d}" for index in range(1, len(items) + 1)])
    return items, {
        "chunks_analyzed": int(len(chunks)), "items_returned": returned_items,
        "items_with_verified_evidence": int(len(items)), "items_rejected_evidence": rejected_evidence,
        "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
    }


def _classify_items(
    items: pd.DataFrame,
    chunks: pd.DataFrame,
    client: Any,
    examples: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    chunk_lookup = chunks.set_index("chunk_id").chunk_text.to_dict()
    predictions: list[dict] = []
    prompt_tokens = completion_tokens = 0
    for start in range(0, len(items), CLASSIFICATION_BATCH_SIZE):
        batch = items.iloc[start:start + CLASSIFICATION_BATCH_SIZE]
        returned, usage = call_calibration_model(
            client, build_calibration_prompt(batch, examples, chunk_lookup)
        )
        by_id = {value.get("item_id"): value for value in returned}
        predictions.extend(
            sanitize_classification(by_id.get(item_id, {}), item_id)
            for item_id in batch.item_id
        )
        prompt, completion = _usage_values(usage)
        prompt_tokens += prompt
        completion_tokens += completion
    classified = items.merge(pd.DataFrame(predictions), on="item_id", validate="one_to_one")
    calibrated = len(examples) > 0
    return classified, {
        "classification_mode": "HUMAN_EXAMPLES" if calibrated else "CRITERIA_ONLY_PROVISIONAL",
        "human_examples_available": int(len(examples)),
        "calibration_status": "CALIBRATED" if calibrated else "PROVISIONAL_NO_PRIVATE_EXAMPLES",
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
    }


def _assess_exposure(items: pd.DataFrame, client: Any) -> tuple[pd.DataFrame, dict]:
    rows: list[dict] = []
    prompt_tokens = completion_tokens = 0
    for start in range(0, len(items), EXPOSURE_BATCH_SIZE):
        batch = items.iloc[start:start + EXPOSURE_BATCH_SIZE]
        response = client.chat.completions.create(
            model=PROFILE_MODEL,
            temperature=0.0,
            messages=[
                {"role": "system", "content": "Evalúa exposición documental con la rúbrica y responde JSON estricto."},
                {"role": "user", "content": build_exposure_prompt(batch)},
            ],
            response_format=PROFILE_SCHEMA,
        )
        parsed = json.loads(response.choices[0].message.content or '{"assessments":[]}')
        by_id = {value.get("item_id"): value for value in parsed.get("assessments", [])}
        rows.extend(sanitize_exposure(by_id.get(item_id, {}), item_id) for item_id in batch.item_id)
        prompt, completion = _usage_values(response.usage)
        prompt_tokens += prompt
        completion_tokens += completion
    return pd.DataFrame(rows), {
        "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
    }


def _pending_result(project_id: str, extraction: dict, classification: dict | None = None) -> dict:
    classification = classification or {
        "classification_mode": "NOT_APPLICABLE", "human_examples_available": 0,
        "calibration_status": "NOT_APPLICABLE", "prompt_tokens": 0, "completion_tokens": 0,
    }
    total_prompt = extraction["prompt_tokens"] + classification["prompt_tokens"]
    total_completion = extraction["completion_tokens"] + classification["completion_tokens"]
    return {
        "project_id": project_id,
        "status": "COMPLETED_NO_VALIDATED_SIGNALS",
        "summary": {
            "chunks_analyzed": extraction["chunks_analyzed"],
            "items_extracted": extraction["items_with_verified_evidence"],
            "signals_validated": 0, "signals_scored": 0, "signals_pending": 0,
            "scoring_coverage": 0.0, "global_pird": None, "global_level": None,
            "profile_status": "PENDIENTE_SIN_SENALES_VALIDADAS",
        },
        "classification": classification,
        "validation": {"items_received": extraction["items_with_verified_evidence"], "items_accepted": 0},
        "timeline": {"signals": 0, "signals_with_persistence": 0},
        "categories": [],
        "usage": {"prompt_tokens": total_prompt, "completion_tokens": total_completion,
                  "total_tokens": total_prompt + total_completion},
        "private": {"items": [], "validated_signals": [], "scored_signals": []},
    }


def process_project_risks(
    ingestion_result: dict[str, Any],
    client: Any,
    encoder: Any,
    calibration_examples: Any = None,
) -> dict[str, Any]:
    """Calcula un perfil de riesgo aislado para la ingesta de un proyecto."""

    project_id = str(ingestion_result.get("project_id") or "")
    chunks_payload = ingestion_result.get("chunks") or []
    if not project_id or not chunks_payload:
        raise ValueError("La ingesta del proyecto está incompleta")
    if len(chunks_payload) > MAX_ANALYSIS_CHUNKS:
        raise ValueError(f"El Día 19B permite máximo {MAX_ANALYSIS_CHUNKS} chunks por ejecución")
    if any(str(row.get("project_id")) != project_id for row in chunks_payload):
        raise ValueError("La ingesta contiene chunks de otro proyecto")

    chunks = pd.DataFrame(chunks_payload).copy()
    chunks["tipo_documento"] = chunks.filename.map(
        lambda name: Path(str(name)).suffix.lower().lstrip(".").upper() or "DESCONOCIDO"
    )
    items, extraction = _extract_items(chunks, client)
    if items.empty:
        return _pending_result(project_id, extraction)

    examples = parse_calibration_examples(calibration_examples)
    classified, classification = _classify_items(items, chunks, client, examples)
    decisions, validation = validate_catalog(classified)
    accepted = decisions[decisions.validation_accepted == 1].reset_index(drop=True)
    if accepted.empty:
        result = _pending_result(project_id, extraction, classification)
        result["validation"] = validation
        result["private"]["items"] = decisions.to_dict(orient="records")
        return result

    signal_texts = (
        accepted.title.fillna("") + ". " + accepted.statement.fillna("") +
        ". " + accepted.evidence_quote.fillna("")
    ).tolist()
    embeddings = np.asarray(
        encoder.encode(signal_texts, batch_size=16, show_progress_bar=False,
                       normalize_embeddings=True, convert_to_numpy=True),
        dtype=np.float32,
    )
    recurrence_docs, recurrence_levels = semantic_recurrence(
        embeddings, accepted.source_doc_id, threshold=0.70
    )
    assignments = pd.DataFrame({
        "item_id": accepted.item_id,
        "recurrence_other_document_count": recurrence_docs,
        "recurrence_level": recurrence_levels,
    })
    timeline, timeline_summary = build_timeline(accepted, assignments, embeddings)
    exposure, exposure_usage = _assess_exposure(accepted, client)
    scored = calculate_item_pird(accepted, exposure, timeline)
    categories, profile = build_profile(scored)

    if profile.get("profile_status") == "PENDIENTE":
        summary = {
            "chunks_analyzed": extraction["chunks_analyzed"],
            "items_extracted": int(len(items)), "signals_validated": int(len(accepted)),
            "signals_scored": 0, "signals_pending": int(len(accepted)),
            "scoring_coverage": 0.0, "global_pird": None, "global_level": None,
            "profile_status": "PENDIENTE_COMPONENTES_PIRD",
        }
    else:
        summary = {
            "chunks_analyzed": extraction["chunks_analyzed"],
            "items_extracted": int(len(items)), "signals_validated": int(len(accepted)),
            "signals_scored": profile["signals_scored"], "signals_pending": profile["signals_pending"],
            "scoring_coverage": profile["scoring_coverage"], "global_pird": profile["global_pird"],
            "global_level": profile["global_level"], "profile_status": profile["profile_status"],
        }

    prompt_tokens = extraction["prompt_tokens"] + classification["prompt_tokens"] + exposure_usage["prompt_tokens"]
    completion_tokens = extraction["completion_tokens"] + classification["completion_tokens"] + exposure_usage["completion_tokens"]
    public_categories = [] if categories.empty else [
        {
            "category": row.calibrated_category,
            "category_score": round(float(row.category_score), 2),
            "category_level": row.category_level,
            "scoring_coverage": round(float(row.scoring_coverage), 4),
            "scored_signals": int(row.scored_signals),
            "total_signals": int(row.total_signals),
        }
        for row in categories.itertuples()
    ]
    return {
        "project_id": project_id,
        "status": "COMPLETED",
        "summary": summary,
        "classification": classification,
        "validation": validation,
        "timeline": timeline_summary,
        "categories": public_categories,
        "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
                  "total_tokens": prompt_tokens + completion_tokens},
        "configuration": {
            "extraction": "documentary_extraction_v2", "validation": "deterministic_day_06",
            "embedding_model": "BAAI/bge-m3", "recurrence_similarity_threshold": 0.70,
            "pird": "days_09_to_11", "persistence": "session_memory_only",
        },
        "private": {
            "items": decisions.to_dict(orient="records"),
            "validated_signals": accepted.to_dict(orient="records"),
            "scored_signals": scored.replace({np.nan: None}).to_dict(orient="records"),
        },
    }
