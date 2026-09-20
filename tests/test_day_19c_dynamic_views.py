from pathlib import Path

from src.frontend.session_project_view import build_session_project_view


ROOT = Path(__file__).resolve().parents[1]


def analysis_fixture():
    return {
        "project_id": "VALIDACION-19C",
        "summary": {
            "signals_validated": 3,
            "signals_scored": 2,
            "signals_pending": 1,
            "scoring_coverage": 2 / 3,
            "global_pird": 44.51,
            "global_level": "MEDIO",
            "profile_status": "PROVISIONAL",
        },
        "classification": {"calibration_status": "PROVISIONAL_NO_PRIVATE_EXAMPLES"},
        "categories": [
            {"category": "Cronograma", "category_score": 52.0, "category_level": "ALTO",
             "scoring_coverage": 1.0, "scored_signals": 1, "total_signals": 1},
            {"category": "Calidad", "category_score": 35.0, "category_level": "MEDIO",
             "scoring_coverage": 0.5, "scored_signals": 1, "total_signals": 2},
        ],
        "timeline": {
            "signals": 3, "source_documents": 2, "signals_with_document_date": 3,
            "signals_without_document_date": 0, "signals_with_persistence": 3,
            "temporal_role_counts": {"APARICION": 2, "RECURRENCIA": 1},
            "persistence_level_counts": {"1": 2, "2": 1},
        },
        "private": {
            "items": [{"evidence_quote": "No debe aparecer"}],
            "validated_signals": [{"statement": "No debe aparecer"}],
            "scored_signals": [
                {"item_id": "A", "pird_status": "CALCULADO", "pird_level": "MEDIO", "evidence_quote": "Privada"},
                {"item_id": "B", "pird_status": "CALCULADO", "pird_level": "ALTO", "evidence_quote": "Privada"},
                {"item_id": "C", "pird_status": "PENDIENTE_ENRIQUECIMIENTO", "pird_level": None},
            ],
        },
    }


def test_day_19c_builds_only_safe_project_aggregates():
    view = build_session_project_view(analysis_fixture(), "Validación académica 19C")

    assert view["source"] == "SESSION_DAY_19B"
    assert view["profile"]["global_pird"] == 44.51
    assert view["profile"]["signals_total"] == 3
    assert view["profile"]["top_categories"] == ["Cronograma", "Calidad"]
    distribution = {row["pird_level"]: row["signal_count"] for row in view["level_distribution"]}
    assert distribution == {"BAJO": 0, "MEDIO": 1, "ALTO": 1, "CRITICO": 0}
    assert view["timeline"]["temporal_role_counts"]["RECURRENCIA"] == 1
    assert view["data_policy"] == {"contains_source_text": False, "contains_individual_signals": False}
    rendered = repr(view)
    assert "evidence_quote" not in rendered
    assert "No debe aparecer" not in rendered
    assert "Privada" not in rendered


def test_day_19c_supports_pending_profile_without_inventing_pird():
    analysis = analysis_fixture()
    analysis["summary"].update({
        "signals_validated": 0, "signals_scored": 0, "signals_pending": 0,
        "scoring_coverage": 0.0, "global_pird": None, "global_level": None,
        "profile_status": "PENDIENTE_SIN_SENALES_VALIDADAS",
    })
    analysis["categories"] = []
    analysis["private"]["scored_signals"] = []

    view = build_session_project_view(analysis, "Sin señales")

    assert view["profile"]["global_pird"] is None
    assert view["profile"]["global_level"] == "PENDIENTE"
    assert view["categories"] == []
    assert all(row["signal_count"] == 0 for row in view["level_distribution"])


def test_day_19c_application_uses_session_view_and_blocks_wrong_chat_scope():
    source = (ROOT / "app/streamlit_app.py").read_text(encoding="utf-8")

    assert "build_session_project_view" in source
    assert "SESSION-19C" in source
    assert "session_project_view is not None" in source
    assert "Día 19C" in source
