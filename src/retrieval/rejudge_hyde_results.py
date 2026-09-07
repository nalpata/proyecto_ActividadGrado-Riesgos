"""Reevalúa el pool normal/HyDE con un criterio de relevancia calibrado."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import pandas as pd

from src.retrieval.run_hyde_experiment import call_json, calculate_metrics


MODEL = "gpt-4o-mini"


def calibrated_prompt(question: str, expected_answer: str, candidates: list[dict]) -> str:
    compact = [
        {
            "chunk_id": row["chunk_id"],
            "filename": row["filename"],
            "chunk_text": str(row["chunk_text"])[:1600],
        }
        for row in candidates
    ]
    return f"""Evalúa si cada fragmento ayuda a responder la pregunta en un sistema RAG de vigilancia documental.

Pregunta: {question}
Respuesta esperada: {expected_answer}

Definición calibrada de relevancia:
- relevant=1 cuando el fragmento aporta evidencia directa, evidencia parcial, un antecedente,
  contexto documental útil, una condición relacionada o un ejemplo que pueda formar parte de la respuesta.
- No exijas que el fragmento responda por sí solo toda la pregunta.
- Para preguntas transversales, un fragmento que describe un evento, situación o contexto relacionado es relevante.
- relevant=0 únicamente cuando el contenido es ajeno a la pregunta o la coincidencia es puramente superficial.
- Evalúa el aporte para recuperación, no la calidad de redacción ni si contiene todos los detalles esperados.
- confidence expresa certeza sobre la decisión tomada. Un rechazo seguro también debe tener confianza alta.

Devuelve exactamente una decisión por chunk_id:
{{"judgments":[{{"chunk_id":"...","relevant":0,"confidence":0.9,"justification":"máximo 25 palabras"}}]}}

FRAGMENTOS:
{json.dumps(compact, ensure_ascii=False)}"""


def run(results_path: Path, questions_path: Path, output_dir: Path, model: str = MODEL):
    from openai import OpenAI

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Falta OPENAI_API_KEY.")
    results = pd.read_csv(results_path)
    questions = pd.read_csv(questions_path)
    required = {"method", "question_id", "question", "categoria", "rank", "chunk_id", "chunk_text", "filename"}
    missing = required - set(results.columns)
    if missing:
        raise ValueError(f"Faltan columnas en resultados: {sorted(missing)}")
    pool = results.sort_values(["question_id", "method", "rank"]).drop_duplicates(
        ["question_id", "chunk_id"]
    )
    q_lookup = questions.set_index("question_id")
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = output_dir / "judge_v2_checkpoint.jsonl"
    cached = {}
    if checkpoint.exists():
        for line in checkpoint.read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            cached[(item["question_id"], item["chunk_id"])] = item
    client = OpenAI()
    started = time.perf_counter()
    for number, (question_id, group) in enumerate(pool.groupby("question_id", sort=True), start=1):
        missing_rows = [
            row for row in group.to_dict("records")
            if (question_id, row["chunk_id"]) not in cached
        ]
        if missing_rows:
            qrow = q_lookup.loc[question_id]
            value, usage = call_json(
                client,
                model,
                "Eres un juez calibrado de relevancia para RAG. Responde únicamente JSON válido.",
                calibrated_prompt(str(qrow["question"]), str(qrow["respuesta_esperada"]), missing_rows),
            )
            by_id = {str(item.get("chunk_id")): item for item in value.get("judgments", [])}
            for index, candidate in enumerate(missing_rows):
                decision = by_id.get(str(candidate["chunk_id"]), {})
                relevant = 1 if str(decision.get("relevant", 0)).lower() in {"1", "true"} else 0
                try:
                    confidence = min(1.0, max(0.0, float(decision.get("confidence", 0))))
                except (TypeError, ValueError):
                    confidence = 0.0
                item = {
                    "question_id": question_id,
                    "chunk_id": candidate["chunk_id"],
                    "relevant_v2": relevant,
                    "judge_v2_confidence": confidence,
                    "judge_v2_justification": str(decision.get("justification", "")).strip(),
                    "api_prompt_tokens": usage["prompt_tokens"] if index == 0 else 0,
                    "api_completion_tokens": usage["completion_tokens"] if index == 0 else 0,
                }
                cached[(question_id, candidate["chunk_id"])] = item
                with checkpoint.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"Juez v2 [{number}/{pool['question_id'].nunique()}] {question_id}", flush=True)

    judgments = pd.DataFrame(cached.values()).drop_duplicates(["question_id", "chunk_id"])
    evaluated = results.drop(
        columns=[c for c in ["relevant", "judge_confidence", "judge_justification",
                             "api_prompt_tokens", "api_completion_tokens", "api_total_tokens"]
                 if c in results.columns]
    ).merge(judgments, on=["question_id", "chunk_id"], how="left", validate="many_to_one")
    evaluated["relevant"] = evaluated["relevant_v2"].astype(int)
    by_question, by_method = calculate_metrics(evaluated)
    prompt_tokens = int(judgments["api_prompt_tokens"].sum())
    completion_tokens = int(judgments["api_completion_tokens"].sum())
    metadata = {
        "judge_model": model,
        "protocol": "calibrated relevance v2 based on human audit definition",
        "questions": int(pool["question_id"].nunique()),
        "pooled_unique_pairs": int(len(pool)),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    evaluated.to_csv(output_dir / "retrieval_results_rejudged_v2.csv", index=False, encoding="utf-8-sig")
    by_question.to_csv(output_dir / "metrics_by_question_v2.csv", index=False, encoding="utf-8-sig")
    by_method.to_csv(output_dir / "metrics_by_method_v2.csv", index=False, encoding="utf-8-sig")
    (output_dir / "rejudge_v2_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"metrics": by_method.to_dict("records"), "metadata": metadata}, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--questions", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--model", default=MODEL)
    args = parser.parse_args()
    run(args.results, args.questions, args.output_dir, args.model)


if __name__ == "__main__":
    main()
