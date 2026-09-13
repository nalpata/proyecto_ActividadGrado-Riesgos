import pandas as pd

from src.risk.run_validation_agent import validate_catalog, validate_row


def row(**changes):
    base = {
        "item_id":"I1", "source_doc_id":"D1", "source_filename":"a.pdf", "source_page":1,
        "source_chunk_id":"C1", "title":"Riesgo", "statement":"Existe una exposición",
        "evidence_quote":"Existe una exposición abierta", "evidence_verified":1,
        "calibrated_type":"RIESGO", "calibrated_watch":1,
        "calibrated_evidence_sufficient":1, "calibrated_category":"Operación",
        "calibrated_confidence":0.9, "calibrated_justification":"La evidencia respalda la señal",
    }
    base.update(changes)
    return pd.Series(base)


def test_accepts_supported_watch_signal():
    decision = validate_row(row())
    assert decision["validation_accepted"] == 1
    assert decision["validation_reason"] == "ACEPTADO"


def test_rejects_item_without_watch_need():
    decision = validate_row(row(calibrated_watch=0))
    assert decision["validation_accepted"] == 0
    assert decision["validation_reason"] == "NO_REQUIERE_VIGILANCIA"


def test_rejects_insufficient_evidence_before_watch_rule():
    decision = validate_row(row(calibrated_evidence_sufficient=0))
    assert decision["validation_reason"] == "EVIDENCIA_INSUFICIENTE"


def test_catalog_rejects_duplicate_ids():
    data = pd.DataFrame([row().to_dict(), row().to_dict()])
    try:
        validate_catalog(data)
    except ValueError as exc:
        assert "duplicados" in str(exc)
    else:
        raise AssertionError("Se esperaba rechazo de item_id duplicado")
