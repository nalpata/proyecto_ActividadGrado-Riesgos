"""Calibra la clasificación documental con etiquetas humanas y evaluación leave-one-out."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import pandas as pd

from src.risk.extract_documentary_items import CATEGORIES, ITEM_TYPES, MODEL


SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "calibrated_documentary_classification", "strict": True,
        "schema": {
            "type": "object", "properties": {"classifications": {"type": "array", "items": {
                "type": "object", "properties": {
                    "item_id": {"type": "string"},
                    "item_type": {"type": "string", "enum": ITEM_TYPES},
                    "surveillance_candidate": {"type": "integer", "enum": [0, 1]},
                    "evidence_sufficient": {"type": "integer", "enum": [0, 1]},
                    "risk_category": {"type": "string", "enum": CATEGORIES},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "justification": {"type": "string"},
                },
                "required": ["item_id", "item_type", "surveillance_candidate", "evidence_sufficient",
                             "risk_category", "confidence", "justification"],
                "additionalProperties": False,
            }}}, "required": ["classifications"], "additionalProperties": False,
        },
    },
}


def human_examples(audit: pd.DataFrame, items: pd.DataFrame) -> pd.DataFrame:
    audit = audit.rename(columns={
        "tipo_humano": "human_type", "requiere_vigilancia": "human_watch",
        "evidencia_suficiente": "human_evidence", "categoria_humana": "human_category",
    })
    required = ["item_id", "human_type", "human_watch", "human_evidence", "human_category"]
    complete = audit.dropna(subset=required).copy()
    complete["human_watch"] = complete.human_watch.astype(int)
    complete["human_evidence"] = complete.human_evidence.astype(int)
    return complete[required].merge(
        items[["item_id", "title", "statement", "evidence_quote", "source_chunk_id"]],
        on="item_id", validate="one_to_one"
    )


def compact_example(row) -> dict:
    return {
        "title": row.title, "statement": row.statement, "evidence": row.evidence_quote,
        "correct_type": row.human_type, "correct_watch": int(row.human_watch),
        "correct_evidence": int(row.human_evidence), "correct_category": row.human_category,
    }


def build_prompt(targets: pd.DataFrame, examples: pd.DataFrame, chunks: dict) -> str:
    training = [compact_example(row) for row in examples.itertuples()]
    items = []
    for row in targets.itertuples():
        items.append({
            "item_id": row.item_id, "title": row.title, "statement": row.statement,
            "evidence": row.evidence_quote,
            "context": str(chunks.get(row.source_chunk_id, ""))[:1400],
        })
    return f"""Clasifica elementos documentales siguiendo el criterio humano mostrado en los ejemplos.

DEFINICIONES:
- RIESGO: posibilidad o exposición futura todavía abierta.
- HECHO_OCURRIDO: evento o desviación que ya sucedió.
- COMPROMISO: obligación, entrega o actuación prometida.
- ACCION_CORRECTIVA: medida para corregir o mitigar.
- HALLAZGO: deficiencia o condición constatada.
- INFORMACION_CONTEXTUAL: dato neutral, administrativo, cerrado o sin valor de vigilancia.

REGLAS:
- Aprende el límite entre clases y vigilancia de los ejemplos humanos; no copies su texto.
- Vigilancia 1 solo si el elemento merece seguimiento según la evidencia y el contexto.
- Evidencia suficiente 1 solo si la cita demuestra toda la declaración.
- No aplica se usa únicamente para información contextual.
- Devuelve exactamente una clasificación por item_id, sin omitir ni agregar identificadores.

EJEMPLOS HUMANOS:
{json.dumps(training, ensure_ascii=False)}

