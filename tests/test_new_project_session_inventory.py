"""El análisis de un proyecto nuevo no debe consultar el inventario del corpus histórico."""
from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_new_project_with_session_analysis_does_not_lookup_historical_project():
    app = AppTest.from_file(str(ROOT / 'app/streamlit_app.py'), default_timeout=30).run()
    app.sidebar.selectbox[0].select('Nuevo proyecto').run()
    next(w for w in app.text_input if w.label == 'Nombre del proyecto').set_value('PRUEBA REGRESION').run()
    app.session_state['project_risk_analysis::PRUEBA REGRESION'] = {
        'project_id': 'PRUEBA-REGRESION',
        'summary': {'signals_validated': 1, 'signals_scored': 1, 'signals_pending': 0,
                    'scoring_coverage': 1.0, 'global_pird': 50.0, 'global_level': 'ALTO',
                    'profile_status': 'PROVISIONAL'},
        'classification': {'calibration_status': 'PROVISIONAL_NO_PRIVATE_EXAMPLES'},
        'categories': [{'category': 'Operación', 'category_score': 50.0, 'category_level': 'ALTO',
                        'scoring_coverage': 1.0, 'scored_signals': 1, 'total_signals': 1}],
        'timeline': {'signals': 1, 'source_documents': 1, 'signals_with_document_date': 1,
                     'temporal_role_counts': {'APARICION': 1}, 'persistence_level_counts': {'1': 1}},
        'private': {'scored_signals': [{'item_id': 'S1', 'pird_status': 'CALCULADO', 'pird_level': 'ALTO'}]},
    }
    app.sidebar.radio[1].set_value('Proyectos y documentos').run()
    assert not app.exception, [e.message for e in app.exception]
    assert any('Proyecto procesado · 1 señales' in entry.value for entry in app.success)
    assert not any('Índice publicado:' in entry.value for entry in app.info)
    assert app.sidebar.selectbox[0].value == 'Nuevo proyecto'


def test_ingestion_inventory_survives_navigation_without_reupload():
    app = AppTest.from_file(str(ROOT / 'app/streamlit_app.py'), default_timeout=30).run()
    app.sidebar.selectbox[0].select('Nuevo proyecto').run()
    next(w for w in app.text_input if w.label == 'Nombre del proyecto').set_value('SESION INVENTARIO').run()
    app.session_state['project_ingestion::SESION INVENTARIO'] = {
        'project_id':'SESION-INVENTARIO',
        'summary':{'documents_processed':1,'pages':2,'chunks':2,'embedding_dimensions':1024},
        'documents':[{'filename':'synthetic.pdf','pages':2,'chunks':2}],
        'errors':[], 'project_scope':{'mode':'USER_DECLARED'},
    }
    app.sidebar.radio[1].set_value('Pregunte a sus documentos').run()
    app.sidebar.radio[1].set_value('Proyectos y documentos').run()
    assert not app.exception, [e.message for e in app.exception]
    assert any(m.label=='Documentos procesados' and m.value=='1' for m in app.metric)
    assert any('Ingesta documental completada' in entry.value for entry in app.success)
    assert any(button.label=='Analizar riesgos' for button in app.button)
    assert not any('Proyecto nuevo · pendiente' in entry.value for entry in app.warning)
