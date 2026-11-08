"""Contratos del detalle privado usando únicamente señales sintéticas."""
import hashlib
import pandas as pd
import pytest
from src.frontend.risk_details import load_corpus_risk_details, select_project_risk_details, filter_risk_details
from src.risk.project_resolution import build_public_project_snapshot


@pytest.fixture
def sample():
    frame = pd.DataFrame([
        dict(item_id='S1', project_id='A', project_assignment_status='ASSIGNED_SIGNAL_EXPLICIT',
             pird_status='CALCULADO', pird=60.0, pird_level='ALTO', calibrated_category='Calidad',
             source_doc_id='D1', document_date='2024-01-01', temporal_role='APARICION', persistence_level=1,
             title='Calidad [pendiente]', statement='Ejemplo sintético', evidence_quote='Cita sintética', source_filename='demo.pdf'),
        dict(item_id='S2', project_id='A', project_assignment_status='ASSIGNED_SIGNAL_EXPLICIT',
             pird_status='PENDIENTE_ENRIQUECIMIENTO', pird=None, pird_level=None, calibrated_category='Calidad',
             source_doc_id='D2', document_date=None, temporal_role='PENDIENTE_FECHA', persistence_level=None,
             title='Otra señal', statement='Ejemplo sintético', evidence_quote='Sin nivel', source_filename='demo2.pdf'),
        dict(item_id='S3', project_id='B', project_assignment_status='ASSIGNED_SIGNAL_EXPLICIT',
             pird_status='CALCULADO', pird=20.0, pird_level='BAJO', calibrated_category='Calidad',
             source_doc_id='D3', document_date=None, temporal_role='APARICION', persistence_level=1,
             title='Proyecto B', statement='Ejemplo sintético', evidence_quote='Cita B', source_filename='demo3.pdf'),
        dict(item_id='S4', project_id='A', project_assignment_status='MULTI_PROJECT_SIGNAL',
             pird_status='PENDIENTE_ASIGNACION_PROYECTO', pird=None, pird_level=None, calibrated_category='Calidad',
             source_doc_id='D4', document_date=None, temporal_role=None, persistence_level=None,
             title='Compartida', statement='No asignada exclusivamente', evidence_quote='Cita compartida', source_filename='demo4.pdf'),
    ])
    catalog={'projects':[{'project_id':'A','display_name':'A'},{'project_id':'B','display_name':'B'}]}
    scope=build_public_project_snapshot(frame,catalog)
    payload=frame.to_csv(index=False).encode('utf-8-sig')
    manifest={'sha256':hashlib.sha256(payload).hexdigest(),'rows':4,'assigned_rows':3,'scored_rows':2}
    return frame,catalog,scope,payload,manifest


def test_project_scope_excludes_shared_rows(sample):
    frame,*_=sample
    assert select_project_risk_details(frame,'A').item_id.tolist()==['S1','S2']
    assert select_project_risk_details(frame,'B').item_id.tolist()==['S3']
    assert select_project_risk_details(frame,'UNKNOWN').empty


def test_pending_literal_search_and_empty_filters(sample):
    frame,*_=sample
    selected=select_project_risk_details(frame,'A')
    assert filter_risk_details(selected,status='Pendientes').item_id.tolist()==['S2']
    assert filter_risk_details(selected,query='[pendiente]').item_id.tolist()==['S1']
    assert filter_risk_details(selected,categories=[]).empty
    assert filter_risk_details(selected,levels=['ALTO']).item_id.tolist()==['S1']


def test_load_matches_snapshot_and_rejects_changes(sample):
    frame,catalog,scope,payload,manifest=sample
    assert len(load_corpus_risk_details(payload,manifest,catalog,scope))==4
    with pytest.raises(ValueError):
        load_corpus_risk_details(payload+b'\n',manifest,catalog,scope)
    scope['projects'][0]['profile']['signals_scored']=999
    with pytest.raises(ValueError):
        load_corpus_risk_details(payload,manifest,catalog,scope)


def test_duplicate_ids_are_rejected_even_with_matching_hash(sample):
    frame,catalog,scope,_,manifest=sample
    frame.loc[1,'item_id']='S1'
    payload=frame.to_csv(index=False).encode('utf-8-sig')
    manifest['sha256']=hashlib.sha256(payload).hexdigest()
    with pytest.raises(ValueError):
        load_corpus_risk_details(payload,manifest,catalog,scope)
