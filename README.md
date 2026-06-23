# Proyecto MIA - Sistema Inteligente de Vigilancia de Riesgos basado en RAG

## Descripción general

Este repositorio contiene el desarrollo de un prototipo académico para consultar, analizar y priorizar riesgos documentales en procesos de aseguramiento técnico e interventoría, utilizando técnicas de Recuperación Aumentada por Generación (RAG), búsqueda semántica, evaluación de recuperación de información y visualización interactiva.

El proyecto busca demostrar cómo un sistema basado en inteligencia artificial puede apoyar la revisión de documentos técnicos, facilitando la identificación de señales tempranas de riesgo, la recuperación de evidencia trazable y la recomendación de documentos relacionados.

## Objetivo del proyecto

Diseñar, implementar y evaluar un prototipo basado en RAG para consultar documentos de aseguramiento técnico, recuperar evidencia documental, recomendar documentos relacionados e identificar señales tempranas de riesgo asociadas a compromisos, incumplimientos, retrasos, ANS, calidad y acciones correctivas.

## Alcance funcional

El prototipo incluye los siguientes componentes:

1. Organización de un corpus documental inicial.
2. Extracción de texto desde documentos PDF y DOCX.
3. Limpieza y preprocesamiento de texto.
4. Construcción de inventario documental.
5. División del corpus en chunks para recuperación.
6. Generación de embeddings y comparación de modelos.
7. Evaluación de recuperación con preguntas tipo gold standard.
8. Implementación de baseline RAG.
9. Evaluación de resultados de retrieval y reranking.
10. Identificación y priorización de señales de riesgo.
11. Construcción de timeline y radar de riesgos.
12. Visualización en una aplicación Streamlit.

## Estructura del repositorio

```text
proyecto_ActividadGrado-Riesgos/
│
├── app/
│   └── streamlit_app.py              # Dashboard interactivo de riesgos
│
├── data/
│   ├── raw/                          # Documentos originales del corpus
│   ├── processed/
│   │   ├── text/                      # Texto extraído desde PDF/DOCX
│   │   ├── clean_text/                # Texto limpio
│   │   ├── chunks/                    # Chunks generados para RAG
│   │   ├── embedding/                 # Resultados de embeddings
│   │   └── retrieval/                 # Resultados y métricas de recuperación
│   │
│   ├── evaluation/                    # Inventarios, preguntas gold y métricas
│   │   └── timeline/                  # Archivos para radar y timeline de riesgos
│   │
│   └── RAG/                           # Resultados y notebooks del baseline RAG
│
├── docs/
│   └── evidencias/                    # Evidencias y resúmenes del avance
│
├── src/
│   ├── ingestion/                     # Scripts de extracción de texto
│   ├── preprocessing/                 # Limpieza e inventario documental
│   ├── retrieval/                     # Recuperación, embeddings y vector store
│   └── risk/                          # Reglas, scoring y priorización de riesgo
│
├── requirements.txt                   # Dependencias principales del proyecto
├── .gitignore                         # Archivos y carpetas excluidos del repositorio
└── README.md                          # Documentación principal
```

## Corpus documental

El corpus inicial está compuesto por documentos de seguimiento, actas, comunicados y documentos asociados a procesos de aseguramiento técnico/interventoría.

Resumen inicial del corpus:

- Total de documentos: 14
- PDFs: 9
- DOCX: 5
- Actas / reviews: 3
- Comunicados: 11
- Páginas PDF extraídas: 29
- Palabras extraídas: 19.079
- Posibles documentos escaneados: 0

> Nota: para efectos académicos y de publicación pública, se recomienda anonimizar o reemplazar información sensible antes de compartir el repositorio con terceros.

## Flujo metodológico

El flujo general del proyecto es el siguiente:

```text
Documentos originales
        ↓
Extracción de texto
        ↓
Limpieza y normalización
        ↓
Inventario documental
        ↓
Chunking
        ↓
Embeddings / recuperación semántica
        ↓
Evaluación con preguntas gold
        ↓
Baseline RAG y reranking
        ↓
Extracción y priorización de riesgos
        ↓
Dashboard Streamlit
```

## Preguntas de evaluación

Se construyó un conjunto de preguntas tipo gold standard para evaluar la capacidad del sistema de recuperar evidencia documental relevante. Las preguntas cubren temas como:

- Incumplimientos contractuales.
- Compromisos vencidos o no cumplidos.
- Riesgos de retraso.
- Riesgos asociados a despliegues.
- ANS afectados o incumplidos.
- Acciones correctivas.
- Hallazgos de calidad.
- Recomendación documental.
- Timeline de riesgos.

