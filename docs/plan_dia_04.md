# Plan de trabajo · Día 4 · Chunking estructural

## Hallazgo que origina el experimento

La auditoría humana del Día 3 identificó que los chunks recursivos actuales pueden ser demasiado extensos y contener varios riesgos o temas. Esta condición afecta la claridad de la evidencia, la extracción de riesgos y las respuestas del futuro front.

## Pregunta experimental

¿Un chunking orientado a estructura documental y atomicidad mejora la recuperación BGE-M3 y la calidad de la evidencia frente al chunking recursivo actual?

## Comparación controlada

| Elemento | Baseline recursivo | Chunking estructural v2 |
|---|---|---|
| Corpus | Mismos documentos | Mismos documentos |
| Embeddings | BGE-M3 | BGE-M3 |
| Consulta | Pregunta original | Pregunta original |
| Top-k | 5 | 5 |
| Preguntas | 20 gold | Las mismas 20 |
| Juez | Juez v3 validado | El mismo juez v3 |

HyDE y reranking quedan excluidos porque no fueron seleccionados en los experimentos anteriores.

## Diseño del chunking v2

1. Preservar trazabilidad por documento y página.
2. Separar primero por encabezados, párrafos, viñetas y numeraciones.
3. Dividir bloques extensos por oraciones.
4. Agrupar unidades cortas relacionadas sin superar el límite configurado.
5. Mantener un solapamiento pequeño únicamente cuando una unidad exceda el límite.
6. Registrar tamaño, estrategia, sección de origen y posición.

## Métricas

- Cantidad total de chunks.
- Palabras promedio, mediana, percentil 95 y máximo.
- Proporción de chunks fuera del rango objetivo.
- Indicadores heurísticos de múltiples temas o riesgos.
- Precision@1, Precision@3 y Precision@5.
- Hit@1, Hit@3 y Hit@5.
- MRR.
- Tiempo y costo de procesamiento.

## Criterio de selección

El chunking v2 se seleccionará si mejora la atomicidad y legibilidad sin deteriorar materialmente Precision@5 ni MRR. Una mejora de recuperación será favorable, pero no es obligatoria si la evidencia resulta más precisa y trazable.

## Salidas

- Script reproducible de chunking estructural.
- Notebook ejecutable en Colab.
- Chunks v2 en CSV y Parquet.
- Comparación de calidad y recuperación.
- Muestra ciega de control humano.
- Decisión metodológica documentada.
