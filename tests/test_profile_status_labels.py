from copy import deepcopy

import pytest
from streamlit.testing.v1 import AppTest
from pathlib import Path

from src.frontend.profile_status_labels import describe_pird_profile


def profile(total=404, scored=234, pird=49.77):
    return {"signals_total": total, "signals_scored": scored,
            "signals_pending": total - scored, "global_pird": pird,
            "profile_status": "PROVISIONAL", "scoring_coverage": scored / total if total else 0}


def test_partial_coverage_is_not_confused_with_an_unimplemented_calculation():
    source = profile()
    original = deepcopy(source)
    presentation = describe_pird_profile(source, "corpus")
    assert presentation["calculation_label"] == "PIRD calculado sobre señales evaluables"
    assert presentation["coverage_text"] == "234 de 404 señales (57.92 %)"
    assert presentation["signals_pending"] == 170
    assert "muestral" in presentation["validation_label"]
    assert source == original


def test_complete_coverage_does_not_become_complete_expert_validation():
    presentation = describe_pird_profile(profile(1, 1, 37.82), "corpus")
    assert "Completa" in presentation["coverage_label"]
    assert "muestral" in presentation["validation_label"]
    assert "no valida todas" in presentation["validation_note"]


@pytest.mark.parametrize("source", [profile(4, 0, None), profile(0, 0, None)])
def test_missing_scores_or_empty_projects_never_present_a_calculated_pird(source):
    presentation = describe_pird_profile(source, "corpus")
    assert presentation["calculation_label"] != "PIRD calculado sobre señales evaluables"
    assert presentation["signals_pending"] == source["signals_total"]


def test_review_of_the_corpus_is_not_transferred_to_sessions_or_synthetic_data():
    assert "Sin revisión experta" in describe_pird_profile(profile(), "session")["validation_label"]
    synthetic = describe_pird_profile(profile(), "synthetic")
    assert "sintéticos" in synthetic["validation_label"]
    assert "sintéticos" in synthetic["index_note"]
    assert "no documentada" in describe_pird_profile(profile(), "unverified")["validation_label"]
    with pytest.raises(ValueError, match="concilian"):
        describe_pird_profile({"signals_total": 2, "signals_scored": 3})


def test_data_r_view_exposes_reviewed_coverage_and_limits():
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app/streamlit_app.py", default_timeout=30).run()
    app.sidebar.radio[0].set_value("Corpus por proyecto").run()
    app.sidebar.radio[1].set_value("Resumen ejecutivo").run()
    assert not app.exception
    assert next(m.value for m in app.metric if m.label == "PIRD global") == "51.42"
    text = "\n".join(m.value for m in app.markdown)
    assert "260 de 404 señales (64.36 %)" in text
    assert "Señales pendientes de componentes:" in text
    assert "Revisión experta muestral del corpus" in text
    assert "Resultado provisional" not in text
    app.sidebar.selectbox[0].set_value("PDIS").run()
    assert not app.exception
    assert next(m.value for m in app.metric if m.label == "PIRD global") == "Pendiente"
