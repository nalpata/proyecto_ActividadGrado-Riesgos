from copy import deepcopy
import pytest
from src.risk.session_exposure_grounding import affirmed_closure, review_session_analysis


def example_analysis():
    # Ejemplo fabricado para probar el control; no es una revisión experta ni un acta real.
    common = dict(source_doc_id='D', source_page=1, evidence_verified=1,
                  calibrated_category='Otro', persistence_level=1, recurrence_level=1,
                  pird_status='CALCULADO', pird_level='MEDIO', exposure_status='ABIERTA',
                  pird_missing_components='')
    rows = [dict(common, item_id='R1', title='Demanda insuficiente', severity=3, probability=4,
                 pird=37.35, evidence_quote='Se mantiene una demanda inferior a la prevista.',
                 exposure_justification='La condición abierta requiere gestión.'),
            dict(common, item_id='A1', title='Solicitud de plan de capacidad', severity=2, probability=1,
                 pird=9.76, evidence_quote='Se solicitó entregar un plan de capacidad.',
                 exposure_justification='La exposición está cerrada.')]
    return dict(project_id='SYNTHETIC', summary=dict(signals_validated=2, signals_scored=2,
                signals_pending=0, scoring_coverage=1.0, global_pird=30.0, global_level='MEDIO',
                profile_status='CALCULADO'), categories=[], private=dict(scored_signals=rows),
                classification={}, timeline={})


@pytest.mark.parametrize('text', ['Se cerró el incumplimiento.', 'La observación fue resuelta.',
                                'La condición quedó subsanada.'])
def test_affirmative_closure_is_recognized(text):
    assert affirmed_closure(text)


@pytest.mark.parametrize('text', ['Se solicitó un plan de capacidad.', 'El cierre está pendiente.',
                                'No se ha cerrado el incumplimiento.', 'No consta que esté resuelta.',
                                'Sin evidencia de que se haya cerrado.'])
def test_request_or_negated_closure_is_not_closure(text):
    assert not affirmed_closure(text)


def test_unsupported_closure_is_pending_not_assumed_open_or_replaced_by_expert():
    original = example_analysis()
    retained = deepcopy(original)
    updated = review_session_analysis(original)
    assert original == retained  # No mutar evidencia original.
    risk, request = updated['private']['scored_signals']
    assert risk['severity']==3 and risk['probability']==4
    assert request['severity'] is None and request['probability'] is None
    assert request['pird'] is None and request['pird_status']=='PENDIENTE_ENRIQUECIMIENTO'
    assert request['exposure_status']=='INDETERMINADA'
    assert request['exposure_grounding_original']['probability']==1
    assert request['exposure_grounding_original']['exposure_justification']=='La exposición está cerrada.'
    assert request['exposure_justification'] != 'La exposición está cerrada.'
    assert updated['summary']['signals_validated']==2
    assert updated['summary']['signals_scored']==1
    assert updated['summary']['signals_pending']==1
    assert updated['summary']['scoring_coverage']==.5
    assert updated['categories'][0]['total_signals']==2
    assert updated['categories'][0]['scored_signals']==1
    assert review_session_analysis(updated) == updated


def test_other_activity_closure_in_context_is_not_proof_of_request_fulfillment():
    analysis = example_analysis()
    analysis['private']['scored_signals'][1]['source_context']='La instalación fue cerrada. Se solicitó un plan de capacidad.'
    assert review_session_analysis(analysis)['summary']['signals_pending']==1


def test_verified_explicit_closure_of_the_signal_keeps_original_value():
    analysis=example_analysis()
    analysis['private']['scored_signals'][1]['evidence_quote']='Se cerró la observación sobre el plan de capacidad.'
    assert review_session_analysis(analysis)==analysis


def test_unverified_quote_cannot_prove_closure():
    analysis=example_analysis()
    analysis['private']['scored_signals'][1].update(evidence_verified=0,
        evidence_quote='Se cerró la observación sobre el plan de capacidad.')
    assert review_session_analysis(analysis)['summary']['signals_pending']==1


def test_no_complete_scores_keeps_profile_pending_without_dropping_signals():
    analysis=example_analysis()
    analysis['private']['scored_signals']=analysis['private']['scored_signals'][1:]
    analysis['summary'].update(signals_validated=1, signals_scored=1)
    result=review_session_analysis(analysis)
    assert result['summary']['signals_validated']==1
    assert result['summary']['signals_scored']==0
    assert result['summary']['global_pird'] is None
    assert result['categories']==[]


def test_inconsistent_denominator_is_not_silently_published():
    analysis=example_analysis()
    analysis['summary']['signals_validated']=99
    with pytest.raises(ValueError, match='denominador'):
        review_session_analysis(analysis)


def test_app_reviews_preexisting_session_before_building_views():
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    root=Path(__file__).resolve().parents[1]
    app=AppTest.from_file(str(root/'app/streamlit_app.py'),default_timeout=30).run()
    app.sidebar.selectbox[0].select('Nuevo proyecto').run()
    next(w for w in app.text_input if w.label=='Nombre del proyecto').set_value('CIERRE CONTROL').run()
    app.session_state['project_risk_analysis::CIERRE CONTROL']=example_analysis()
    app.run()
    assert not app.exception, [e.message for e in app.exception]
    reviewed=app.session_state['project_risk_analysis::CIERRE CONTROL']
    assert reviewed['summary']['signals_scored']==1
    assert reviewed['private']['scored_signals'][1]['probability'] is None
    assert reviewed['private']['scored_signals'][0]['probability']==4
