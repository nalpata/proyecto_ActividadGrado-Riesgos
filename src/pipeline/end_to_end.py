"""Automatización del Día 13 desde una consulta hasta Q&A y perfil de riesgo.

El pipeline conecta el grafo del Día 12 con los artefactos reales seleccionados.
Los archivos por señal permanecen privados y se suministran en tiempo de ejecución.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from src.agents.risk_graph import RiskGraphDependencies, run_risk_graph


class BgeM3Retriever:
    """Recuperación directa sobre los embeddings BGE-M3 congelados."""

    def __init__(self, embeddings_path: Path, top_k: int = 5, encoder: Any | None = None):
        self.embeddings_path = Path(embeddings_path)
        self.top_k = top_k
        self._encoder = encoder
        self._chunks: pd.DataFrame | None = None
        self._matrix: np.ndarray | None = None

    def _load(self) -> None:
        if self._chunks is not None:
            return
        chunks = pd.read_parquet(self.embeddings_path).reset_index(drop=True)
        required = {"doc_id", "filename", "page", "chunk_id", "chunk_text", "embedding"}
        missing = required - set(chunks.columns)
        if missing:
            raise ValueError(f"Faltan columnas en embeddings: {sorted(missing)}")
        matrix = np.vstack(chunks.embedding.map(lambda value: np.asarray(value, dtype=np.float32)))
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        self._chunks = chunks
        self._matrix = matrix / np.where(norms == 0, 1, norms)

    def _get_encoder(self):
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer

            self._encoder = SentenceTransformer("BAAI/bge-m3")
        return self._encoder

    def __call__(self, question: str, document_ids: list[str]) -> list[dict[str, Any]]:
        if not str(question).strip():
            return []
        self._load()
        assert self._chunks is not None and self._matrix is not None
        query = self._get_encoder().encode(
            [question], convert_to_numpy=True, normalize_embeddings=True
        )[0]
        scores = self._matrix @ np.asarray(query, dtype=np.float32)
        eligible = np.arange(len(self._chunks))
        if document_ids:
            allowed = self._chunks.doc_id.astype(str).isin({str(value) for value in document_ids})
            eligible = np.flatnonzero(allowed.to_numpy())
        if len(eligible) == 0:
            return []
        ordered = eligible[np.argsort(scores[eligible])[::-1][: self.top_k]]
        records = []
        for rank, index in enumerate(ordered, 1):
            row = self._chunks.iloc[index]
            records.append({
                "rank": rank,
                "score": float(scores[index]),
                "doc_id": str(row.doc_id),
                "filename": str(row.filename),
                "page": row.page,
                "chunk_id": str(row.chunk_id),
                "chunk_text": str(row.chunk_text),
            })
        return records


class CalibratedCatalogExtractor:
    """Recupera candidatos ya calibrados para los chunks seleccionados.

    El CSV es un artefacto privado generado en el Día 5 y no se versiona.
    """

    def __init__(self, calibrated_catalog_path: Path):
        self.path = Path(calibrated_catalog_path)
        self._catalog: pd.DataFrame | None = None

    def _load(self) -> pd.DataFrame:
        if self._catalog is None:
            catalog = pd.read_csv(self.path)
            required = {
                "item_id", "source_chunk_id", "evidence_quote", "evidence_verified",
                "calibrated_watch", "calibrated_evidence_sufficient",
                "calibrated_category", "calibrated_confidence",
            }
            missing = required - set(catalog.columns)
            if missing:
                raise ValueError(f"Faltan columnas en catálogo calibrado: {sorted(missing)}")
            self._catalog = catalog
        return self._catalog

    def __call__(self, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        chunk_ids = {str(item.get("chunk_id")) for item in chunks}
        if not chunk_ids:
            return []
        catalog = self._load()
        selected = catalog[catalog.source_chunk_id.astype(str).isin(chunk_ids)].copy()
        return selected.to_dict("records")


class PublishedProfileLoader:
    """Entrega el perfil agregado aprobado sin exponer evaluaciones individuales."""

    def __init__(self, profile_path: Path, categories_path: Path | None = None):
        self.profile_path = Path(profile_path)
        self.categories_path = Path(categories_path) if categories_path else None

    def __call__(self, signals: list[dict[str, Any]]) -> dict[str, Any]:
        profile = json.loads(self.profile_path.read_text(encoding="utf-8"))
        profile["validated_signals_in_request"] = int(len(signals))
        profile["profile_source"] = "frozen_day_11_aggregate"
        if self.categories_path and self.categories_path.exists():
            categories = pd.read_csv(self.categories_path)
            profile["categories"] = categories.to_dict("records")
        return profile


class OpenAIRagAnswerer:
    """Genera una respuesta exclusivamente desde los chunks recuperados."""

    def __init__(self, model: str = "gpt-4o-mini", client: Any | None = None):
        self.model = model
        self._client = client

    def _get_client(self):
        if self._client is None:
            if not os.getenv("OPENAI_API_KEY"):
                raise RuntimeError("Falta OPENAI_API_KEY")
            from openai import OpenAI

            self._client = OpenAI()
        return self._client

    def __call__(self, question: str, chunks: list[dict[str, Any]]) -> dict[str, Any]:
        if not chunks:
            return {
                "answer": "No se encontró evidencia documental suficiente para responder.",
                "evidence_available": False,
                "sources": [],
                "model": self.model,
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            }
        context = "\n\n".join(
            f"[{item['rank']}] Documento: {item['filename']} | página: {item['page']} | chunk: {item['chunk_id']}\n{item['chunk_text']}"
            for item in chunks
        )
        prompt = f"""Responde la pregunta usando únicamente la evidencia proporcionada.

