"""Compara retrieval normal/HyDE con y sin reranking multilingüe."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd


RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
EMBEDDING_MODEL = "BAAI/bge-m3"


def normalize_matrix(values) -> np.ndarray:
    matrix = np.vstack([np.asarray(v, dtype=np.float32) for v in values])
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.where(norms == 0, 1, norms)


def top_candidates(query_embedding: np.ndarray, matrix: np.ndarray, top_n: int) -> tuple[np.ndarray, np.ndarray]:
    scores = matrix @ query_embedding
    indices = np.argsort(scores)[::-1][:top_n]
    return indices, scores[indices]


def rank_by_scores(frame: pd.DataFrame, scores, top_k: int) -> pd.DataFrame:
    ranked = frame.copy()
    ranked["reranker_score"] = np.asarray(scores, dtype=float)
    ranked = ranked.sort_values("reranker_score", ascending=False).head(top_k).reset_index(drop=True)
    ranked["rank"] = np.arange(1, len(ranked) + 1)
    return ranked


def run(embeddings_path: Path, questions_path: Path, hyde_path: Path, output_dir: Path,
        top_n: int = 20, top_k: int = 5, reranker_model: str = RERANKER_MODEL):
    from sentence_transformers import SentenceTransformer
    from FlagEmbedding import FlagReranker

    started = time.perf_counter()
    chunks = pd.read_parquet(embeddings_path).reset_index(drop=True)
    questions = pd.read_csv(questions_path)
    hyde = pd.read_csv(hyde_path)
    required = {"doc_id", "filename", "tipo_documento", "page", "chunk_id", "chunk_text", "embedding"}
    missing = required - set(chunks.columns)
    if missing:
        raise ValueError(f"Faltan columnas en embeddings: {sorted(missing)}")
    questions = questions.merge(hyde[["question_id", "hypothetical_document"]], on="question_id", validate="one_to_one")
    matrix = normalize_matrix(chunks["embedding"])

    embedder = SentenceTransformer(EMBEDDING_MODEL)
    reranker = FlagReranker(reranker_model, use_fp16=True)
    original_queries = questions["question"].astype(str).tolist()
    hyde_queries = questions["hypothetical_document"].astype(str).tolist()
    query_vectors = {
        "normal": embedder.encode(original_queries, normalize_embeddings=True, convert_to_numpy=True),
        "hyde": embedder.encode(hyde_queries, normalize_embeddings=True, convert_to_numpy=True),
    }

    rows = []
    for qpos, qrow in questions.reset_index(drop=True).iterrows():
        for query_method in ("normal", "hyde"):
            indices, scores = top_candidates(query_vectors[query_method][qpos], matrix, top_n)
            candidates = chunks.iloc[indices].copy().reset_index(drop=True)
            candidates["retriever_rank"] = np.arange(1, len(candidates) + 1)
            candidates["retriever_score"] = scores

            base = candidates.head(top_k).copy()
            base["rank"] = np.arange(1, len(base) + 1)
            base["reranker_score"] = np.nan
            base["method"] = query_method

            pairs = [[str(qrow["question"]), str(text)] for text in candidates["chunk_text"]]
            reranked = rank_by_scores(candidates, reranker.compute_score(pairs, normalize=True), top_k)
            reranked["method"] = f"{query_method}_rerank"

            for frame in (base, reranked):
                frame["question_id"] = qrow["question_id"]
                frame["question"] = qrow["question"]
                frame["categoria"] = qrow["categoria"]
                rows.append(frame)
        print(f"Reranking [{qpos + 1}/{len(questions)}] {qrow['question_id']}", flush=True)

    results = pd.concat(rows, ignore_index=True)
    cols = ["method", "question_id", "question", "categoria", "rank", "retriever_rank",
            "retriever_score", "reranker_score", "doc_id", "filename", "tipo_documento",
            "page", "chunk_id", "chunk_text"]
    results = results[cols]
    output_dir.mkdir(parents=True, exist_ok=True)
    results.to_csv(output_dir / "reranking_results.csv", index=False, encoding="utf-8-sig")
    metadata = {
        "embedding_model": EMBEDDING_MODEL, "reranker_model": reranker_model,
        "questions": int(len(questions)), "chunks": int(len(chunks)), "top_n": top_n,
        "top_k": top_k, "configurations": ["normal", "hyde", "normal_rerank", "hyde_rerank"],
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    (output_dir / "reranking_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--embeddings", required=True, type=Path)
    parser.add_argument("--questions", required=True, type=Path)
    parser.add_argument("--hyde", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--reranker-model", default=RERANKER_MODEL)
    args = parser.parse_args()
    run(args.embeddings, args.questions, args.hyde, args.output_dir, args.top_n, args.top_k, args.reranker_model)


if __name__ == "__main__":
    main()
