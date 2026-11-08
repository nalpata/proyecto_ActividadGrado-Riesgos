"""Recuperación sobre una ingesta de sesión sin acceso al índice histórico."""

from typing import Any
from copy import copy
import json
import re
from pathlib import Path

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
        catalog = json.loads((Path(__file__).resolve().parents[2] / "config/project_catalog.json").read_text())
        self._project_alias_groups = [
            tuple({str(p["display_name"]), *map(str, p.get("aliases", []))})
            for p in catalog["projects"]
        ]
        self.project_id = project_id
        self.allowed_chunk_ids = None
        self.top_k = top_k
        self._encoder = encoder
        self._chunks = chunks.reset_index(drop=True)
        self._matrix = matrix / norms
        if ingestion.get("project_scope", {}).get("mode") == "DOCUMENT_EVIDENCE":
            mask = self._chunks.detected_project_id.eq(project_id).to_numpy()
            self._chunks = self._chunks.loc[mask].reset_index(drop=True)
            self._matrix = self._matrix[mask]

    def _load(self) -> None:
        # Nunca abre el parquet histórico ni persiste la ingesta.
        return

    def __call__(self, question: str, document_ids: list[str]) -> list[dict[str, Any]]:
        if self._chunks.empty:
            return []
        # A named catalog project must occur in eligible documentary text, not
        # merely in the user's question or the arbitrary session name.
        eligible = self._chunks
        if document_ids:
            eligible = eligible[eligible.doc_id.astype(str).isin(map(str, document_ids))]
        mask = np.zeros(len(eligible), dtype=bool)
        named_project = False
        for aliases in self._project_alias_groups:
            pattern = r"(?<!\w)(?:" + "|".join(re.escape(a) for a in aliases) + r")(?!\w)"
            if re.search(pattern, question, re.IGNORECASE):
                named_project = True
                matches = eligible.chunk_text.astype(str).str.contains(pattern, case=False, regex=True).to_numpy()
                if not matches.any():
                    return []
                mask |= matches
        if not named_project:
            mask[:] = True
        allowed = set(eligible.loc[mask, "chunk_id"].astype(str))
        if not allowed:
            return []
        # Scope before ranking; do not discard unrelated Top-k after retrieval.
        scoped = copy(self)
        scoped.allowed_chunk_ids = allowed if self.allowed_chunk_ids is None else allowed & self.allowed_chunk_ids
        return BgeM3Retriever.__call__(scoped, question, document_ids)



CONTROLS_VERSION = "PROJECT-EXPOSURE-2"