Estas preguntas se encuentran en:

```text
data/evaluation/gold_questions.csv
```

## Métricas utilizadas

Para evaluar el desempeño del sistema de recuperación se utilizaron métricas como:

- Precision@1
- Precision@3
- Precision@5
- Hit@1
- Hit@3
- Hit@5
- MRR (Mean Reciprocal Rank)

Los resultados de evaluación se encuentran principalmente en:

```text
data/processed/retrieval/retrieval_metrics_by_question.csv
data/processed/retrieval/retrieval_metrics_by_category.csv
data/evaluation/rerankin/reranking_metrics_by_question.csv
```

## Modelos de embeddings evaluados

En el proyecto se compararon modelos de embeddings para recuperación semántica, incluyendo:

- `sentence-transformers/all-MiniLM-L6-v2`
- `BAAI/bge-m3`

Los resultados comparativos se encuentran en:

```text
data/processed/embedding/resumen_embeddings_comparison.csv
```

## Aplicación Streamlit

El repositorio incluye una aplicación interactiva para visualizar el radar de riesgos documentales.

La aplicación permite:

- Filtrar riesgos por categoría, prioridad y severidad.
- Visualizar indicadores generales.
- Revisar distribución de riesgos por categoría y prioridad.
- Explorar un timeline de riesgos documentales.
- Consultar un radar por score promedio de riesgo.
- Revisar evidencia documental y acciones recomendadas.

Archivo principal:

```text
app/streamlit_app.py
```

## Instalación y ejecución

### 1. Clonar el repositorio

```bash
git clone https://github.com/nalpata/proyecto_ActividadGrado-Riesgos.git
cd proyecto_ActividadGrado-Riesgos
```

### 2. Crear y activar ambiente virtual

En Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

En macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Ejecutar scripts principales

Extracción de texto:

```bash
python src/ingestion/extract_text.py
```

Limpieza de texto:

```bash
python src/preprocessing/clean_text.py
```

Construcción de inventario:

```bash
python src/preprocessing/build_inventory.py
```

### 5. Ejecutar dashboard

```bash
streamlit run app/streamlit_app.py
```

## Principales salidas del proyecto

Algunas de las salidas generadas por el prototipo son:

```text
data/evaluation/inventario_corpus.csv
data/evaluation/gold_questions.csv
data/processed/chunks/resumen_chunking.csv
data/processed/embedding/resumen_embeddings_comparison.csv
data/processed/retrieval/retrieval_metrics_by_question.csv
data/RAG/rag_baseline_results.csv
data/evaluation/timeline/timeline_riesgos.csv
data/evaluation/timeline/radar_riesgos_resumen.csv
data/evaluation/timeline/riesgos_priorizados.csv
```

## Estado actual del proyecto

El proyecto cuenta actualmente con:

- Corpus inicial organizado.
- Extracción y limpieza de texto.
- Inventario documental.
- Chunking del corpus.
- Preguntas gold para evaluación.
- Evaluación de recuperación semántica.
- Comparación de modelos de embeddings.
- Baseline RAG.
- Resultados de reranking.
- Identificación y priorización de riesgos.
- Dashboard inicial en Streamlit.

## Próximos pasos sugeridos

Para fortalecer el proyecto antes de la entrega final, se recomienda:

1. Renombrar la carpeta `data/evaluation/rerankin/` a `data/evaluation/reranking/`.
2. Mover notebooks desde `data/RAG/` hacia una carpeta `notebooks/`.
3. Anonimizar documentos, nombres propios y evidencias sensibles.
4. Documentar con mayor detalle la metodología de scoring de riesgos.
5. Consolidar resultados finales en una tabla resumen de métricas.
6. Agregar capturas del dashboard en `docs/evidencias/`.
7. Incluir una sección de limitaciones del prototipo.
8. Preparar una versión sintética del corpus si el repositorio se mantiene público.

## Consideraciones de confidencialidad

Este proyecto fue desarrollado con fines académicos. Si se utilizan documentos reales de proyectos, contratos, interventorías o comunicaciones empresariales, se debe validar previamente que su publicación esté permitida.

Antes de compartir este repositorio públicamente se recomienda:

- Eliminar o anonimizar nombres de clientes, proveedores y personas.
- Reemplazar documentos reales por versiones sintéticas o enmascaradas.
- Evitar publicar contratos, actas o comunicaciones confidenciales.
- Mantener fuera del repositorio archivos pesados, bases vectoriales locales, claves o credenciales.

## Autora

Patricia Patiño  
Maestría en Inteligencia Artificial  
Proyecto aplicado / Trabajo de grado
