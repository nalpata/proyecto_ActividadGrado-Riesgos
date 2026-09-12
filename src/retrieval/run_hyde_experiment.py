"""Compara retrieval directo y HyDE usando BGE-M3.

El experimento utiliza los mismos chunks, embeddings, top-k y juez de
relevancia para ambos métodos. Registra métricas, tiempos, tokens y costo
estimado. Incluye checkpoints para poder reanudar una ejecución en Colab.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_LLM_MODEL = "gpt-4o-mini"
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-m3"
REQUIRED_CHUNK_COLUMNS = {
    "doc_id", "filename", "tipo_documento", "page", "chunk_id", "chunk_text", "embedding"
}
REQUIRED_QUESTION_COLUMNS = {
    "question_id", "question", "categoria", "respuesta_esperada"
}


def parse_json(raw: str | None) -> dict:
    if not raw:
        return {}
    text = raw.strip().replace("```json", "").replace("```", "").strip()
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            return {}
        try:
            value = json.loads(text[start:end + 1])
            return value if isinstance(value, dict) else {}
        except json.JSONDecodeError:
            return {}


def call_json(client, model: str, system: str, user: str, retries: int = 3):
    for attempt in range(1, retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            usage = response.usage
            return parse_json(response.choices[0].message.content), {
                "prompt_tokens": int(usage.prompt_tokens or 0),
                "completion_tokens": int(usage.completion_tokens or 0),
                "total_tokens": int(usage.total_tokens or 0),
            }
        except Exception:
            if attempt == retries:
                raise
            time.sleep(2 ** attempt)
    return {}, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def hyde_prompt(question: str, expected_answer: str) -> str:
    return f"""Redacta un fragmento documental hipotético que sería altamente relevante para responder la pregunta.

Contexto: documentos de interventoría y aseguramiento técnico de proyectos tecnológicos.
Pregunta: {question}
Tipo de respuesta esperada: {expected_answer}

Reglas:
- Escribe entre 90 y 160 palabras en español.
- Usa lenguaje de acta, informe o comunicación técnica.
- Incluye conceptos y relaciones que ayuden a la recuperación semántica.
- No inventes nombres propios, números de contrato, fechas ni cifras específicas.
- No respondas con una explicación de HyDE.

Devuelve solo JSON: {{"hypothetical_document": "texto"}}"""


def judge_prompt(question: str, expected_answer: str, candidates: list[dict]) -> str:
    compact = [
        {
            "chunk_id": item["chunk_id"],
            "filename": item["filename"],
            "chunk_text": str(item["chunk_text"])[:1400],
        }
        for item in candidates
    ]
    return f"""Evalúa si cada fragmento contiene evidencia útil para responder la pregunta.

Pregunta: {question}
Respuesta esperada (guía, no respuesta literal): {expected_answer}

Criterio:
- relevant=1 si el fragmento aporta evidencia directa, un ejemplo concreto o información necesaria para responder.
- relevant=0 si solo comparte palabras, es contexto genérico o no ayuda a responder.
- No penalices al fragmento por responder solo una parte de una pregunta transversal.
- Evalúa únicamente el contenido recibido. No uses conocimiento externo.
- confidence representa certeza sobre la decisión tomada, no probabilidad de relevancia.
  Un rechazo muy seguro debe tener confidence alto, por ejemplo 0.9.

Devuelve exactamente una decisión por chunk_id en JSON:
{{"judgments":[{{"chunk_id":"...","relevant":0,"confidence":0.0,"justification":"máximo 25 palabras"}}]}}

