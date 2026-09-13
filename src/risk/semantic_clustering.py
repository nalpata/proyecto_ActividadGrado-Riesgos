"""Clustering semántico reproducible de señales documentales y recurrencia PIRD."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    normalized_mutual_info_score,
    silhouette_score,
)
from sklearn.preprocessing import normalize


DEFAULT_K_RANGE = range(2, 13)
SEEDS = (17, 29, 42, 71, 101)
SPANISH_STOP_WORDS = {
    "a", "al", "algo", "ante", "bajo", "cada", "como", "con", "contra", "cual", "cuando",
    "de", "del", "desde", "donde", "durante", "e", "el", "ella", "ellas", "ellos", "en",
    "entre", "era", "es", "esa", "ese", "eso", "esta", "este", "esto", "fue", "ha", "hacia",
    "hasta", "hay", "la", "las", "le", "lo", "los", "más", "mediante", "muy", "ni", "no",
    "o", "para", "pero", "por", "porque", "que", "se", "según", "ser", "si", "sin", "sobre",
    "son", "su", "sus", "también", "un", "una", "uno", "y", "ya",
}


def recurrence_level(other_document_count: int) -> int:
    """Rúbrica 1–5 basada en otros documentos con una señal semánticamente cercana."""
    if other_document_count < 0:
        raise ValueError("other_document_count no puede ser negativo")
    if other_document_count == 0:
        return 1
    if other_document_count == 1:
        return 2
    if other_document_count <= 3:
        return 3
    if other_document_count <= 6:
        return 4
    return 5


def semantic_recurrence(embeddings: np.ndarray, source_docs: pd.Series, threshold: float = 0.70) -> tuple[np.ndarray, np.ndarray]:
    """Cuenta documentos distintos con al menos un vecino cuya similitud supera el umbral."""
    x = normalize(np.asarray(embeddings), norm="l2")
    similarities = x @ x.T
    docs = source_docs.astype(str).to_numpy()
    counts = []
    for row in range(len(x)):
        mask = (similarities[row] >= threshold) & (docs != docs[row])
        counts.append(len(set(docs[mask])))
    counts = np.asarray(counts, dtype=int)
    levels = np.asarray([recurrence_level(value) for value in counts], dtype=int)
    return counts, levels


def evaluate_k(embeddings: np.ndarray, k_values=DEFAULT_K_RANGE) -> pd.DataFrame:
    """Evalúa candidatos k con separación, compacidad y estabilidad."""
    x = normalize(np.asarray(embeddings), norm="l2")
    rows = []
    for k in [k for k in k_values if 1 < k < len(x)]:
        labels_by_seed = []
        inertias = []
        for seed in SEEDS:
            model = KMeans(n_clusters=k, random_state=seed, n_init=20)
            labels_by_seed.append(model.fit_predict(x))
            inertias.append(model.inertia_)
        reference = labels_by_seed[2]
        stability = float(np.mean([adjusted_rand_score(reference, labels) for labels in labels_by_seed if labels is not reference]))
        rows.append({
            "k": k,
            "silhouette_cosine": silhouette_score(x, reference, metric="cosine"),
            "calinski_harabasz": calinski_harabasz_score(x, reference),
            "davies_bouldin": davies_bouldin_score(x, reference),
            "stability_ari": stability,
            "mean_inertia": float(np.mean(inertias)),
        })
    metrics = pd.DataFrame(rows)
    if metrics.empty:
        raise ValueError("No hay suficientes observaciones para evaluar k")
    for column, ascending in [
        ("silhouette_cosine", False), ("calinski_harabasz", False),
        ("davies_bouldin", True), ("stability_ari", False),
    ]:
        metrics[f"rank_{column}"] = metrics[column].rank(ascending=ascending, method="min")
    rank_columns = [c for c in metrics if c.startswith("rank_")]
    metrics["mean_rank"] = metrics[rank_columns].mean(axis=1)
    metrics["selected"] = metrics["mean_rank"].eq(metrics["mean_rank"].min())
    return metrics.sort_values(["mean_rank", "k"]).reset_index(drop=True)


def cluster_keywords(texts: pd.Series, labels: np.ndarray, top_n: int = 4) -> dict[int, str]:
    vectorizer = TfidfVectorizer(stop_words=list(SPANISH_STOP_WORDS), ngram_range=(1, 2), min_df=2, max_df=0.85, max_features=8000)
    matrix = vectorizer.fit_transform(texts.fillna("").astype(str))
    terms = np.asarray(vectorizer.get_feature_names_out())
    names = {}
    for cluster_id in sorted(np.unique(labels)):
        centroid = np.asarray(matrix[labels == cluster_id].mean(axis=0)).ravel()
        names[int(cluster_id)] = " · ".join(terms[centroid.argsort()[-top_n:][::-1]])
    return names


def category_alignment(labels: np.ndarray, categories: pd.Series) -> dict:
    valid = categories.fillna("SIN_CATEGORIA").astype(str)
    category_codes = pd.factorize(valid)[0]
    table = pd.crosstab(pd.Series(labels, name="cluster"), valid.rename("category"))
    purity = float(table.max(axis=1).sum() / table.to_numpy().sum())
    return {
        "adjusted_rand_index": float(adjusted_rand_score(category_codes, labels)),
        "normalized_mutual_information": float(normalized_mutual_info_score(category_codes, labels)),
        "cluster_purity": purity,
    }


def analyze(items: pd.DataFrame, embeddings: np.ndarray) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    required = {"item_id", "statement", "source_doc_id", "calibrated_category"}
    missing = required.difference(items.columns)
    if missing:
        raise ValueError(f"Faltan columnas: {sorted(missing)}")
    if len(items) != len(embeddings):
        raise ValueError("El número de embeddings no coincide con el catálogo")
    metrics = evaluate_k(embeddings)
    selected_k = int(metrics.loc[metrics.selected, "k"].iloc[0])
    x = normalize(np.asarray(embeddings), norm="l2")
    model = KMeans(n_clusters=selected_k, random_state=42, n_init=50)
    labels = model.fit_predict(x)
    names = cluster_keywords(items.statement, labels)

    assignments = items[["item_id", "source_doc_id", "calibrated_category"]].copy()
    assignments["cluster_id"] = labels
    assignments["cluster_label_auto"] = assignments.cluster_id.map(names)
    recurrence_docs, recurrence_levels = semantic_recurrence(embeddings, items.source_doc_id, threshold=0.70)
    assignments["recurrence_other_document_count"] = recurrence_docs
    assignments["recurrence_level"] = recurrence_levels

    summary = assignments.groupby(["cluster_id", "cluster_label_auto"], as_index=False).agg(
        signal_count=("item_id", "size"),
        document_count=("source_doc_id", "nunique"),
        median_recurrence_level=("recurrence_level", "median"),
    )
    dominant = (assignments.groupby("cluster_id").calibrated_category
                .agg(lambda x: x.fillna("SIN_CATEGORIA").value_counts().index[0]))
    summary["dominant_existing_category"] = summary.cluster_id.map(dominant)
    alignment = category_alignment(labels, items.calibrated_category)
    result_summary = {
        "signals": int(len(items)), "embedding_model": "BAAI/bge-m3",
        "selected_k": selected_k, "selection_rule": "lowest mean rank across silhouette, Calinski-Harabasz, Davies-Bouldin and stability ARI",
        "cluster_size_min": int(summary.signal_count.min()), "cluster_size_max": int(summary.signal_count.max()),
        "documents_per_cluster_min": int(summary.document_count.min()), "documents_per_cluster_max": int(summary.document_count.max()),
        "recurrence_similarity_threshold": 0.70,
        "recurrence_level_counts": {str(k): int(v) for k, v in assignments.recurrence_level.value_counts().sort_index().items()},
        **alignment,
        "interpretation": "Clusters are exploratory semantic families. Recurrence counts other documents containing a close semantic neighbor; it is not event probability.",
    }
    return assignments, summary, metrics, result_summary


def run(input_csv: Path, output_dir: Path, model_name: str = "BAAI/bge-m3") -> dict:
    from sentence_transformers import SentenceTransformer

    items = pd.read_csv(input_csv)
    texts = (items.title.fillna("") + ". " + items.statement.fillna("") + ". " + items.evidence_quote.fillna(""))
    model = SentenceTransformer(model_name)
    embeddings = model.encode(texts.tolist(), batch_size=16, show_progress_bar=True, normalize_embeddings=True)
    assignments, clusters, metrics, summary = analyze(items, embeddings)
    output_dir.mkdir(parents=True, exist_ok=True)
    np.save(output_dir / "signal_embeddings_bge_m3.npy", embeddings)
    assignments.to_csv(output_dir / "cluster_assignments_private.csv", index=False, encoding="utf-8-sig")
    clusters.to_csv(output_dir / "cluster_summary.csv", index=False, encoding="utf-8-sig")
    metrics.to_csv(output_dir / "k_selection_metrics.csv", index=False, encoding="utf-8-sig")
    (output_dir / "clustering_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--model", default="BAAI/bge-m3")
    args = parser.parse_args()
    print(json.dumps(run(args.input_csv, args.output_dir, args.model), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
