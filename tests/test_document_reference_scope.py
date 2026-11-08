from unittest.mock import Mock
import pytest
from src.retrieval.document_reference_scope import (
    DocumentReferenceScopedRetriever, requested_document_dates, filename_document_date,
)

DOCUMENTS = [dict(doc_id='A', filename='acta_20250303.pdf'),
             dict(doc_id='B', filename='acta_20250404.pdf')]


def test_requested_acta_date_filters_documents_without_rewriting_question():
    backend = Mock(return_value=[{'rank': 1}])
    retriever = DocumentReferenceScopedRetriever(backend, DOCUMENTS)
    question = 'Según el acta del 04/04/2025, ¿qué entrega se previó para el 10/05/2025?'
    assert retriever(question, []) == [{'rank': 1}]
    backend.assert_called_once_with(question, ['B'])


@pytest.mark.parametrize('question', [
    '¿Qué estimación se previó para el 04/04/2025?',
    '¿Qué pasó el 04/04/2025?',
    '¿Puede atribuirse al proyecto Ejemplo la entrega del 04/04/2025?',
])
def test_event_date_does_not_become_document_scope(question):
    backend = Mock(return_value=[])
    DocumentReferenceScopedRetriever(backend, DOCUMENTS)(question, ['A'])
    backend.assert_called_once_with(question, ['A'])


@pytest.mark.parametrize('question', [
    'Según el acta del 05/05/2025, ¿qué ocurrió?',
    'Según el acta del 31/02/2025, ¿qué ocurrió?',
])
def test_missing_or_invalid_document_date_never_falls_back_to_other_actas(question):
    backend = Mock()
    assert DocumentReferenceScopedRetriever(backend, DOCUMENTS)(question, []) == []
    backend.assert_not_called()


def test_caller_document_scope_is_intersected_never_expanded():
    backend = Mock()
    assert DocumentReferenceScopedRetriever(backend, DOCUMENTS)('Acta del 04/04/2025', ['A']) == []
    backend.assert_not_called()


def test_two_explicit_document_dates_are_a_union():
    assert requested_document_dates('Actas del 03/03/2025 y 04/04/2025') == {'2025-03-03','2025-04-04'}


def test_ambiguous_filename_dates_are_not_guessed():
    assert filename_document_date('acta_20250303_revision_20250404.pdf') is None
    assert filename_document_date('acta_20250404.pdf') == '2025-04-04'
