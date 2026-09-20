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

## Arquitectura multiagente del Día 12

El procesamiento se coordina mediante un grafo LangGraph con cuatro funciones delimitadas:

```text
Retrieval Agent -> Risk Extractor Agent -> Risk Validator Agent -> Risk Profiler Agent
```

La orquestación se encuentra en `src/agents/risk_graph.py`. El retrieval conserva consulta original, BGE-M3 y chunking recursivo; HyDE y reranking permanecen descartados. El validador reutiliza la puerta determinista del Día 6 y no añade una llamada LLM. Las operaciones con modelos o artefactos privados se inyectan como dependencias para permitir pruebas reproducibles sin publicar información sensible.

## Automatización de extremo a extremo del Día 13

`src/pipeline/end_to_end.py` conecta el grafo con los embeddings BGE-M3, el catálogo calibrado privado, la respuesta RAG, el perfil agregado aprobado y checkpoints reanudables. Los archivos por señal y los checkpoints se suministran fuera de Git. La función `public_execution_summary` genera métricas publicables sin respuestas, fragmentos ni evidencia.

## Backend congelado del Día 14

`src/pipeline/backend_contract.py` valida y congela el contrato público `1.0.0` que consumirá el front. La salida canónica es `results/day_14/backend_snapshot_v1.json`, compuesta únicamente por agregados conciliados: perfil, categorías, distribución PIRD, sensibilidad y resumen sintético de ejecución. El pipeline maneja respuestas vacías y fallos del generador, y admite un registro JSONL privado sin payload documental. El cierre aprobó 51 pruebas.

## Estructura del front del Día 15

`app/streamlit_app.py` implementa una portada, gestión de proyectos/documentos y siete vistas analíticas. Permite seleccionar el proyecto, recibir y validar archivos PDF/DOCX en la sesión, explorar los agregados aprobados y consultar el corpus procesado mediante el asistente documental. La rama conversacional del pipeline final ejecuta retrieval BGE-M3 y respuesta RAG sin recalcular el PIRD congelado. La aplicación no publica evidencia ni datasets por señal.

## Discriminación por proyecto del Día 18A

`src/risk/project_resolution.py` asigna cada señal a un proyecto únicamente cuando existe evidencia explícita en la propia señal, su cita, el contexto próximo, el chunk o un nombre de archivo dedicado. Los casos con varios proyectos o sin evidencia permanecen como `MULTIPROYECTO` o `PENDIENTE_PROYECTO`; nunca se imputan.

El catálogo real, las asignaciones y los agregados por proyecto no se publican en GitHub. Un despliegue privado puede habilitarlos mediante `PROJECT_CATALOG_JSON` y `PROJECT_SCOPE_JSON` en los secretos del servidor. Sin esos secretos, la aplicación pública ofrece la vista consolidada y una demostración académica claramente rotulada con cuatro proyectos totalmente sintéticos.

## Integración y experiencia de usuario del Día 18B

El asistente utiliza `EndToEndPipeline.run_qa`, una rama explícita del pipeline final que ejecuta la configuración aprobada —consulta original, BGE-M3, Top-k y generación RAG— sin volver a extraer señales ni modificar el perfil PIRD. La interfaz muestra estados de carga, ausencia de evidencia y errores controlados; además incorpora preguntas demostrativas seleccionables.

La carga de PDF/DOCX valida la recepción de documentos en la sesión. La ingesta automática del Día 19A extrae y limpia el texto, aplica el chunking recursivo aprobado y genera embeddings BGE-M3 normalizados en memoria. La extracción de señales y la actualización del radar corresponden al Día 19B.

## Ingesta automática por proyecto del Día 19A

`src/pipeline/project_ingestion.py` procesa documentos PDF/DOCX nuevos sin escribirlos en el repositorio ni en el disco del servidor. Cada ejecución:

1. valida formato, tamaño, cantidad y duplicados;
2. extrae texto y tablas mediante PyMuPDF y python-docx;
3. aplica la limpieza aprobada;
4. utiliza el chunking recursivo seleccionado en el Día 4B, con 2.200 caracteres y 300 de solapamiento;
5. genera embeddings normalizados con `BAAI/bge-m3`;
6. asocia documentos, chunks y vectores al proyecto activo únicamente durante la sesión.

El Día 19A no recalcula todavía señales, recurrencia, persistencia ni PIRD. Esos componentes se conectarán en el Día 19B sobre la salida de ingesta ya validada.

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

## Plan intensivo de cierre

