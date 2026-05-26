# Proyecto MIA - RAG para aseguramiento técnico e identificación de riesgos

## Objetivo
Diseñar, implementar y evaluar un prototipo basado en RAG para consultar documentos de aseguramiento técnico, recuperar evidencia trazable, recomendar documentos relacionados e identificar señales tempranas de riesgo.

## Corpus inicial
El corpus inicial contiene documentos de seguimiento/interventoría en formatos PDF y DOCX.

Resumen inicial:
- Total documentos: 14
- PDFs: 9
- DOCX: 5
- Actas / reviews: 3
- Comunicados: 11
- Páginas PDF extraídas: 29
- Palabras extraídas: 19079
- Posibles documentos escaneados: 0

## Estructura del repositorio
```text
data/
  raw/                  # documentos originales
  processed/text/        # texto extraído
  processed/clean_text/  # texto limpio
  processed/chunks/      # chunks para RAG
  evaluation/            # inventarios y métricas
src/
  ingestion/             # extracción de texto
  preprocessing/         # limpieza e inventario
  retrieval/             # búsqueda keyword, embeddings, vector store
  risk/                  # reglas y scoring de riesgo
app/
  streamlit_app.py       # interfaz futura
docs/
  evidencias/            # evidencias de avance
```

## Avance actual
1. Corpus inicial organizado.
2. Extracción inicial de texto.
3. Inventario documental creado.
4. Conteo preliminar de señales de riesgo por documento.

## Próximos pasos
1. Limpieza documental.
2. Chunking inicial.
3. Baseline de búsqueda por palabras clave.
4. Definición de preguntas de evaluación.
5. RAG inicial con trazabilidad a fuente.
