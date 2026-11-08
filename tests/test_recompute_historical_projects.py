import numpy as np
import pandas as pd
import pytest

from src.risk.build_intelligent_risk_profile import calculate_item_pird
from src.risk.build_risk_timeline import build_timeline
from src.risk.recompute_historical_projects import recompute_projects
from src.risk.corpus_project_catalog import load_recomputed_scope
import json
from pathlib import Path


def fixture():
    catalog = {"projects": [
        {"project_id": "A", "display_name": "Alpha", "aliases": ["Alpha"]},
        {"project_id": "B", "display_name": "Beta", "aliases": ["Beta"]},
        {"project_id": "C", "display_name": "Gamma", "aliases": ["Gamma"]},
    ], "unassigned_project_id": "PENDING", "multi_project_id": "MULTI"}
    items = pd.DataFrame([
        {"item_id": f"I{i}", "source_doc_id": f"D{i}", "source_chunk_id": f"C{i}",
         "source_filename": f"acta_{date}.pdf", "explicit_date": "",
         "evidence_quote": f"{name} registra un atraso.", "calibrated_confidence": .9,
         "calibrated_evidence_sufficient": 1, "calibrated_category": "Cronograma"}
        for i, name, date in [(1, "Alpha", "20260101"), (2, "Beta", "20260301")]
    ])
    vectors = np.array([[1., 0.], [1., 0.]])
    index = items[["item_id", "source_doc_id"]].copy()
    index["recurrence_level"] = 2
    timeline, _ = build_timeline(items, index, vectors)
    exposure = pd.DataFrame([{"item_id": i, "severity": 3, "severity_supported": 1,
                             "probability": 4, "probability_supported": 1,
                             "exposure_evidence_basis": "atraso", "exposure_justification": "rúbrica histórica",
                             "exposure_assessment_confidence": .8} for i in items.item_id])
    scored = calculate_item_pird(items, exposure, timeline)
    chunks = items[["source_chunk_id", "source_filename", "evidence_quote"]].rename(
        columns={"source_chunk_id": "chunk_id", "source_filename": "filename", "evidence_quote": "chunk_text"})
    return items, scored, index, vectors, chunks, catalog


def test_recomputation_excludes_other_project_neighbors_and_preserves_original_exposure():
    args = fixture()
    historical_before = args[1].copy(deep=True)
    recomputed, snapshot = recompute_projects(*args)
    assert args[1].equals(historical_before)
    assert args[1].recurrence_level.tolist() == [2, 2]
    assert recomputed.recurrence_level.tolist() == [1, 1]
    assert recomputed.persistence_level.tolist() == [1, 1]
    assert recomputed.severity.tolist() == [3, 3]
    assert recomputed.probability.tolist() == [4, 4]
    assert (recomputed.pird < args[1].pird).all()
    assert snapshot["method"]["new_llm_calls"] == 0
    assert snapshot["projects"][2]["profile"]["global_pird"] is None
    assert snapshot["projects"][2]["profile"]["signals_total"] == 0


def test_recomputation_rejects_wrong_vector_document_alignment_and_missing_records():
    args = list(fixture())
    args[2].loc[0, "source_doc_id"] = "WRONG"
    with pytest.raises(ValueError, match="documentos fuente"):
        recompute_projects(*args)
    args = list(fixture())
    args[1] = args[1].iloc[:1]
    with pytest.raises(ValueError, match="Identificadores"):
        recompute_projects(*args)


def test_changed_classification_and_zero_vectors_cannot_silently_reuse_historical_exposure():
    args = list(fixture())
    args[0].loc[0, "calibrated_confidence"] = .1
    with pytest.raises(ValueError, match="señales originales"):
        recompute_projects(*args)
    args = list(fixture())
    args[3][0] = 0
    with pytest.raises(ValueError, match="vectores cero"):
        recompute_projects(*args)


def test_ambiguous_signals_remain_in_reconciliation_without_entering_any_profile():
    args = list(fixture())
    for frame in (args[0], args[1]):
        frame.loc[0, "evidence_quote"] = "Alpha y Beta registran un atraso."
    args[4].loc[0, "chunk_text"] = "Alpha y Beta registran un atraso."
    recomputed, snapshot = recompute_projects(*args)
    assert len(recomputed) == 2
    assert snapshot["assignment"]["signals_assigned_single_project"] == 1
    assert snapshot["assignment"]["signals_pending_or_ambiguous"] == 1
    assert snapshot["projects"][0]["profile"]["signals_total"] == 0
    pending = recomputed[recomputed.project_id == "MULTI"].iloc[0]
    assert pd.isna(pending.pird)
    assert pending.pird_status == "PENDIENTE_ASIGNACION_PROYECTO"
    assert pending.severity == 3
    assert pending.probability == 4
    assert pending.exposure_evidence_basis == "atraso"
    assert pending.exposure_justification == "rúbrica histórica"


def test_catalog_change_invalidates_cached_project_profile(tmp_path):
    args = fixture()
    _, snapshot = recompute_projects(*args)
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(snapshot))
    assert load_recomputed_scope(path, args[-1]) is not None
    args[-1]["projects"][0]["aliases"].append("New alias")
    assert load_recomputed_scope(path, args[-1]) is None


def test_project_without_signals_renders_profile_without_global_fallback():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app/streamlit_app.py", default_timeout=30).run()
    app.sidebar.radio[0].set_value("Corpus por proyecto").run()
    app.sidebar.selectbox[0].set_value("PDIS").run()
    app.sidebar.radio[1].set_value("Perfil del proyecto").run()
    assert not app.exception
    assert any("no tiene señales puntuadas" in i.value for i in app.info)
    app.sidebar.radio[1].set_value("Resumen ejecutivo").run()
    assert not app.exception
    assert next(m.value for m in app.metric if m.label == "PIRD global") == "Pendiente"
