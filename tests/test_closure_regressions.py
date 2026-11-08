from types import SimpleNamespace
from unittest.mock import Mock
import numpy as np
import pandas as pd
import pytest
import fitz
from src.pipeline.end_to_end import OpenAIRagAnswerer
from src.pipeline.project_ingestion import ingest_project_documents
from src.pipeline import project_risk_processing as processing
from src.frontend.chat_service import ConversationalRagService
from src.frontend.runtime_chat import append_runtime_history


def chunk(rank=1):
    return dict(rank=rank, filename='example.pdf',page=2,chunk_id=f'C{rank}',doc_id='D',score=.8,
                chunk_text='El servicio incluye 12 solicitudes.',section_path='5.2.2 Proyecto Ejemplo')


def answerer(text):
    client=Mock()
    client.chat.completions.create.return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))],usage=None)
    return OpenAIRagAnswerer(client=client),client


def test_grouped_references_preserve_gate_and_original_context():
    a,client=answerer('El servicio incluye 12 solicitudes [1, 2].')
    result=a('¿Qué incluye?', [chunk(1),chunk(2)])
    assert result['response_status']=='COMPLETED'
    assert len(result['sources'])==2
    assert '[1][2]' in result['answer']
    assert '5.2.2 Proyecto Ejemplo' in client.chat.completions.create.call_args.kwargs['messages'][1]['content']


@pytest.mark.parametrize('text', ['Un monto inventado sin cita.', 'Monto [1, 9].'])
def test_invalid_references_never_present_unverified_answer(text):
    a,_=answerer(text)
    result=a('Pregunta', [chunk()])
    assert result['response_status']=='INVALID_CITATIONS'
    assert result['sources']==[] and not result['evidence_available']
    assert len(result['retrieved_sources'])==1
    assert text not in result['answer']


def test_no_retrieval_is_distinct_from_invalid_citations():
    a,client=answerer('irrelevant')
    result=a('Pregunta', [])
    assert result['response_status']=='NO_EVIDENCE'
    client.chat.completions.create.assert_not_called()


def test_retrieval_diagnostics_survive_session_chat_without_chunk_text():
    a,_=answerer('Sin citas')
    result=ConversationalRagService(lambda q, docs:[chunk()], a).ask('Pregunta')
    history=append_runtime_history([],result)
    assert history[0]['retrieved_sources'][0]['section_path']=='5.2.2 Proyecto Ejemplo'
    assert 'chunk_text' not in history[0]['retrieved_sources'][0]


class Encoder:
    def encode(self,texts,**kwargs):
        self.texts=texts
        return np.ones((len(texts),2))


def test_section_metadata_carries_across_pages_without_changing_embedded_text():
    d=fitz.open()
    for text in ['5.2.2 Proyecto Ejemplo\nInicio del seguimiento.', 'El servicio incluye 12 solicitudes.', '5.2.3 Otro Proyecto\nOtro servicio.']:
        p=d.new_page();p.insert_text((72,72),text)
    enc=Encoder()
    result=ingest_project_documents('SESION',[{'name':'example.pdf','content':d.tobytes()}],enc)
    rows=result['chunks']
    assert 'Proyecto Ejemplo' in rows[1]['section_path']
    assert 'Otro Proyecto' in rows[2]['section_path']
    assert 'Proyecto Ejemplo' not in rows[2]['section_path']
    assert enc.texts==[r['chunk_text'] for r in rows]


def test_extraction_resume_does_not_repeat_completed_calls_and_rejects_changed_input(monkeypatch):
    chunks=pd.DataFrame([dict(chunk_id='C1',chunk_text='Uno'),dict(chunk_id='C2',chunk_text='Dos')])
    calls=[]
    def call(client,prompt):
        calls.append(prompt)
        if len(calls)==2: raise RuntimeError('network')
        return '[]',None
    monkeypatch.setattr(processing,'build_extraction_prompt',lambda row:row.chunk_text)
    monkeypatch.setattr(processing,'call_extraction_model',call)
    state={};events=[]
    with pytest.raises(RuntimeError): processing._extract_items(chunks,None,lambda *x:events.append(x),state)
    processing._extract_items(chunks,None,lambda *x:events.append(x),state)
    assert calls==['Uno','Dos','Dos']
    changed=chunks.copy();changed.loc[0,'chunk_text']='Nuevo'
    processing._extract_items(changed,None,checkpoint=state)
    assert calls[-2:]==['Nuevo','Dos']
    assert events[-1]==('Extracción',2,2)


def test_differing_mentions_are_flagged_without_overwriting_or_crossing_documents():
    frame=pd.DataFrame([dict(source_doc_id='D1',title='Alerta',severity=3,probability=4),dict(source_doc_id='D1',title='Alerta',severity=2,probability=4),dict(source_doc_id='D2',title='Alerta',severity=5,probability=5)])
    marked=processing.flag_assessment_discrepancies(frame)
    assert marked.assessment_review_required.tolist()==[True,True,False]
    pd.testing.assert_frame_equal(marked[frame.columns],frame)
