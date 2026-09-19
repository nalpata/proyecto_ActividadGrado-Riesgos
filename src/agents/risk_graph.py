"""Grafo coordinado del Día 12 para recuperación, extracción, validación y perfil.

Los nodos son funciones delimitadas y observables. Las operaciones que requieren
modelos o artefactos privados se inyectan como dependencias para evitar acoplar la
orquestación con credenciales, datos sensibles o una interfaz de usuario.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, TypedDict

import pandas as pd
from langgraph.graph import END, START, StateGraph

from src.risk.build_intelligent_risk_profile import build_profile
from src.risk.run_validation_agent import validate_catalog


FINAL_RETRIEVAL_CONFIGURATION = {
    "query": "original",
    "embedding_model": "BAAI/bge-m3",
    "chunking": "recursive_character_splitter",
    "hyde": False,
    "reranking": False,
}


class RiskGraphState(TypedDict, total=False):
    """Contrato mínimo compartido por los cuatro nodos."""

    request_id: str
    question: str
    document_ids: list[str]
    retrieved_chunks: list[dict[str, Any]]
    documentary_candidates: list[dict[str, Any]]
    validation_decisions: list[dict[str, Any]]
    validated_signals: list[dict[str, Any]]
    risk_profile: dict[str, Any]
    evidence_available: bool
    status: str
    current_stage: str
    errors: list[dict[str, Any]]
    execution_trace: list[dict[str, Any]]


Retriever = Callable[[str, list[str]], list[dict[str, Any]]]
Extractor = Callable[[list[dict[str, Any]]], list[dict[str, Any]]]
Profiler = Callable[[list[dict[str, Any]]], dict[str, Any]]


@dataclass(frozen=True)
class RiskGraphDependencies:
    """Operaciones de dominio usadas por el grafo.

    El extractor debe devolver candidatos ya calibrados con las columnas que
    consume la puerta determinista del Día 6. Esto mantiene cuatro responsabilidades
    visibles sin añadir un quinto agente ni una llamada LLM en el validador.
    """

    retriever: Retriever
    extractor: Extractor
    profiler: Profiler | None = None


def _trace(state: RiskGraphState, stage: str, started: float, received: int, produced: int) -> list[dict[str, Any]]:
    return [
        *state.get("execution_trace", []),
        {
            "stage": stage,
            "status": "ok",
            "elapsed_seconds": round(time.perf_counter() - started, 6),
            "received": int(received),
            "produced": int(produced),
        },
    ]


def _failure(state: RiskGraphState, stage: str, started: float, exc: Exception) -> dict[str, Any]:
    error = {"stage": stage, "error_type": type(exc).__name__, "message": str(exc)[:500]}
    trace = [
        *state.get("execution_trace", []),
        {"stage": stage, "status": "error", "elapsed_seconds": round(time.perf_counter() - started, 6)},
    ]
    return {
        "status": "ERROR",
        "current_stage": stage,
        "errors": [*state.get("errors", []), error],
        "execution_trace": trace,
    }


def aggregate_profile(validated_signals: list[dict[str, Any]]) -> dict[str, Any]:
    """Consolida un perfil cuando las señales ya contienen resultados PIRD.

    Si aún no llegan enriquecidas, conserva la política estricta de faltantes y
    declara el perfil pendiente en vez de imputar severidad o probabilidad.
    """

    frame = pd.DataFrame(validated_signals)
    required = {"item_id", "pird_status", "pird", "pird_level", "calibrated_category", "persistence_level"}
    if frame.empty:
        return {"profile_status": "PENDIENTE", "reason": "No hay señales validadas", "signals_total": 0}
    if not required.issubset(frame.columns):
        return {
            "profile_status": "PENDIENTE_ENRIQUECIMIENTO",
            "signals_total": int(len(frame)),
            "signals_scored": 0,
            "signals_pending": int(len(frame)),
            "missing_fields": sorted(required - set(frame.columns)),
        }
    categories, profile = build_profile(frame)
    profile["categories"] = categories.to_dict("records")
    return profile


def build_risk_graph(dependencies: RiskGraphDependencies):
    """Compila el flujo LangGraph del Día 12."""

    profiler = dependencies.profiler or aggregate_profile

    def retrieval_agent(state: RiskGraphState) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            chunks = dependencies.retriever(state.get("question", ""), state.get("document_ids", []))
            available = bool(chunks)
            return {
                "retrieved_chunks": chunks,
                "evidence_available": available,
                "status": "RUNNING" if available else "NO_EVIDENCE",
                "current_stage": "retrieval",
                "execution_trace": _trace(state, "retrieval", started, 1, len(chunks)),
            }
        except Exception as exc:  # pragma: no cover - comportamiento probado por estado
            return _failure(state, "retrieval", started, exc)

    def risk_extractor_agent(state: RiskGraphState) -> dict[str, Any]:
        started = time.perf_counter()
        chunks = state.get("retrieved_chunks", [])
        try:
            candidates = dependencies.extractor(chunks)
            return {
                "documentary_candidates": candidates,
                "status": "RUNNING" if candidates else "NO_CANDIDATES",
                "current_stage": "risk_extraction",
                "execution_trace": _trace(state, "risk_extraction", started, len(chunks), len(candidates)),
            }
        except Exception as exc:
            return _failure(state, "risk_extraction", started, exc)

    def risk_validator_agent(state: RiskGraphState) -> dict[str, Any]:
        started = time.perf_counter()
        candidates = state.get("documentary_candidates", [])
        try:
            decisions, _ = validate_catalog(pd.DataFrame(candidates))
            accepted = decisions[decisions.validation_accepted == 1]
            accepted_records = accepted.to_dict("records")
            return {
                "validation_decisions": decisions.to_dict("records"),
                "validated_signals": accepted_records,
                "status": "RUNNING" if accepted_records else "NO_VALIDATED_SIGNALS",
                "current_stage": "risk_validation",
                "execution_trace": _trace(state, "risk_validation", started, len(candidates), len(accepted_records)),
            }
        except Exception as exc:
            return _failure(state, "risk_validation", started, exc)

    def risk_profiler_agent(state: RiskGraphState) -> dict[str, Any]:
        started = time.perf_counter()
        signals = state.get("validated_signals", [])
        try:
            profile = profiler(signals)
            return {
                "risk_profile": profile,
                "status": "COMPLETED",
                "current_stage": "risk_profile",
                "execution_trace": _trace(state, "risk_profile", started, len(signals), 1),
            }
        except Exception as exc:
            return _failure(state, "risk_profile", started, exc)

    def continue_or_end(state: RiskGraphState) -> str:
        return "end" if state.get("status") in {"ERROR", "NO_EVIDENCE", "NO_CANDIDATES", "NO_VALIDATED_SIGNALS"} else "continue"

    graph = StateGraph(RiskGraphState)
    graph.add_node("retrieval_agent", retrieval_agent)
    graph.add_node("risk_extractor_agent", risk_extractor_agent)
    graph.add_node("risk_validator_agent", risk_validator_agent)
    graph.add_node("risk_profiler_agent", risk_profiler_agent)
    graph.add_edge(START, "retrieval_agent")
    graph.add_conditional_edges("retrieval_agent", continue_or_end, {"continue": "risk_extractor_agent", "end": END})
    graph.add_conditional_edges("risk_extractor_agent", continue_or_end, {"continue": "risk_validator_agent", "end": END})
    graph.add_conditional_edges("risk_validator_agent", continue_or_end, {"continue": "risk_profiler_agent", "end": END})
    graph.add_edge("risk_profiler_agent", END)
    return graph.compile()


def run_risk_graph(
    dependencies: RiskGraphDependencies,
    question: str,
    document_ids: list[str] | None = None,
    request_id: str | None = None,
) -> RiskGraphState:
    """Ejecuta el grafo con un estado inicial reproducible."""

    initial: RiskGraphState = {
        "request_id": request_id or str(uuid.uuid4()),
        "question": question,
        "document_ids": document_ids or [],
        "errors": [],
        "execution_trace": [],
        "status": "STARTED",
        "current_stage": "start",
    }
    return build_risk_graph(dependencies).invoke(initial)
