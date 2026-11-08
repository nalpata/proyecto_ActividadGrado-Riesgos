"""Synthetic regressions; no private actas or expert labels used in code."""
import json
import numpy as np
import pandas as pd
from src.retrieval.session_retriever import SessionRetriever
from src.risk.session_exposure_grounding import unsupported_closure
from src.risk.build_intelligent_risk_profile import build_prompt, sanitize, SCHEMA
class Encoder:
    def encode(self, texts, **kwargs):
        return np.array([[1., 0.] for _ in texts])
def session(texts):
    return SessionRetriever({'project_id':'SYNTHETIC', 'chunks':[
        dict(project_id='SYNTHETIC',doc_id=f'D{i}',filename=f'file{i}.pdf',page=1,
             chunk_id=f'C{i}',chunk_text=text,embedding=np.array(vector))
        for i,(text,vector) in enumerate(texts)]},Encoder(),top_k=1)
def test_named_project_absent_cannot_reuse_another_projects_figures():
    r=session([('Proyecto independiente. Avance 42%.',[1.,0.])])
    assert r('¿Cuál es el avance NSGA?',[])==[]
    assert len(r('¿Cuál es el avance?',[]))==1

def test_named_project_filter_precedes_top_k_and_document_scope():
    r=session([('Otro proyecto. Avance 42%.',[1.,0.]),('NSGA avance 23%.',[0.,1.])])
    assert r('avance NSGA',[])[0]['doc_id']=='D1'
    assert r('avance NSGA',['D0'])==[]
    assert r('avance',[])[0]['doc_id']=='D0'

def test_alias_requires_word_boundary():
    r=session([('Otro proyecto, NSGAX es un identificador ajeno.',[1.,0.])])
    assert r('NSGA',[])==[]

def test_old_closed_extraction_label_does_not_override_independent_assessment():
    row=dict(exposure_status='CERRADA',assessed_exposure_status='ABIERTA',
             exposure_justification='La falta de recursos requiere gestión.',
             evidence_verified=1,evidence_quote='Faltan recursos para realizar pruebas.')
    assert not unsupported_closure(row)
    row['assessed_exposure_status']='CERRADA'
    assert unsupported_closure(row)
    row['assessed_exposure_status']='ABIERTA'
    row['exposure_justification']='La condición quedó resuelta.'
    assert unsupported_closure(row)

def test_independent_status_is_required_and_extraction_label_not_in_prompt():
    batch=pd.DataFrame([dict(item_id='X',calibrated_type='RIESGO',calibrated_category='Otro',
       exposure_status='CERRADA',title='Faltan recursos',statement='No hay recursos',
       evidence_quote='No hay recursos suficientes para probar.')])
    payload=json.loads(build_prompt(batch).split('SEÑALES:\n')[1])
    assert 'exposure_status' not in payload[0]
    required=SCHEMA['json_schema']['schema']['properties']['assessments']['items']['required']
    assert 'assessed_exposure_status' in required
    out=sanitize(dict(assessed_exposure_status='ABIERTA',severity=3,severity_supported=1,
                     probability=4,probability_supported=1),'X')
    assert out['assessed_exposure_status']=='ABIERTA'
    assert out['severity']==3 and out['probability']==4
