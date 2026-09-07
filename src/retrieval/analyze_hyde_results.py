"""Resume diferencias entre retrieval normal y HyDE por pregunta."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


METRICS = [
    "precision_at_1", "precision_at_3", "precision_at_5",
    "hit_at_1", "hit_at_3", "hit_at_5", "mrr",
]


def analyze(metrics_path: Path, output_dir: Path, repetitions: int = 20_000, seed: int = 42):
    data = pd.read_csv(metrics_path)
    expected_methods = {"normal", "hyde"}
    if set(data["method"]) != expected_methods:
        raise ValueError(f"Se esperaban métodos {expected_methods}.")
    wide = data.pivot(index="question_id", columns="method", values=METRICS)
    rng = np.random.default_rng(seed)
    records = []
    for metric in METRICS:
        differences = (wide[metric]["hyde"] - wide[metric]["normal"]).to_numpy()
        bootstrap = np.array([
            rng.choice(differences, len(differences), replace=True).mean()
            for _ in range(repetitions)
        ])
        records.append({
            "metric": metric,
            "normal_mean": round(float(wide[metric]["normal"].mean()), 4),
            "hyde_mean": round(float(wide[metric]["hyde"].mean()), 4),
            "mean_delta_hyde_minus_normal": round(float(differences.mean()), 4),
            "questions_improved": int((differences > 0).sum()),
            "questions_equal": int((differences == 0).sum()),
            "questions_worse": int((differences < 0).sum()),
            "bootstrap_ci_95_low": round(float(np.quantile(bootstrap, 0.025)), 4),
            "bootstrap_ci_95_high": round(float(np.quantile(bootstrap, 0.975)), 4),
        })
    comparison = pd.DataFrame(records)
    primary = comparison.set_index("metric")
    recommend_hyde = bool(
        primary.loc["mrr", "mean_delta_hyde_minus_normal"] > 0
        and primary.loc["hit_at_3", "mean_delta_hyde_minus_normal"] >= 0
        and primary.loc["precision_at_5", "mean_delta_hyde_minus_normal"] >= -0.02
    )
    conclusion = {
        "questions": int(data["question_id"].nunique()),
        "recommended_method": "hyde" if recommend_hyde else "normal",
        "recommend_hyde": recommend_hyde,
        "selection_rule": "improve MRR and Hit@3, with Precision@5 deterioration no greater than 0.02",
        "finding": (
            "HyDE no supera el retrieval normal con BGE-M3 en este corpus."
            if not recommend_hyde else
            "HyDE supera el retrieval normal bajo la regla definida."
        ),
        "limitations": [
            "La relevancia fue etiquetada inicialmente mediante LLM-as-judge.",
            "La confianza del juez en esta corrida no es interpretable: varios rechazos recibieron confianza 0.",
            "Se requiere consolidar la muestra ciega de auditoría humana antes del cierre definitivo.",
            "Los intervalos bootstrap describen variabilidad entre 20 preguntas; no prueban generalización a otros corpus.",
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(output_dir / "comparison_with_bootstrap.csv", index=False, encoding="utf-8-sig")
    (output_dir / "experiment_conclusion.json").write_text(
        json.dumps(conclusion, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return comparison, conclusion


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics-by-question", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    comparison, conclusion = analyze(args.metrics_by_question, args.output_dir)
    print(comparison.to_string(index=False))
    print(json.dumps(conclusion, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
