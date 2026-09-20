from pathlib import Path

from src.frontend.dashboard_data import NAVIGATION, SUPPORTED_DOCUMENT_TYPES, load_front_snapshot

ROOT = Path(__file__).resolve().parents[1]


def test_day_15_has_all_planned_navigation_sections():
    assert NAVIGATION == (
        "Portada", "Proyectos y documentos", "Resumen ejecutivo", "Radar de riesgos", "Timeline", "Riesgos priorizados",
        "Perfil del proyecto", "Pregunte a sus documentos", "Metodología y métricas",
    )


def test_document_module_accepts_expected_technical_formats():
    assert SUPPORTED_DOCUMENT_TYPES == ("pdf", "docx")


def test_front_loads_only_the_frozen_public_contract():
    snapshot = load_front_snapshot(ROOT / "results/day_14/backend_snapshot_v1.json")
    assert snapshot["schema_version"] == "1.0.0"
    assert snapshot["contract_status"] == "FROZEN"
    assert snapshot["data_policy"]["aggregate_only"] is True
    assert snapshot["data_policy"]["contains_source_text"] is False
    assert snapshot["data_policy"]["contains_individual_signals"] is False


def test_streamlit_structure_does_not_reference_private_evidence_files():
    source = (ROOT / "app/streamlit_app.py").read_text(encoding="utf-8")
    forbidden = ("timeline_riesgos.csv", "riesgos_priorizados.csv", "evidence_quote", "chunk_text")
    assert all(item not in source for item in forbidden)


def test_cover_uses_the_approved_system_title():
    source = (ROOT / "app/streamlit_app.py").read_text(encoding="utf-8")
    assert "Sistema inteligente de vigilancia de riesgo documental" in source
    assert "Retrieval-Augmented Generation (RAG)" in source
