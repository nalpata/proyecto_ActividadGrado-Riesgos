import json
import re
from types import SimpleNamespace

import numpy as np
import pandas as pd

from src.pipeline.project_risk_processing import (
    parse_calibration_examples,
    process_project_risks,
)
from src.risk.build_intelligent_risk_profile import build_profile


class FakeEncoder:
    def encode(self, texts, **kwargs):
        assert kwargs["normalize_embeddings"] is True
        return np.tile(np.asarray([[1.0, 0.0, 0.0]], dtype=np.float32), (len(texts), 1))


class FakeCompletions:
    def create(self, **kwargs):
        schema = kwargs["response_format"]["json_schema"]["name"]
        prompt = kwargs["messages"][-1]["content"]
        if schema == "documentary_item_extraction":
            payload = {"items": [{
                "item_type": "HALLAZGO",
                "title": "Retraso de entrega",
                "statement": "La entrega mantiene un retraso documentado.",
                "evidence_quote": "La entrega mantiene un retraso documentado y continúa pendiente.",
                "evidence_sufficient": 1,
                "surveillance_candidate": 1,
                "exposure_status": "ABIERTA",
                "risk_category": "Cronograma",
                "responsible": "",
                "explicit_date": "",
                "confidence": 0.9,
                "justification": "Condición adversa abierta.",
            }]}
        elif schema == "calibrated_documentary_classification":
            ids = list(dict.fromkeys(re.findall(r'ITEM_\d{5}', prompt)))
            payload = {"classifications": [{
                "item_id": item_id,
                "item_type": "HALLAZGO",
                "surveillance_candidate": 1,
                "evidence_sufficient": 1,
                "risk_category": "Cronograma",
                "confidence": 0.9,
                "justification": "Evidencia suficiente y exposición abierta.",
            } for item_id in ids]}
        elif schema == "pird_exposure_assessment":
            ids = list(dict.fromkeys(re.findall(r'ITEM_\d{5}', prompt)))
            payload = {"assessments": [{
                "item_id": item_id,
                "severity": 3,
                "severity_supported": 1,
                "probability": 4,
                "probability_supported": 1,
                "evidence_basis": "retraso documentado y pendiente",
                "justification": "La condición permanece abierta.",
                "confidence": 0.85,
            } for item_id in ids]}
        else:
            raise AssertionError(f"Esquema inesperado: {schema}")
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
        )


class FakeClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=FakeCompletions())


def ingestion_payload():
    text = "La entrega mantiene un retraso documentado y continúa pendiente."
    return {
        "project_id": "PROYECTO-19B",
        "chunks": [
            {
                "project_id": "PROYECTO-19B", "doc_id": "DOC-A",
                "filename": "acta_20260101.pdf", "page": 1, "chunk_id": "CHUNK-A",
                "chunk_text": text, "embedding": np.asarray([1.0, 0.0, 0.0]),
            },
            {
                "project_id": "PROYECTO-19B", "doc_id": "DOC-B",
                "filename": "acta_20260215.pdf", "page": 1, "chunk_id": "CHUNK-B",
                "chunk_text": text, "embedding": np.asarray([1.0, 0.0, 0.0]),
            },
        ],
    }


def test_day_19b_runs_project_scoped_pipeline_and_calculates_pird():
    result = process_project_risks(ingestion_payload(), FakeClient(), FakeEncoder())

    assert result["status"] == "COMPLETED"
    assert result["project_id"] == "PROYECTO-19B"
    assert result["summary"]["items_extracted"] == 2
    assert result["summary"]["signals_validated"] == 2
    assert result["summary"]["signals_scored"] == 2
    assert result["summary"]["scoring_coverage"] == 1.0
    assert result["summary"]["global_pird"] is not None
    assert result["classification"]["calibration_status"] == "PROVISIONAL_NO_PRIVATE_EXAMPLES"
    assert result["timeline"]["signals_with_persistence"] == 2
    assert result["usage"]["total_tokens"] > 0
    assert result["categories"][0]["category"] == "Cronograma"


def test_day_19b_rejects_cross_project_chunks_before_model_calls():
    payload = ingestion_payload()
    payload["chunks"][1]["project_id"] = "OTRO-PROYECTO"

    try:
        process_project_risks(payload, FakeClient(), FakeEncoder())
        raise AssertionError("La mezcla de proyectos debía rechazarse")
    except ValueError as exc:
        assert "otro proyecto" in str(exc)


def test_private_calibration_examples_accept_public_alias_format():
    frame = parse_calibration_examples([{
        "title": "Caso", "statement": "Declaración", "evidence": "Evidencia literal",
        "correct_type": "RIESGO", "correct_watch": 1, "correct_evidence": 1,
        "correct_category": "Cronograma",
    }])

    assert len(frame) == 1
    assert frame.iloc[0].human_type == "RIESGO"
    assert frame.iloc[0].evidence_quote == "Evidencia literal"


def test_day_19b_interface_exposes_analysis_action_and_privacy_boundary():
    source = open("app/streamlit_app.py", encoding="utf-8").read()

    assert "Analizar riesgos · Día 19B" in source
    assert "process_project_risks" in source
    assert "CALIBRATION_EXAMPLES_JSON" in source
    assert "Día 19C" in source


def test_profile_keeps_category_without_complete_pird_as_pending():
    scored = pd.DataFrame([
        {"item_id": "A", "calibrated_category": "Cronograma", "pird_status": "CALCULADO",
         "pird": 60.0, "persistence_level": 3, "pird_level": "ALTO"},
        {"item_id": "B", "calibrated_category": "Calidad", "pird_status": "PENDIENTE_ENRIQUECIMIENTO",
         "pird": None, "persistence_level": None, "pird_level": None},
    ])

    categories, profile = build_profile(scored)

    pending = categories[categories.calibrated_category == "Calidad"].iloc[0]
    assert pending.category_level == "PENDIENTE"
    assert pending.scored_signals == 0
    assert pending.scoring_coverage == 0
    assert profile["signals_pending"] == 1
