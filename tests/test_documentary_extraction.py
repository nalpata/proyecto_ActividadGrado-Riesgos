import pandas as pd

from src.risk.extract_documentary_items import evidence_is_verbatim, parse_response, sanitize_item
from src.risk.calibrate_documentary_classifier import human_examples, sanitize as sanitize_calibrated


def test_evidence_is_verbatim_normalizes_whitespace():
    assert evidence_is_verbatim("fechas comprometidas no se cumplen", "Las fechas comprometidas no se cumplen.\nSe reiteró el atraso.")
    assert not evidence_is_verbatim("riesgo inventado", "No se reportaron riesgos.")


def test_parse_response_reads_items():
    parsed = parse_response('{"items":[{"item_type":"RIESGO"}]}')
    assert parsed == [{"item_type": "RIESGO"}]


def test_sanitize_rejects_nonverbatim_evidence():
    row = pd.Series({"doc_id":"D1", "filename":"a.pdf", "tipo_documento":"ACTA", "page":1,
                     "chunk_id":"C1", "chunk_text":"El entregable continúa pendiente."})
    item = {"item_type":"HALLAZGO", "evidence_quote":"El contrato fue terminado",
            "risk_category":"Contractual", "exposure_status":"ABIERTA", "confidence":0.9}
    assert sanitize_item(item, row) is None


def test_calibrated_sanitize_disables_watch_when_evidence_is_insufficient():
    item = {"item_type": "RIESGO", "surveillance_candidate": 1,
            "evidence_sufficient": 0, "risk_category": "Cronograma",
            "confidence": 0.8, "justification": "Prueba"}
    clean = sanitize_calibrated(item, "I1")
    assert clean["calibrated_watch"] == 0
    assert clean["calibrated_evidence_sufficient"] == 0


def test_human_examples_omits_incomplete_rows():
    audit = pd.DataFrame([
        {"item_id":"I1", "tipo_humano":"RIESGO", "requiere_vigilancia":1,
         "evidencia_suficiente":1, "categoria_humana":"Cronograma"},
        {"item_id":"I2", "tipo_humano":None, "requiere_vigilancia":None,
         "evidencia_suficiente":None, "categoria_humana":None},
    ])
    items = pd.DataFrame([
        {"item_id":"I1", "title":"a", "statement":"b", "evidence_quote":"c", "source_chunk_id":"C1"},
        {"item_id":"I2", "title":"d", "statement":"e", "evidence_quote":"f", "source_chunk_id":"C2"},
    ])
    result = human_examples(audit, items)
    assert result.item_id.tolist() == ["I1"]
