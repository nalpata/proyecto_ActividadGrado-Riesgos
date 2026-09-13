"""Estandariza severidad/probabilidad, calcula PIRD y construye el perfil ejecutivo."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from src.risk.pird import PIRDInputs, calculate_pird, risk_level


MODEL = "gpt-4o-mini"
SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "pird_exposure_assessment", "strict": True,
        "schema": {
            "type": "object", "properties": {"assessments": {"type": "array", "items": {
                "type": "object", "properties": {
                    "item_id": {"type": "string"},
                    "severity": {"type": ["integer", "null"], "minimum": 1, "maximum": 5},
                    "severity_supported": {"type": "integer", "enum": [0, 1]},
                    "probability": {"type": ["integer", "null"], "minimum": 1, "maximum": 5},
                    "probability_supported": {"type": "integer", "enum": [0, 1]},
                    "evidence_basis": {"type": "string"},
                    "justification": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["item_id", "severity", "severity_supported", "probability", "probability_supported", "evidence_basis", "justification", "confidence"],
                "additionalProperties": False,
            }}}, "required": ["assessments"], "additionalProperties": False,
        },
    },
}


def build_prompt(batch: pd.DataFrame) -> str:
    records = []
    for row in batch.itertuples():
        records.append({
            "item_id": row.item_id, "type": row.calibrated_type, "category": row.calibrated_category,
            "exposure_status": row.exposure_status, "title": row.title,
            "statement": row.statement, "evidence": row.evidence_quote,
        })
    return f"""Evalúa severidad y probabilidad documental para cada señal. Usa solo el texto entregado; no agregues consecuencias, cifras ni contexto externo.

SEVERIDAD (impacto sustentado):
1 = impacto mínimo o administrativo, sin afectación objetiva demostrada.
2 = afectación limitada, local y reversible.
3 = afectación moderada a un objetivo del proyecto que requiere gestión.
4 = afectación alta y material a plazo, costo, calidad, operación, seguridad o contrato.
5 = afectación crítica que amenaza continuidad, cumplimiento esencial, seguridad grave o viabilidad.

PROBABILIDAD (posibilidad de que la exposición adversa continúe o se materialice, según esta evidencia):
1 = remota o condición cerrada/resuelta.
2 = posible, con indicios débiles.
3 = plausible, con un indicador concreto.
4 = probable, por condición abierta, incumplimiento o evidencia fuerte.
5 = casi cierta, por ocurrencia confirmada que continúa abierta o repetición explícita en el mismo texto.

REGLAS:
- Para hechos ocurridos y hallazgos, evalúa la probabilidad de continuidad de la exposición, no la probabilidad del hecho pasado.
- No utilices recurrencia entre documentos ni persistencia temporal: se incorporan aparte en el PIRD.
- Marca supported=1 solo cuando la cita permite justificar el nivel.
- Si no hay base suficiente, devuelve el nivel null y supported=0.
- evidence_basis debe ser una frase breve tomada o parafraseada estrictamente de la cita.
- Devuelve exactamente una evaluación por item_id.

