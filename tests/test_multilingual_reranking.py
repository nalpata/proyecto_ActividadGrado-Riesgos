import numpy as np
import pandas as pd

from src.retrieval.run_multilingual_reranking import normalize_matrix, rank_by_scores, top_candidates


def test_normalize_matrix_and_top_candidates():
    matrix = normalize_matrix([[3, 0], [0, 2]])
    indices, scores = top_candidates(np.array([1.0, 0.0]), matrix, 1)
    assert indices.tolist() == [0]
    assert scores.tolist() == [1.0]


def test_rank_by_scores_orders_descending():
    frame = pd.DataFrame({"chunk_id": ["a", "b", "c"]})
    ranked = rank_by_scores(frame, [0.1, 0.9, 0.5], 2)
    assert ranked["chunk_id"].tolist() == ["b", "c"]
    assert ranked["rank"].tolist() == [1, 2]
