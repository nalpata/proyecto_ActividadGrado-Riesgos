import hashlib
import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.risk.enrich_missing_exposure import prepare_cases, apply_assessments, validate_response, normalize_response, run
from src.risk.project_resolution import build_public_project_snapshot


CATALOG = {"projects": [{"project_id": "A", "display_name": "Alpha", "aliases": ["Alpha"]},
                         {"project_id": "B", "display_name": "Beta", "aliases": ["Beta"]}],
           "unassigned_project_id": "PENDING", "multi_project_id": "MULTI"}
QUOTE = "Alpha mantiene un atraso que afecta la entrega contractual."


def fixture():
    row = {"item_id": "I1", "source_doc_id": "D1", "source_chunk_id": "C1", "source_filename": "Alpha.pdf",
           "source_page": 1, "project_id": "A", "project_assignment_status": "ASSIGNED_SIGNAL_EXPLICIT",
           "evidence_quote": QUOTE, "severity": np.nan, "severity_supported": 0, "probability": 4.,
           "probability_supported": 1, "recurrence_level": 1., "persistence_level": 1.,
           "calibrated_confidence": .9, "calibrated_evidence_sufficient": 1, "calibrated_category": "Cronograma",
           "calibrated_type": "HALLAZGO", "exposure_status": "ABIERTA", "title": "Atraso",
           "statement": QUOTE, "pird": np.nan, "pird_status": "PENDIENTE_ENRIQUECIMIENTO",
           "pird_level": None, "exposure_index": np.nan, "reliability_index": np.nan,
           "pird_missing_components": "severity", "document_date": "2024-01-01", "temporal_role": "APARICION"}
    signals = pd.DataFrame([row])
    chunks = pd.DataFrame([{"chunk_id": "C1", "doc_id": "D1", "filename": "Alpha.pdf", "page": 1,
                            "chunk_text": QUOTE + " Beta tiene un hallazgo grave en otra contratación."}])
    return signals, chunks


def response():
    return [{"item_id": "I1", "severity": {"value": 4, "quote": QUOTE,
        "justification": "Afecta la entrega contractual de Alpha", "status": "SUSTENTADO"},
        "probability": {"value": None, "quote": "", "justification": "Conservar", "status": "YA_EXISTENTE"}}]


def test_only_missing_component_is_filled_and_provenance_is_separate():
    signals, chunks = fixture(); before = signals.copy(deep=True)
    records = response()
    # A proposal must never overwrite an existing probability.
    records[0]["probability"] = {**records[0]["severity"], "value": 1}
    result, audit = apply_assessments(signals, prepare_cases(signals, chunks, CATALOG), records, CATALOG)
    assert result.iloc[0].severity == 4 and result.iloc[0].probability == 4
    assert result.iloc[0].pird_status == "CALCULADO"
    assert audit.accepted.tolist() == [True, False]
    assert result.iloc[0].evidence_quote == QUOTE
    pd.testing.assert_frame_equal(signals, before)


@pytest.mark.parametrize("quote,decision", [("Texto inventado que no está en la fuente", "REJECTED_UNVERIFIED_EVIDENCE"),
    ("Beta tiene un hallazgo grave en otra contratación.", "REJECTED_PROJECT_SCOPE")])
def test_unsupported_or_other_project_quotes_do_not_fill_missing(quote, decision):
    signals, chunks = fixture(); records = response(); records[0]["severity"]["quote"] = quote
    result, audit = apply_assessments(signals, prepare_cases(signals, chunks, CATALOG), records, CATALOG)
    assert pd.isna(result.iloc[0].severity) and pd.isna(result.iloc[0].pird)
    assert audit.iloc[0].decision == decision


@pytest.mark.parametrize("records", [[], response() * 2, [{**response()[0], "item_id": "ALIEN"}]])
def test_incomplete_duplicate_or_alien_responses_are_rejected(records):
    signals, chunks = fixture()
    with pytest.raises(ValueError, match="identificadores"):
        validate_response(records, prepare_cases(signals, chunks, CATALOG))


def test_no_aplica_does_not_remove_signal_from_denominator():
    signals, chunks = fixture(); records = response()
    records[0]["severity"].update(value=None, status="NO_APLICA", quote="")
    result, audit = apply_assessments(signals, prepare_cases(signals, chunks, CATALOG), records, CATALOG)
    assert len(result) == 1 and pd.isna(result.iloc[0].pird) and not audit.accepted.any()


