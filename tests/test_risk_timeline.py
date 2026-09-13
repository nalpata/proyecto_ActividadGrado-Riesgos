import numpy as np
import pandas as pd

from src.risk.build_risk_timeline import build_timeline, infer_document_date, persistence_level


def test_filename_date_patterns_and_anomaly():
    assert str(infer_document_date("Acta_20240430.docx")["document_date"].date()) == "2024-04-30"
    assert str(infer_document_date("Comunicado_21042023.pdf")["document_date"].date()) == "2023-04-21"
    assert str(infer_document_date("Reporte_202407.pdf")["document_date"].date()) == "2024-07-01"
    assert str(infer_document_date("Agosto 5 2024.pdf")["document_date"].date()) == "2024-08-05"
    assert pd.isna(infer_document_date("Comunicado_20140105.pdf")["document_date"])


def test_persistence_rubric():
    assert [persistence_level(days, docs) for days, docs in [(0, 1), (10, 2), (60, 2), (120, 3), (365, 4)]] == [1, 2, 3, 4, 5]


def test_timeline_does_not_invent_pird():
    items = pd.DataFrame({
        "item_id": ["I1", "I2", "I3"], "source_doc_id": ["D1", "D2", "D3"],
        "source_filename": ["Acta_20240101.pdf", "Acta_20240315.pdf", "sin_fecha.pdf"],
        "explicit_date": [None, None, None], "calibrated_confidence": [0.9, 0.8, 0.7],
        "calibrated_evidence_sufficient": [1, 1, 1],
    })
    assignments = pd.DataFrame({"item_id": ["I1", "I2", "I3"], "recurrence_level": [2, 2, 1]})
    embeddings = np.array([[1, 0], [0.99, 0.01], [0, 1]], dtype=float)
    timeline, summary = build_timeline(items, assignments, embeddings, threshold=0.90)
    assert timeline.loc[0, "persistence_level"] == 3
    assert timeline.loc[1, "temporal_role"] == "RECURRENCIA"
    assert timeline.loc[2, "temporal_role"] == "PENDIENTE_FECHA"
    assert summary["pird_calculated"] == 0
    assert summary["pird_pending"] == 3
