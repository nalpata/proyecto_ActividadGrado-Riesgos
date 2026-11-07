"""Recuperación sobre una ingesta de sesión sin acceso al índice histórico."""

from typing import Any

import numpy as np
import pandas as pd

from src.pipeline.end_to_end import BgeM3Retriever


class SessionRetriever(BgeM3Retriever):
    """Índice en memoria con alcance de proyecto comprobado antes de consultar."""

    def __init__(self, ingestion: dict[str, Any], encoder: Any, top_k: int = 5):
        project_id = str(ingestion.get("project_id") or "")
        rows = ingestion.get("chunks") or []
        if not project_id or not rows:
            raise ValueError("El proyecto no tiene documentos procesados")
        if any(str(row.get("project_id")) != project_id for row in rows):
            raise ValueError("El índice contiene documentos de otro proyecto")
        if top_k < 1:
            raise ValueError("top_k debe ser positivo")
        chunks = pd.DataFrame(rows).copy(deep=True)
        required = {"doc_id", "filename", "page", "chunk_id", "chunk_text", "embedding"}
        if not required.issubset(chunks.columns):
            raise ValueError("Índice de sesión incompleto")
        matrix = np.vstack([np.asarray(v, dtype=np.float32) for v in chunks.embedding])
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        if not np.isfinite(matrix).all() or (norms == 0).any():
            raise ValueError("El índice contiene vectores inválidos")
        self.project_id = project_id
        self.allowed_chunk_ids = None
        self.top_k = top_k
        self._encoder = encoder
        self._chunks = chunks.reset_index(drop=True)
        self._matrix = matrix / norms

    def _load(self) -> None:
        # Nunca abre el parquet histórico ni persiste la ingesta.
        return