SEÑALES:
{json.dumps(records, ensure_ascii=False)}"""


def sanitize(raw: dict, item_id: str) -> dict:
    severity = raw.get("severity") if raw.get("severity_supported") == 1 else None
    probability = raw.get("probability") if raw.get("probability_supported") == 1 else None
    if severity not in {1, 2, 3, 4, 5}: severity = None
    if probability not in {1, 2, 3, 4, 5}: probability = None
    return {
        "item_id": item_id, "severity": severity, "severity_supported": int(severity is not None),
        "probability": probability, "probability_supported": int(probability is not None),
        "exposure_evidence_basis": str(raw.get("evidence_basis", ""))[:500],
        "exposure_justification": str(raw.get("justification", ""))[:1000],
        "exposure_assessment_confidence": min(1.0, max(0.0, float(raw.get("confidence", 0) or 0))),
    }


def assess_exposure(items: pd.DataFrame, output_dir: Path, batch_size: int = 10) -> tuple[pd.DataFrame, dict]:
    from openai import OpenAI
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Falta OPENAI_API_KEY")
    checkpoint = output_dir / "exposure_assessment_checkpoint.jsonl"
    completed, rows = set(), []
    if checkpoint.exists():
        for line in checkpoint.read_text(encoding="utf-8").splitlines():
            record = json.loads(line); completed.update(record["item_ids"]); rows.extend(record["assessments"])
    pending = items[~items.item_id.isin(completed)]
    client = OpenAI(); prompt_tokens = completion_tokens = 0
    for start in range(0, len(pending), batch_size):
        batch = pending.iloc[start:start + batch_size]
        response = client.chat.completions.create(
            model=MODEL, temperature=0.0,
            messages=[{"role": "system", "content": "Evalúa exposición documental con la rúbrica y responde JSON estricto."}, {"role": "user", "content": build_prompt(batch)}],
            response_format=SCHEMA,
        )
        parsed = json.loads(response.choices[0].message.content or '{"assessments":[]}').get("assessments", [])
        by_id = {value.get("item_id"): value for value in parsed}
        clean = [sanitize(by_id.get(item_id, {}), item_id) for item_id in batch.item_id]
        rows.extend(clean)
        with checkpoint.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"item_ids": batch.item_id.tolist(), "assessments": clean}, ensure_ascii=False) + "\n")
        prompt_tokens += int(response.usage.prompt_tokens or 0); completion_tokens += int(response.usage.completion_tokens or 0)
        print(f"Exposición [{min(start + batch_size, len(pending))}/{len(pending)}]", flush=True)
    result = pd.DataFrame(rows).drop_duplicates("item_id", keep="last")
    return result, {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens, "total_tokens": prompt_tokens + completion_tokens}


def calculate_item_pird(items: pd.DataFrame, exposure: pd.DataFrame, timeline: pd.DataFrame) -> pd.DataFrame:
    data = items.merge(exposure, on="item_id", validate="one_to_one").merge(
        timeline[["item_id", "recurrence_level", "persistence_level", "document_date", "temporal_role"]],
        on="item_id", validate="one_to_one",
    )
    outputs = []
    for row in data.itertuples():
        evidence_level = 5.0 if int(row.calibrated_evidence_sufficient) == 1 else None
        confidence_level = 1.0 + 4.0 * float(row.calibrated_confidence)
        severity = row.severity if pd.notna(row.severity) else None
        probability = row.probability if pd.notna(row.probability) else None
        result = calculate_pird(PIRDInputs(
            severity, probability, row.recurrence_level,
            row.persistence_level if pd.notna(row.persistence_level) else None,
            evidence_level, confidence_level,
        ))
        outputs.append({
            "item_id": row.item_id, "pird_status": result["score_status"],
            "pird": result["pird"], "pird_level": result["risk_level"],
            "exposure_index": result["exposure_index"], "reliability_index": result["reliability_index"],
            "pird_missing_components": ",".join(result["missing_components"]),
        })
    return data.merge(pd.DataFrame(outputs), on="item_id", validate="one_to_one")


def build_profile(scored: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    valid = scored[scored.pird_status == "CALCULADO"].copy()
    if valid.empty:
        return pd.DataFrame(), {"profile_status": "PENDIENTE", "reason": "No calculated PIRD values"}
    categories = valid.groupby("calibrated_category", as_index=False).agg(
        signal_count=("item_id", "size"), mean_pird=("pird", "mean"),
        median_pird=("pird", "median"), p90_pird=("pird", lambda x: x.quantile(0.90)),
        max_pird=("pird", "max"), persistent_signals=("persistence_level", lambda x: int((x >= 4).sum())),
    )
    categories["category_score"] = 0.70 * categories.mean_pird + 0.30 * categories.p90_pird
    categories["category_level"] = categories.category_score.map(risk_level)
    categories = categories.sort_values("category_score", ascending=False).reset_index(drop=True)
    global_score = round(float(0.70 * categories.category_score.mean() + 0.30 * categories.category_score.max()), 2)
    profile = {
        "profile_status": "CALCULADO",
        "signals_total": int(len(scored)), "signals_scored": int(len(valid)),
        "signals_pending": int(len(scored) - len(valid)),
        "global_pird": global_score, "global_level": risk_level(global_score),
        "global_formula": "70% mean of category scores + 30% maximum category score",
        "category_formula": "70% mean PIRD + 30% category P90",
        "top_categories": categories.head(3).calibrated_category.tolist(),
        "critical_signals": int((valid.pird_level == "CRITICO").sum()),
        "high_signals": int((valid.pird_level == "ALTO").sum()),
        "limitation": "Severity and probability are LLM rubric assessments without an independent human gold standard.",
    }
    return categories, profile


def run(items_csv: Path, timeline_csv: Path, output_dir: Path, batch_size: int = 10) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    items = pd.read_csv(items_csv); timeline = pd.read_csv(timeline_csv)
    exposure, usage = assess_exposure(items, output_dir, batch_size)
    scored = calculate_item_pird(items, exposure, timeline)
    categories, profile = build_profile(scored)
    scored.to_csv(output_dir / "pird_scored_signals_private.csv", index=False, encoding="utf-8-sig")
    categories.to_csv(output_dir / "pird_category_profile.csv", index=False, encoding="utf-8-sig")
    profile.update({"model": MODEL, **usage})
    (output_dir / "intelligent_risk_profile.json").write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    return profile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items-csv", required=True, type=Path)
    parser.add_argument("--timeline-csv", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--batch-size", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(run(args.items_csv, args.timeline_csv, args.output_dir, args.batch_size), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