### Día 1: diagnóstico de falsos positivos

El primer paso del cierre final consiste en analizar los falsos positivos de la extracción estructurada de riesgos. Los recursos reproducibles se encuentran en:

```text
notebooks/12_diagnostico_falsos_positivos.ipynb
src/evaluation/analyze_false_positives.py
data/evaluation/risk_validation/README.md
```

El objetivo es establecer el baseline, clasificar las causas de error y producir los insumos para diseñar la etapa posterior de validación de riesgos.

### Día 4A: reranking multilingüe

Se compararon BGE-M3 normal, HyDE y ambas consultas con `BAAI/bge-reranker-v2-m3`. Aunque `hyde_rerank` obtuvo el mayor MRR automático, la auditoría humana ciega favoreció al retrieval normal tanto en relevancia (91,7 % frente a 58,3 %) como en atomicidad de los fragmentos (83,3 % frente a 25,0 %).

La configuración seleccionada es **BGE-M3 normal, sin HyDE ni reranking**. Los resultados agregados y las limitaciones están documentados en `docs/resultados_dia_04a.md`. El siguiente experimento evaluará chunking estructural sin cambiar la estrategia de recuperación.

### Día 4B: chunking estructural

Se comparó el chunking recursivo actual con una variante que respeta páginas, títulos, párrafos, listas y oraciones. Aunque la variante redujo el tamaño máximo de 378 a 210 palabras, no mejoró la relevancia humana y obtuvo menor atomicidad (41,7 % frente a 58,3 %). También redujo Precision@1 de 0,75 a 0,50 y MRR de 0,846 a 0,717.

Se conserva el **chunking recursivo actual**. La estrategia final de recuperación es consulta original + BGE-M3 + chunking actual, sin HyDE y sin reranking. Los resultados están documentados en `docs/resultados_dia_04b.md`.

### Día 5: extracción documental mejorada

Se implementó una extracción estructurada que diferencia riesgo, hecho ocurrido, compromiso, acción correctiva, hallazgo e información contextual, exige evidencia literal y separa el tipo documental de la decisión de vigilancia.

La configuración seleccionada usa un clasificador calibrado con 29 decisiones humanas y evaluación leave-one-out. Obtuvo Precision 0,818, Recall 0,857 y F1 0,837 para vigilancia, y 0,828 de exactitud en suficiencia de evidencia. Reclasificó 1.049 elementos y seleccionó 649 señales documentales.

La exactitud del tipo documental fue 0,345. Por ello, la taxonomía y la categoría se mantienen como atributos auxiliares; la señal operativa principal es `calibrated_watch`. Los resultados completos no se publican porque contienen fragmentos de documentos fuente. La metodología, las métricas agregadas y el código reproducible están disponibles en `docs/plan_dia_05.md`, `results/day_05/` y `src/risk/`.

### Día 6: agente validador

La salida calibrada del Día 5 se integró en una puerta final, determinista y explicable. El agente acepta únicamente elementos con vigilancia positiva, evidencia suficiente y evidencia textual verificada. La confianza se registra, pero no se utiliza como umbral automático.

Sobre 1.049 elementos, aceptó 649 y rechazó 400: 282 por no requerir vigilancia y 118 por evidencia insuficiente. Esta reducción operativa de 38,1 % no implica que todos los rechazos sean falsos positivos confirmados. La evaluación humana sigue siendo la documentada en el Día 5.

El componente reproducible se encuentra en `src/risk/run_validation_agent.py` y su metodología en `docs/plan_dia_06.md`.

### Día 7: evaluación del núcleo

Se compararon el prompt mejorado v2 y la extracción con validación sobre las mismas 29 etiquetas humanas. La validación mantuvo Precision de 81,8 %, aumentó Recall de 42,9 % a 85,7 % y elevó F1 de 56,3 % a 83,7 %. Por tanto, se seleccionó la configuración de extracción + validación.

El núcleo final combina consulta original, BGE-M3 y chunking recursivo, sin HyDE ni reranking, con extracción documental v2, clasificación calibrada y agente validador. El 64,6 % de Precision de la extracción inicial se conserva como referencia histórica no comparable porque no dispone de muestra ni matriz de confusión reproducible.

### Día 8: diseño del índice compuesto de riesgo

Se definió el PIRD en una escala de 0 a 100 separando exposición —severidad, probabilidad, recurrencia y persistencia— de confiabilidad —calidad de evidencia y confianza de extracción—. Los pesos son una hipótesis metodológica explícita y no parámetros aprendidos.

