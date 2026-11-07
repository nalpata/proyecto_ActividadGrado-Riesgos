from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app/streamlit_app.py"


def test_public_and_synthetic_navigation_remains_operational():
    app = AppTest.from_file(APP, default_timeout=20).run()
    for scope in app.radio[0].options:
        app.radio[0].set_value(scope).run()
        for page in app.radio[1].options:
            app.radio[1].set_value(page).run()
            assert not app.exception, (scope, page)


def test_new_and_replaced_documents_never_show_historical_metrics():
    app = AppTest.from_file(APP, default_timeout=20).run()
    original_project = app.selectbox[0].value
    for name, new in [("Prueba de aislamiento", True), (original_project, False)]:
        app.selectbox[0].set_value("Nuevo proyecto" if new else original_project).run()
        if new:
            app.text_input[0].set_value(name).run()
        app.session_state[f"project_ingestion::{name}"] = {"project_id": "S", "chunks": []}
        for page in ["Resumen ejecutivo", "Radar de riesgos", "Timeline", "Riesgos priorizados", "Perfil del proyecto"]:
            app.radio[1].set_value(page).run()
            assert not app.exception
            assert not app.metric, (name, page)
