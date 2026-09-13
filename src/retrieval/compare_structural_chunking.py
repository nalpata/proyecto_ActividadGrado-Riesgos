"""Recupera Top-k con BGE-M3 sobre chunks estructurales y combina el baseline."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def retrieve(chunks: pd.DataFrame, questions: pd.DataFrame, model, top_k: int = 5):
    chunk_vectors = model.encode(chunks.chunk_text.astype(str).tolist(), normalize_embeddings=True,
                                 convert_to_numpy=True, show_progress_bar=True)
    question_vectors = model.encode(questions.question.astype(str).tolist(), normalize_embeddings=True,
                                    convert_to_numpy=True)
    rows = []
    for qpos, question in questions.reset_index(drop=True).iterrows():
        scores = chunk_vectors @ question_vectors[qpos]
        indices = np.argsort(scores)[::-1][:top_k]
        for rank, idx in enumerate(indices, 1):
            chunk = chunks.iloc[idx]
            rows.append({
                "method": "normal_structural", "question_id": question.question_id,
                "question": question.question, "categoria": question.categoria, "rank": rank,
                "retriever_rank": rank, "retriever_score": float(scores[idx]),
                "reranker_score": np.nan, "doc_id": chunk.doc_id, "filename": chunk.filename,
                "tipo_documento": chunk.tipo_documento, "page": chunk.page,
                "chunk_id": chunk.chunk_id, "chunk_text": chunk.chunk_text,
            })
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--structural-chunks", required=True, type=Path)
    parser.add_argument("--baseline-results", required=True, type=Path)
    parser.add_argument("--questions", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    from sentence_transformers import SentenceTransformer
    chunks = pd.read_csv(args.structural_chunks)
    questions = pd.read_csv(args.questions)
    model = SentenceTransformer("BAAI/bge-m3")
    structural = retrieve(chunks, questions, model, args.top_k)
    baseline = pd.read_csv(args.baseline_results).rename(columns={"score": "retriever_score"})
    baseline["method"] = "normal_current"
    baseline["retriever_rank"] = baseline["rank"]
    baseline["reranker_score"] = np.nan
    cols = structural.columns.tolist()
    combined = pd.concat([baseline[cols], structural[cols]], ignore_index=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    combined.to_csv(args.output_dir / "chunking_comparison_results.csv", index=False, encoding="utf-8-sig")
    print({"rows": len(combined), "methods": combined.method.value_counts().to_dict()})


if __name__ == "__main__":
    main()