El motor no calcula un score cuando falta cualquiera de los seis componentes: devuelve `PENDIENTE_ENRIQUECIMIENTO`. Por ello, todavía no se asignaron puntajes a las 649 señales; la recurrencia será derivada del clustering del Día 9 y la persistencia del timeline del Día 10.

La sensibilidad sobre cuatro casos controlados y cuatro escenarios conservó el orden de prioridad en todos los escenarios. La máxima variación fue de 14,55 puntos y un caso cambió entre alto y crítico, por lo que el análisis de sensibilidad se conserva como limitación y evidencia metodológica. El diseño está documentado en `docs/diseno_pird_dia_08.md` y es reproducible mediante `src/risk/pird.py` y el notebook 24.

### Día 9: clustering semántico y recurrencia

El experimento representa las 649 señales aceptadas con BGE-M3 y compara entre 2 y 12 clusters mediante Silhouette coseno, Calinski-Harabasz, Davies-Bouldin y estabilidad ARI en cinco semillas. Las categorías existentes no intervienen en la construcción de los grupos; se utilizan posteriormente para medir alineación mediante ARI, NMI y pureza.

La recurrencia del PIRD se deriva del número de documentos distintos donde aparece cada familia, no del número bruto de frases. El código y la metodología están en `src/risk/semantic_clustering.py`, `docs/plan_dia_09.md` y el notebook 25. Las descripciones, evidencias, embeddings y asignaciones por señal se mantienen fuera del repositorio público.

La ejecución seleccionó seis familias exploratorias, con Silhouette 0,077 y estabilidad ARI 0,776. La baja alineación con las categorías existentes (ARI 0,050; NMI 0,140; pureza 0,414) indica que los clusters no deben reemplazar la taxonomía. La recurrencia final utiliza vecinos semánticos en otros documentos con similitud coseno mínima de 0,70 y distribuye las señales en los cinco niveles: 266, 157, 128, 55 y 43.

### Día 10: timeline y persistencia

Se normalizaron fechas documentales desde nombres de archivo con trazabilidad de fuente y precisión. Se fecharon 29 de 35 documentos y 614 de 649 señales. Una fecha fuera del periodo permitido fue marcada como anomalía y no se corrigió automáticamente.

La persistencia semántica pudo calcularse para 638 señales: 304 en nivel 1, 31 en nivel 2, 38 en nivel 3, 24 en nivel 4 y 241 en nivel 5. El timeline diferencia aparición y recurrencia; el escalamiento permanece pendiente porque requiere severidad temporal.

El PIRD no se calculó para ninguna señal porque el catálogo no contiene severidad ni probabilidad estandarizadas. El sistema devuelve este estado de forma explícita. La metodología y los resultados agregados están en `docs/plan_dia_10.md`, `src/risk/build_risk_timeline.py` y `results/day_10/`.

### Día 11: Perfil Inteligente de Riesgo

La etapa final estandariza severidad y probabilidad mediante una rúbrica de cinco niveles aplicada únicamente a la descripción y evidencia. Recurrencia y persistencia se excluyen del prompt para evitar circularidad. Cuando un componente no está sustentado, permanece nulo y el PIRD no se calcula.

El perfil por categoría combina 70 % del PIRD promedio y 30 % del percentil 90. El score global combina 70 % del promedio simple de las categorías y 30 % del mayor score de categoría, evitando que el volumen documental determine por sí solo el resultado. La metodología y el código se encuentran en `docs/plan_dia_11.md`, `src/risk/build_intelligent_risk_profile.py` y el notebook 27.

La ejecución calculó 372 de 649 señales (57,3 %) y produjo un score global provisional de 52,16, nivel alto. Cronograma, Contractual y Financiero obtuvieron los mayores scores de categoría. La sensibilidad de pesos mantuvo el score entre 51,69 y 55,17, pero la cobertura desigual entre categorías exige conservar la etiqueta provisional.

#### Alcance del Gold Standard

El Gold Standard humano construido en los Días 1, 2 y 5 valida la inclusión de señales, la necesidad de vigilancia y la suficiencia de evidencia. No contiene etiquetas humanas de severidad y probabilidad en escala 1–5, pues estos componentes se definieron posteriormente con el PIRD del Día 8. En consecuencia, la evaluación humana existente sigue siendo válida para la detección, mientras que severidad y probabilidad se reportan como evaluaciones estructuradas asistidas por IA.

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
