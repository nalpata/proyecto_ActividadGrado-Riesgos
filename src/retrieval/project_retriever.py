"""Alcance por proyecto compatible con el constructor histórico del recuperador."""

from pathlib import Path
from typing import Any

from src.pipeline.end_to_end import BgeM3Retriever


class ProjectBgeM3Retriever(BgeM3Retriever):
    """Restringe el índice antes del ranking sin ampliar la firma del constructor base."""

    def __init__(self, embeddings_path: Path, top_k: int = 5,
                 encoder: Any | None = None, allowed_chunk_ids: set[str] | None = None):
        super().__init__(embeddings_path, top_k=top_k, encoder=encoder)
        self._scope_ids = None if allowed_chunk_ids is None else set(allowed_chunk_ids)
        self._scope_applied = False
        # Compatibilidad con la base nueva: el índice ya se filtra en _load.
        self.allowed_chunk_ids = None

    def _load(self) -> None:
        super()._load()
        if self._scope_applied:
            return
        if self._scope_ids is not None:
            mask = self._chunks.chunk_id.astype(str).isin(self._scope_ids).to_numpy()
            self._chunks = self._chunks.loc[mask].reset_index(drop=True)
            self._matrix = self._matrix[mask]
        self._scope_applied = True

    def __call__(self, question: str, document_ids: list[str]) -> list[dict[str, Any]]:
        if not str(question).strip():
            return []
        self._load()
        if self._chunks.empty:
            return []
        return super().__call__(question, document_ids)