FRAGMENTOS:
{json.dumps(compact, ensure_ascii=False)}"""


def load_inputs(embeddings_path: Path, questions_path: Path):
    chunks = pd.read_parquet(embeddings_path).reset_index(drop=True)
    questions = pd.read_csv(questions_path).reset_index(drop=True)
    missing_chunks = REQUIRED_CHUNK_COLUMNS - set(chunks.columns)
    missing_questions = REQUIRED_QUESTION_COLUMNS - set(questions.columns)
    if missing_chunks:
        raise ValueError(f"Faltan columnas en embeddings: {sorted(missing_chunks)}")
    if missing_questions:
        raise ValueError(f"Faltan columnas en preguntas: {sorted(missing_questions)}")
    if questions["question_id"].duplicated().any():
        raise ValueError("question_id debe ser único.")
    matrix = np.vstack(chunks["embedding"].map(lambda value: np.asarray(value, dtype=np.float32)))
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    matrix = matrix / np.where(norms == 0, 1, norms)
    return chunks, questions, matrix


def generate_hyde_documents(client, questions, model: str, checkpoint: Path):
    cached = {}
    if checkpoint.exists():
        for line in checkpoint.read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            cached[item["question_id"]] = item
    records = []
    for number, row in questions.iterrows():
        question_id = str(row["question_id"])
        if question_id in cached:
            records.append(cached[question_id])
            continue
        started = time.perf_counter()
        value, usage = call_json(
            client, model,
            "Generas documentos hipotéticos para recuperación HyDE y respondes solo JSON válido.",
            hyde_prompt(str(row["question"]), str(row["respuesta_esperada"])),
        )
        document = str(value.get("hypothetical_document", "")).strip()
        if not document:
            raise RuntimeError(f"HyDE vacío para {question_id}")
        item = {
            "question_id": question_id,
            "hypothetical_document": document,
            "elapsed_seconds": round(time.perf_counter() - started, 4),
            **usage,
        }
        records.append(item)
        with checkpoint.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"HyDE [{number + 1}/{len(questions)}] {question_id}", flush=True)
    frame = pd.DataFrame(records).drop_duplicates("question_id", keep="last")
    usage_total = {
        key: int(pd.to_numeric(frame.get(key, 0), errors="coerce").fillna(0).sum())
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    }
    return frame, usage_total


def retrieve(method: str, query_texts: list[str], question_rows, model, chunks, matrix, top_k: int):
    query_matrix = model.encode(
        query_texts, batch_size=16, show_progress_bar=True,
        convert_to_numpy=True, normalize_embeddings=True,
    )
    records = []
    for position, (_, question) in enumerate(question_rows.iterrows()):
        scores = matrix @ query_matrix[position]
        top_indices = np.argsort(scores)[::-1][:top_k]
        for rank, chunk_index in enumerate(top_indices, start=1):
            chunk = chunks.iloc[chunk_index]
            records.append({
                "method": method,
                "question_id": question["question_id"],
                "question": question["question"],
                "categoria": question["categoria"],
                "rank": rank,
                "score": float(scores[chunk_index]),
                "chunk_id": chunk["chunk_id"],
                "doc_id": chunk["doc_id"],
                "filename": chunk["filename"],
                "tipo_documento": chunk["tipo_documento"],
                "page": chunk["page"],
                "chunk_text": chunk["chunk_text"],
            })
    return pd.DataFrame(records)


def judge_pool(client, pooled, questions, model: str, checkpoint: Path):
    cached = {}
    if checkpoint.exists():
        for line in checkpoint.read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            cached[(item["question_id"], item["chunk_id"])] = item
    records = []
    q_lookup = questions.set_index("question_id")
    for number, (question_id, group) in enumerate(pooled.groupby("question_id", sort=True), start=1):
        missing = [row for row in group.to_dict("records") if (question_id, row["chunk_id"]) not in cached]
        if missing:
            qrow = q_lookup.loc[question_id]
            value, usage = call_json(
                client, model,
                "Eres un juez independiente de relevancia documental. Responde solo JSON válido.",
                judge_prompt(str(qrow["question"]), str(qrow["respuesta_esperada"]), missing),
            )
            by_id = {str(item.get("chunk_id")): item for item in value.get("judgments", [])}
            for candidate_number, candidate in enumerate(missing):
                decision = by_id.get(str(candidate["chunk_id"]), {})
                relevant = 1 if str(decision.get("relevant", 0)).lower() in {"1", "true"} else 0
                try:
                    confidence = min(1.0, max(0.0, float(decision.get("confidence", 0))))
                except (TypeError, ValueError):
                    confidence = 0.0
                item = {
                    "question_id": question_id,
                    "chunk_id": candidate["chunk_id"],
                    "relevant": relevant,
                    "judge_confidence": confidence,
                    "judge_justification": str(decision.get("justification", "")).strip(),
                    # La llamada evalúa varios chunks; los tokens se guardan una
                    # sola vez para reconstruir el costo al reanudar.
                    "api_prompt_tokens": usage["prompt_tokens"] if candidate_number == 0 else 0,
                    "api_completion_tokens": usage["completion_tokens"] if candidate_number == 0 else 0,
                    "api_total_tokens": usage["total_tokens"] if candidate_number == 0 else 0,
                }
                cached[(question_id, candidate["chunk_id"])] = item
                with checkpoint.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(item, ensure_ascii=False) + "\n")
        records.extend(cached[(question_id, row["chunk_id"])] for row in group.to_dict("records"))
        print(f"Juez [{number}/{pooled['question_id'].nunique()}] {question_id}", flush=True)
    frame = pd.DataFrame(records).drop_duplicates(["question_id", "chunk_id"])
    def sum_column(name: str) -> int:
        if name not in frame.columns:
            return 0
        return int(pd.to_numeric(frame[name], errors="coerce").fillna(0).sum())

    usage_total = {
        "prompt_tokens": sum_column("api_prompt_tokens"),
        "completion_tokens": sum_column("api_completion_tokens"),
        "total_tokens": sum_column("api_total_tokens"),
    }
    return frame, usage_total


def calculate_metrics(results: pd.DataFrame):
    rows = []
    for (method, question_id), group in results.groupby(["method", "question_id"]):
        ordered = group.sort_values("rank")
        relevant = ordered[ordered["relevant"] == 1]
        row = {"method": method, "question_id": question_id, "categoria": group["categoria"].iloc[0]}
        for k in (1, 3, 5):
            top = ordered[ordered["rank"] <= k]
            row[f"precision_at_{k}"] = float(top["relevant"].mean()) if len(top) else 0.0
            row[f"hit_at_{k}"] = int(top["relevant"].sum() > 0)
        row["mrr"] = 0.0 if relevant.empty else 1.0 / int(relevant["rank"].min())
        rows.append(row)
    by_question = pd.DataFrame(rows)
    metric_columns = [f"precision_at_{k}" for k in (1, 3, 5)] + [f"hit_at_{k}" for k in (1, 3, 5)] + ["mrr"]
    by_method = by_question.groupby("method", as_index=False).agg(
        questions_evaluated=("question_id", "nunique"),
        **{column: (column, "mean") for column in metric_columns},
    )
    by_method[metric_columns] = by_method[metric_columns].round(4)
    return by_question, by_method


def make_blind_review(pooled: pd.DataFrame, judgments: pd.DataFrame, size: int = 30):
    key = pooled.merge(judgments, on=["question_id", "chunk_id"], how="left", validate="one_to_one")
    uncertain = key.sort_values("judge_confidence").head(size // 2)
    remainder = key.drop(uncertain.index).sample(
        n=min(size - len(uncertain), len(key) - len(uncertain)), random_state=42
    )
    key = pd.concat([uncertain, remainder]).drop_duplicates(["question_id", "chunk_id"]).head(size)
    blind = key[[
        "question_id", "question", "categoria", "chunk_id", "doc_id", "filename",
        "page", "chunk_text",
    ]].copy()
    blind["control_humano_relevante"] = ""
    blind["comentario_humano"] = ""
    return blind, key


def run(args):
    from openai import OpenAI
    from sentence_transformers import SentenceTransformer

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Falta OPENAI_API_KEY.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    started_total = time.perf_counter()
    chunks, questions, chunk_matrix = load_inputs(args.embeddings, args.questions)
    client = OpenAI()

    started = time.perf_counter()
    hyde, usage_hyde = generate_hyde_documents(
        client, questions, args.llm_model, args.output_dir / "hyde_checkpoint.jsonl"
    )
    hyde_seconds = time.perf_counter() - started

    embedding_model = SentenceTransformer(args.embedding_model)
    started = time.perf_counter()
    normal = retrieve(
        "normal", questions["question"].astype(str).tolist(), questions,
        embedding_model, chunks, chunk_matrix, args.top_k,
    )
    hyde_lookup = hyde.set_index("question_id")["hypothetical_document"]
    hyde_queries = questions["question_id"].map(hyde_lookup).tolist()
    hyde_results = retrieve(
        "hyde", hyde_queries, questions, embedding_model, chunks, chunk_matrix, args.top_k,
    )
    retrieval_seconds = time.perf_counter() - started
    results = pd.concat([normal, hyde_results], ignore_index=True)

    pooled = results.sort_values(["question_id", "method", "rank"]).drop_duplicates(
        ["question_id", "chunk_id"]
    )
    started = time.perf_counter()
    judgments, usage_judge = judge_pool(
        client, pooled, questions, args.llm_model, args.output_dir / "judge_checkpoint.jsonl"
    )
    judge_seconds = time.perf_counter() - started
    evaluated = results.merge(judgments, on=["question_id", "chunk_id"], how="left", validate="many_to_one")
    if evaluated["relevant"].isna().any():
        raise RuntimeError("Quedaron resultados sin juicio de relevancia.")
    by_question, by_method = calculate_metrics(evaluated)
    blind, key = make_blind_review(pooled, judgments, args.review_size)

    prompt_tokens = usage_hyde["prompt_tokens"] + usage_judge["prompt_tokens"]
    completion_tokens = usage_hyde["completion_tokens"] + usage_judge["completion_tokens"]
    estimated_cost = (
        prompt_tokens * args.input_cost_per_million
        + completion_tokens * args.output_cost_per_million
    ) / 1_000_000
    metadata = {
        "llm_model": args.llm_model,
        "embedding_model": args.embedding_model,
        "questions": int(len(questions)),
        "chunks": int(len(chunks)),
        "top_k": args.top_k,
        "pooled_unique_pairs": int(len(pooled)),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "input_cost_per_million_usd": args.input_cost_per_million,
        "output_cost_per_million_usd": args.output_cost_per_million,
        "estimated_cost_usd": round(estimated_cost, 6),
        "hyde_seconds": round(hyde_seconds, 3),
        "retrieval_seconds": round(retrieval_seconds, 3),
        "judge_seconds": round(judge_seconds, 3),
        "total_seconds": round(time.perf_counter() - started_total, 3),
        "relevance_protocol": "LLM-as-judge blind to retrieval method, with human audit sample",
    }
    hyde.to_csv(args.output_dir / "hyde_documents.csv", index=False, encoding="utf-8-sig")
    evaluated.to_csv(args.output_dir / "retrieval_results_evaluated.csv", index=False, encoding="utf-8-sig")
    by_question.to_csv(args.output_dir / "metrics_by_question.csv", index=False, encoding="utf-8-sig")
    by_method.to_csv(args.output_dir / "metrics_by_method.csv", index=False, encoding="utf-8-sig")
    blind.to_excel(args.output_dir / "human_audit_sample_blind.xlsx", index=False)
    key.to_excel(args.output_dir / "human_audit_sample_key.xlsx", index=False)
    (args.output_dir / "experiment_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"metrics": by_method.to_dict("records"), "metadata": metadata}, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--embeddings", required=True, type=Path)
    parser.add_argument("--questions", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--review-size", type=int, default=30)
    parser.add_argument("--llm-model", default=DEFAULT_LLM_MODEL)
    parser.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    parser.add_argument("--input-cost-per-million", type=float, default=0.15)
    parser.add_argument("--output-cost-per-million", type=float, default=0.60)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