def test_mismatched_source_is_rejected_before_model_call():
    signals, chunks = fixture(); chunks.loc[0, "filename"] = "OTHER.pdf"
    with pytest.raises(ValueError, match="Fuente"):
        prepare_cases(signals, chunks, CATALOG)


def test_resume_reuses_verified_checkpoint_and_refuses_changed_context(tmp_path):
    signals, chunks = fixture()
    class Client:
        def __init__(self): self.chat = SimpleNamespace(completions=self); self.calls = 0
        def create(self, **kwargs):
            self.calls += 1
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({"assessments": response()})))],
                usage=SimpleNamespace(prompt_tokens=10, completion_tokens=20), model="fake-test-model")
    client = Client(); baseline = {"catalog_sha256": hashlib.sha256(json.dumps(CATALOG, sort_keys=True, ensure_ascii=False).encode()).hexdigest(), "method": {}}
    first = run(signals, chunks, CATALOG, baseline, client, tmp_path)
    second = run(signals, chunks, CATALOG, baseline, client, tmp_path)
    assert client.calls == 1 and first == second and first["components_accepted"] == 1
    chunks.loc[0, "chunk_text"] += " Otro párrafo."
    with pytest.raises(ValueError, match="Checkpoint"):
        run(signals, chunks, CATALOG, baseline, client, tmp_path)


def test_boolean_value_cannot_pass_as_level_one():
    signals, chunks = fixture(); records = response(); records[0]["severity"]["value"] = True
    with pytest.raises(ValueError, match="rúbrica"):
        validate_response(records, prepare_cases(signals, chunks, CATALOG))


@pytest.mark.parametrize("status,value", [("NO_APLICA", 4), ("SUSTENTADO", None),
    ("EVIDENCIA_INSUFICIENTE", 2), ("SUSTENTADO", True), ("SUSTENTADO", 9)])
def test_inconsistent_component_is_rejected_without_stopping_batch(status, value):
    signals, chunks = fixture(); records = response()
    records[0]["severity"].update(status=status, value=value)
    cases = prepare_cases(signals, chunks, CATALOG)
    normalized = normalize_response(records, cases)
    result, audit = apply_assessments(signals, cases, normalized, CATALOG)
    assert pd.isna(result.iloc[0].severity) and pd.isna(result.iloc[0].pird)
    assert result.iloc[0].probability == 4
    assert audit.iloc[0].decision == "REJECTED_INCONSISTENT_MODEL_RESPONSE"


def test_valid_component_survives_inconsistent_other_component():
    signals, chunks = fixture(); signals.loc[0, "probability"] = np.nan
    records = response(); records[0]["probability"].update(status="NO_APLICA", value=3)
    cases = prepare_cases(signals, chunks, CATALOG)
    result, audit = apply_assessments(signals, cases, normalize_response(records, cases), CATALOG)
    assert result.iloc[0].severity == 4 and pd.isna(result.iloc[0].probability)
    assert audit.accepted.tolist() == [True, False]


@pytest.mark.parametrize("records", [None, [], response() * 2, [{"item_id": ["I1"]}], response()[0]])
def test_malformed_batch_stays_pending_with_audit(records):
    signals, chunks = fixture(); cases = prepare_cases(signals, chunks, CATALOG)
    normalized = normalize_response(records, cases)
    result, audit = apply_assessments(signals, cases, normalized, CATALOG)
    assert pd.isna(result.iloc[0].severity) and not audit.accepted.any()
    assert audit.iloc[0].decision == "REJECTED_RESPONSE_IDENTIFIERS"


def test_partial_batch_keeps_unique_known_ids_without_associating_by_position():
    cases = [{"item_id": "I1", "missing": ["severity"]}, {"item_id": "I2", "missing": ["severity"]}]
    result = normalize_response(response(), cases)
    assert result[0]["severity"]["value"] == 4
    assert result[1]["severity"]["value"] is None
    assert result[1]["validation_errors"]["severity"] == "REJECTED_RESPONSE_IDENTIFIERS"


def test_duplicate_id_is_rejected_while_other_unique_response_survives():
    cases = [{"item_id": "I1", "missing": ["severity"]}, {"item_id": "I2", "missing": ["severity"]}]
    records = response() * 2 + [{**response()[0], "item_id": "I2"}]
    result = normalize_response(records, cases)
    assert result[0]["severity"]["value"] is None
    assert result[1]["severity"]["value"] == 4
