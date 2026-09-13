import pandas as pd

from src.risk.extract_documentary_items import evidence_is_verbatim, parse_response, sanitize_item


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
