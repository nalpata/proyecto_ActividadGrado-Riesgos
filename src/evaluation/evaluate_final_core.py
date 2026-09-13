"""Compara el prompt mejorado y la validación final sobre el mismo gold humano."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def binary_metrics(actual, predicted) -> dict:
    actual = pd.Series(actual).astype(int)
    predicted = pd.Series(predicted).astype(int)
    tp = int(((actual == 1) & (predicted == 1)).sum())
    tn = int(((actual == 0) & (predicted == 0)).sum())
    fp = int(((actual == 0) & (predicted == 1)).sum())
    fn = int(((actual == 1) & (predicted == 0)).sum())
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    specificity = tn / (tn + fp) if tn + fp else 0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
    return {
        "n": int(len(actual)), "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "precision": round(precision, 4), "recall": round(recall, 4),
        "f1": round(f1, 4), "accuracy": round((tp + tn) / len(actual), 4),
        "specificity": round(specificity, 4),
    }


def load_gold(audit_path: Path) -> pd.DataFrame:
    audit = pd.read_excel(audit_path, sheet_name="Auditoria")
    required = ["item_id", "requiere_vigilancia"]
    return audit.dropna(subset=required)[required].rename(
        columns={"requiere_vigilancia": "human_watch"}
    ).assign(human_watch=lambda x: x.human_watch.astype(int))


def evaluate(items_path: Path, audit_path: Path, loo_path: Path) -> tuple[pd.DataFrame, dict]:
    items = pd.read_csv(items_path)
    gold = load_gold(audit_path)
    loo = pd.read_csv(loo_path)
    prompt = gold.merge(
        items[["item_id", "surveillance_candidate"]], on="item_id", validate="one_to_one"
    )
    validated = gold.merge(
        loo[["item_id", "calibrated_watch"]], on="item_id", validate="one_to_one"
    )
    if len(prompt) != len(gold) or len(validated) != len(gold):
        raise ValueError("Las configuraciones no cubren el mismo conjunto gold")

    prompt_metrics = binary_metrics(prompt.human_watch, prompt.surveillance_candidate)
    validated_metrics = binary_metrics(validated.human_watch, validated.calibrated_watch)
    rows = [
        {"configuration":"extraccion_inicial_historica", "comparable_sample":False,
         "n":None, "tp":None, "tn":None, "fp":None, "fn":None,
         "precision":0.646, "recall":None, "f1":None, "accuracy":None, "specificity":None,
         "note":"Referencia histórica sin muestra ni matriz de confusión reproducible"},
        {"configuration":"prompt_mejorado_v2", "comparable_sample":True, **prompt_metrics,
         "note":"Evaluado sobre las 29 etiquetas humanas finales"},
        {"configuration":"extraccion_mas_validacion", "comparable_sample":True, **validated_metrics,
         "note":"Evaluación leave-one-out sobre las mismas 29 etiquetas"},
    ]
    comparison = pd.DataFrame(rows)
    summary = {
        "paired_sample_size": int(len(gold)),
        "human_positive": int(gold.human_watch.sum()),
        "human_negative": int((gold.human_watch == 0).sum()),
        "selected_risk_configuration": "extraccion_mas_validacion",
        "selection_basis": "Mayor F1 y recall en la comparación pareada, con igual precision",
        "additional_true_positives_vs_prompt_v2": validated_metrics["tp"] - prompt_metrics["tp"],
        "additional_false_positives_vs_prompt_v2": validated_metrics["fp"] - prompt_metrics["fp"],
        "final_retrieval_configuration": {
            "query": "original",
            "embedding_model": "BAAI/bge-m3",
            "chunking": "recursive_character_splitter",
            "hyde": False,
            "reranking": False,
        },
        "final_risk_configuration": {
            "extraction": "documentary_extraction_v2",
            "classification": "calibrated_leave_one_out_validated",
            "final_gate": "watch=1, evidence_sufficient=1, verified_evidence_present",
        },
        "historical_baseline_limitation": "Precision 0.646 conservada solo como referencia; Recall y F1 no son calculables",
    }
    return comparison, summary


def run(items: Path, audit: Path, loo: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    comparison, summary = evaluate(items, audit, loo)
    comparison.to_csv(output_dir / "core_configuration_comparison.csv", index=False, encoding="utf-8-sig")
    (output_dir / "final_core_selection.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", required=True, type=Path)
    parser.add_argument("--audit", required=True, type=Path)
    parser.add_argument("--loo", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.items, args.audit, args.loo, args.output_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