Reglas:
- No uses conocimiento externo ni completes vacíos.
- Si la evidencia es insuficiente, indícalo expresamente.
- Cita las fuentes con el formato [n].
- Distingue hechos ocurridos, riesgos, compromisos y acciones cuando corresponda.

PREGUNTA:
{question}

EVIDENCIA:
{context}"""
        response = self._get_client().chat.completions.create(
            model=self.model,
            temperature=0.0,
            messages=[
                {"role": "system", "content": "Respondes consultas documentales con trazabilidad y sin inventar información."},
                {"role": "user", "content": prompt},
            ],
        )
        usage = response.usage
        answer = (response.choices[0].message.content or "").strip()
        empty_response = not bool(answer)
        return {
            "answer": answer or "El modelo no produjo una respuesta. Intente nuevamente.",
            "evidence_available": not empty_response,
            "response_status": "EMPTY_MODEL_RESPONSE" if empty_response else "COMPLETED",
            "sources": [
                {k: item[k] for k in ("rank", "doc_id", "filename", "page", "chunk_id", "score")}
                for item in chunks
            ],
            "model": self.model,
            "usage": {
                "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
                "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
                "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
            },
        }


class JsonCheckpointStore:
    """Checkpoint privado por solicitud para reanudar sin repetir llamadas."""

    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, request_id: str) -> Path:
        safe = "".join(char for char in request_id if char.isalnum() or char in {"-", "_"})
        if not safe:
            raise ValueError("request_id inválido")
        return self.directory / f"{safe}.json"

    def load(self, request_id: str) -> dict[str, Any] | None:
        path = self._path(request_id)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def save(self, request_id: str, result: dict[str, Any]) -> None:
        path = self._path(request_id)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        temporary.replace(path)


class JsonlErrorLogger:
    """Registro privado y append-only de fallos operativos sin payload documental."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def __call__(self, request_id: str, error: dict[str, Any]) -> None:
        safe_error = {
            "request_id": request_id,
            "stage": error.get("stage", "unknown"),
            "error_type": error.get("error_type", "RuntimeError"),
            "message": str(error.get("message", "Error no especificado"))[:500],
        }
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(safe_error, ensure_ascii=False) + "\n")


class EndToEndPipeline:
    """Coordina el grafo, la respuesta RAG y el checkpoint del Día 13."""

    def __init__(
        self,
        retriever: Callable[[str, list[str]], list[dict[str, Any]]],
        extractor: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
        profiler: Callable[[list[dict[str, Any]]], dict[str, Any]],
        answerer: Callable[[str, list[dict[str, Any]]], dict[str, Any]],
        checkpoint_store: JsonCheckpointStore | None = None,
        error_logger: Callable[[str, dict[str, Any]], None] | None = None,
    ):
        self.dependencies = RiskGraphDependencies(retriever=retriever, extractor=extractor, profiler=profiler)
        self.answerer = answerer
        self.checkpoint_store = checkpoint_store
        self.error_logger = error_logger

    def run(
        self,
        question: str,
        request_id: str,
        document_ids: list[str] | None = None,
        resume: bool = True,
    ) -> dict[str, Any]:
        if resume and self.checkpoint_store:
            cached = self.checkpoint_store.load(request_id)
            if cached is not None:
                cached.setdefault("execution", {})["resumed_from_checkpoint"] = True
                return cached
        started = time.perf_counter()
        state = run_risk_graph(self.dependencies, question, document_ids, request_id)
        try:
            qa_result = self.answerer(question, state.get("retrieved_chunks", []))
        except Exception as exc:
            qa_error = {
                "stage": "rag_answer",
                "error_type": type(exc).__name__,
                "message": str(exc)[:500],
            }
            state.setdefault("errors", []).append(qa_error)
            state["status"] = "ERROR"
            state["current_stage"] = "rag_answer"
            qa_result = {
                "answer": "No fue posible generar la respuesta en esta ejecución.",
                "evidence_available": False,
                "response_status": "ERROR",
                "sources": [],
            }
        if self.error_logger:
            for error in state.get("errors", []):
                self.error_logger(request_id, error)
        result = {
            "request_id": request_id,
            "qa_result": qa_result,
            "risk_result": {
                "validated_signals_count": len(state.get("validated_signals", [])),
                "profile": state.get("risk_profile"),
            },
            "execution": {
                "status": state.get("status"),
                "current_stage": state.get("current_stage"),
                "trace": state.get("execution_trace", []),
                "errors": state.get("errors", []),
                "elapsed_seconds": round(time.perf_counter() - started, 6),
                "resumed_from_checkpoint": False,
            },
        }
        if self.checkpoint_store:
            self.checkpoint_store.save(request_id, result)
        return result


def public_execution_summary(result: dict[str, Any]) -> dict[str, Any]:
    """Crea un resumen publicable sin respuestas, fuentes ni señales."""

    profile = result.get("risk_result", {}).get("profile") or {}
    qa = result.get("qa_result", {})
    execution = result.get("execution", {})
    return {
        "request_id": result.get("request_id"),
        "status": execution.get("status"),
        "stages": [item.get("stage") for item in execution.get("trace", [])],
        "elapsed_seconds": execution.get("elapsed_seconds"),
        "evidence_available": bool(qa.get("evidence_available")),
        "source_count": len(qa.get("sources", [])),
        "validated_signals_count": result.get("risk_result", {}).get("validated_signals_count", 0),
        "profile_status": profile.get("profile_status"),
        "global_pird": profile.get("global_pird"),
        "scoring_coverage": profile.get("scoring_coverage"),
        "private_payload_included": False,
    }