ELEMENTOS A CLASIFICAR:
{json.dumps(items, ensure_ascii=False)}"""


def call(client, prompt: str):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role":"system","content":"Clasifica según el criterio humano y responde JSON estricto."},
                  {"role":"user","content":prompt}],
        temperature=0.0, response_format=SCHEMA,
    )
    parsed = json.loads(response.choices[0].message.content or '{"classifications":[]}')
    return parsed.get("classifications", []), response.usage


def sanitize(item: dict, expected_id: str) -> dict:
    typ = item.get("item_type") if item.get("item_type") in ITEM_TYPES else "INFORMACION_CONTEXTUAL"
    cat = item.get("risk_category") if item.get("risk_category") in CATEGORIES else "Otro"
    if typ == "INFORMACION_CONTEXTUAL": cat = "No aplica"
    elif cat == "No aplica": cat = "Otro"
    evidence = 1 if item.get("evidence_sufficient") in {1, True} else 0
    watch = 1 if item.get("surveillance_candidate") in {1, True} else 0
    if not evidence: watch = 0
    return {"item_id": expected_id, "calibrated_type": typ, "calibrated_watch": watch,
            "calibrated_evidence_sufficient": evidence, "calibrated_category": cat,
            "calibrated_confidence": float(item.get("confidence", 0)),
            "calibrated_justification": str(item.get("justification", ""))}


def metrics(gold: pd.DataFrame, predictions: pd.DataFrame) -> dict:
    from sklearn.metrics import accuracy_score, cohen_kappa_score, precision_recall_fscore_support
    data = gold.merge(predictions, on="item_id", validate="one_to_one")
    precision, recall, f1, _ = precision_recall_fscore_support(
        data.human_watch.astype(int), data.calibrated_watch.astype(int), average="binary", zero_division=0
    )
    return {
        "evaluated": len(data),
        "type_accuracy": round(accuracy_score(data.human_type, data.calibrated_type), 4),
        "type_kappa": round(cohen_kappa_score(data.human_type, data.calibrated_type), 4),
        "watch_precision": round(precision, 4), "watch_recall": round(recall, 4),
        "watch_f1": round(f1, 4),
        "watch_accuracy": round(accuracy_score(data.human_watch.astype(int), data.calibrated_watch.astype(int)), 4),
        "evidence_accuracy": round(accuracy_score(data.human_evidence.astype(int), data.calibrated_evidence_sufficient.astype(int)), 4),
        "category_accuracy": round(accuracy_score(data.human_category, data.calibrated_category), 4),
    }


def run(items_path: Path, audit_path: Path, chunks_path: Path, output_dir: Path, batch_size: int = 10):
    from openai import OpenAI
    if not os.getenv("OPENAI_API_KEY"): raise RuntimeError("Falta OPENAI_API_KEY")
    output_dir.mkdir(parents=True, exist_ok=True)
    items = pd.read_csv(items_path)
    audit = pd.read_excel(audit_path, sheet_name="Auditoria")
    chunks_df = pd.read_parquet(chunks_path)
    chunks = chunks_df.set_index("chunk_id").chunk_text.to_dict()
    gold = human_examples(audit, items)
    client = OpenAI()
    loo_predictions = []
    prompt_tokens = completion_tokens = 0
    for pos, row in enumerate(gold.itertuples(), 1):
        target = items[items.item_id == row.item_id]
        training = gold[gold.item_id != row.item_id]
        returned, usage = call(client, build_prompt(target, training, chunks))
        by_id = {x.get("item_id"): x for x in returned}
        loo_predictions.append(sanitize(by_id.get(row.item_id, {}), row.item_id))
        prompt_tokens += int(usage.prompt_tokens or 0); completion_tokens += int(usage.completion_tokens or 0)
        print(f"LOO [{pos}/{len(gold)}] {row.item_id}", flush=True)
    loo = pd.DataFrame(loo_predictions)
    result_metrics = metrics(gold, loo)

    checkpoint = output_dir / "calibrated_classification_checkpoint.jsonl"
    completed, predictions = set(), []
    if checkpoint.exists():
        for line in checkpoint.read_text(encoding="utf-8").splitlines():
            record = json.loads(line); completed.update(record["item_ids"]); predictions.extend(record["predictions"])
    pending = items[~items.item_id.isin(completed)].copy()
    for start in range(0, len(pending), batch_size):
        batch = pending.iloc[start:start+batch_size]
        returned, usage = call(client, build_prompt(batch, gold, chunks))
        by_id = {x.get("item_id"): x for x in returned}
        clean = [sanitize(by_id.get(item_id, {}), item_id) for item_id in batch.item_id]
        predictions.extend(clean)
        record = {"item_ids": batch.item_id.tolist(), "predictions": clean}
        with checkpoint.open("a", encoding="utf-8") as handle: handle.write(json.dumps(record, ensure_ascii=False)+"\n")
        prompt_tokens += int(usage.prompt_tokens or 0); completion_tokens += int(usage.completion_tokens or 0)
        print(f"Clasificación [{min(start+batch_size,len(pending))}/{len(pending)}]", flush=True)
    pred = pd.DataFrame(predictions).drop_duplicates("item_id", keep="last")
    final = items.merge(pred, on="item_id", validate="one_to_one")
    final.to_csv(output_dir/"documentary_items_calibrated.csv", index=False, encoding="utf-8-sig")
    final[final.calibrated_watch == 1].to_csv(output_dir/"surveillance_candidates_calibrated.csv", index=False, encoding="utf-8-sig")
    loo.to_csv(output_dir/"leave_one_out_predictions.csv", index=False, encoding="utf-8-sig")
    result_metrics.update({"human_examples":len(gold), "items_classified":len(final),
                           "prompt_tokens":prompt_tokens, "completion_tokens":completion_tokens,
                           "total_tokens":prompt_tokens+completion_tokens})
    (output_dir/"calibrated_classifier_metrics.json").write_text(json.dumps(result_metrics,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result_metrics,ensure_ascii=False,indent=2))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--items",required=True,type=Path); p.add_argument("--audit",required=True,type=Path)
    p.add_argument("--chunks",required=True,type=Path); p.add_argument("--output-dir",required=True,type=Path)
    p.add_argument("--batch-size",type=int,default=10); a=p.parse_args()
    run(a.items,a.audit,a.chunks,a.output_dir,a.batch_size)


if __name__=="__main__": main()
