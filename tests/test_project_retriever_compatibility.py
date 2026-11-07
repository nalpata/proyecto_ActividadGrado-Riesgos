from types import SimpleNamespace

import numpy as np
import pandas as pd

from src.pipeline.end_to_end import BgeM3Retriever
from src.retrieval.project_retriever import ProjectBgeM3Retriever


def test_constructor_works_with_legacy_base_and_filters_before_top_k(monkeypatch, tmp_path):
    def legacy_init(self, embeddings_path, top_k=5, encoder=None):
        self.embeddings_path = embeddings_path
        self.top_k = top_k
        self._encoder = encoder
        self._chunks = None
        self._matrix = None
    monkeypatch.setattr(BgeM3Retriever, "__init__", legacy_init)
    path = tmp_path / "vectors.parquet"
    pd.DataFrame([
        {"doc_id": "D1", "filename": "other.pdf", "page": 1, "chunk_id": "X",
         "chunk_text": "Otro proyecto", "embedding": [1., 0.]},
        {"doc_id": "D2", "filename": "active.pdf", "page": 1, "chunk_id": "A",
         "chunk_text": "Proyecto activo", "embedding": [.8, .2]},
    ]).to_parquet(path)
    encoder = SimpleNamespace(encode=lambda *args, **kwargs: np.array([[1., 0.]]))
    retriever = ProjectBgeM3Retriever(path, top_k=1, encoder=encoder, allowed_chunk_ids={"A"})
    assert retriever("consulta", [])[0]["doc_id"] == "D2"
    assert retriever("otra consulta", [])[0]["doc_id"] == "D2"
    assert retriever("consulta", ["D1"]) == []
    assert ProjectBgeM3Retriever(path, encoder=encoder, allowed_chunk_ids=set())("consulta", []) == []
    assert ProjectBgeM3Retriever(path, encoder=encoder)("consulta", [])[0]["doc_id"] == "D1"
