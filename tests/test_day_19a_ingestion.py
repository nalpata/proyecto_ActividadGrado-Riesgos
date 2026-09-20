from io import BytesIO
from pathlib import Path

import fitz
import numpy as np
from docx import Document

from src.pipeline.project_ingestion import (
    CHUNK_OVERLAP_CHARS,
    CHUNK_SIZE_CHARS,
    ingest_project_documents,
    recursive_character_chunks,
    validate_uploads,
)


ROOT = Path(__file__).resolve().parents[1]


class FakeEncoder:
    def encode(self, texts, **kwargs):
        assert kwargs["normalize_embeddings"] is True
        vectors = []
        for index, text in enumerate(texts, start=1):
            vector = np.asarray([len(text), index, 1.0], dtype=np.float32)
            vectors.append(vector / np.linalg.norm(vector))
        return np.vstack(vectors)


def pdf_bytes(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    content = document.tobytes()
    document.close()
    return content


def docx_bytes(text: str) -> bytes:
    document = Document()
    document.add_paragraph(text)
    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


def test_recursive_chunking_preserves_approved_size_and_overlap_configuration():
    text = " ".join(f"palabra{index}." for index in range(900))
    chunks = recursive_character_chunks(text)

    assert len(chunks) > 1
    assert all(len(chunk) <= CHUNK_SIZE_CHARS for chunk in chunks)
    assert CHUNK_SIZE_CHARS == 2200
    assert CHUNK_OVERLAP_CHARS == 300


def test_project_ingestion_extracts_chunks_and_normalized_bge_compatible_vectors():
    result = ingest_project_documents(
        "Proyecto académico",
        [
            {"name": "acta.pdf", "content": pdf_bytes("Retraso documentado y compromiso pendiente. " * 20)},
            {"name": "informe.docx", "content": docx_bytes("Hallazgo de calidad con evidencia verificable. " * 20)},
        ],
        FakeEncoder(),
    )

    assert result["summary"]["documents_processed"] == 2
    assert result["summary"]["documents_rejected"] == 0
    assert result["summary"]["chunks"] == len(result["chunks"])
    assert result["summary"]["embedding_dimensions"] == 3
    assert result["configuration"]["embedding_model"] == "BAAI/bge-m3"
    assert result["configuration"]["persistence"] == "session_memory_only"
    assert all(item["project_id"] == "Proyecto-academico" for item in result["chunks"])
    assert all(np.isclose(np.linalg.norm(item["embedding"]), 1.0) for item in result["chunks"])


def test_project_ingestion_rejects_duplicate_in_same_batch_without_duplicating_chunks():
    content = pdf_bytes("Evidencia de retraso. " * 30)
    result = ingest_project_documents(
        "P1",
        [{"name": "a.pdf", "content": content}, {"name": "copia.pdf", "content": content}],
        FakeEncoder(),
    )

    assert result["summary"]["documents_processed"] == 1
    assert result["summary"]["documents_rejected"] == 1
    assert result["summary"]["status"] == "COMPLETED_WITH_WARNINGS"
    assert result["errors"][0]["error"] == "Documento duplicado en la misma carga"


def test_upload_validation_rejects_unsupported_or_empty_documents():
    for files in (
        [{"name": "datos.csv", "content": b"a,b"}],
        [{"name": "vacio.pdf", "content": b""}],
    ):
        try:
            validate_uploads(files)
            raise AssertionError("La carga inválida debía rechazarse")
        except ValueError:
            pass


def test_day_19a_interface_exposes_explicit_processing_action():
    source = (ROOT / "app/streamlit_app.py").read_text(encoding="utf-8")

    assert "Procesar documentos · Día 19A" in source
    assert "ingest_project_documents" in source
    assert "Día 19B" in source

