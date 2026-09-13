# Plan de trabajo · Día 5 · Extracción mejorada

## Objetivo

Extraer elementos documentales diferenciando riesgo, hecho ocurrido, compromiso, acción correctiva, hallazgo e información contextual, sin convertir automáticamente cada elemento en riesgo.

## Principios

- Clasificación primaria excluyente por función documental.
- Cita textual literal de máximo 45 palabras.
- Verificación automática de que la evidencia existe en el chunk.
- Separación entre `item_type` y `surveillance_candidate`.
- Responsable y fecha solo cuando aparecen explícitamente.
- Sin acciones recomendadas inventadas.
- Checkpoint por chunk para reanudar la ejecución.

## Corpus y modelo

- 345 chunks del corpus recursivo seleccionado en el Día 4B.
- Modelo `gpt-4o-mini`, temperatura 0 y salida JSON Schema estricta.
- Una llamada por chunk para conservar trazabilidad y evitar mezclar fuentes.

## Evaluación

La evaluación se realizó en tres iteraciones y se cerró con 29 etiquetas humanas completas. No se solicitarán nuevas auditorías manuales.

## Resultado final

| Métrica | v1 | v2 | Clasificador calibrado |
|---|---:|---:|---:|
| Precision de vigilancia | 0,625 | 0,818 | **0,818** |
| Recall de vigilancia | 0,833 | 0,429 | **0,857** |
| F1 de vigilancia | 0,714 | 0,563 | **0,837** |
| Accuracy de vigilancia | 0,600 | 0,517 | **0,759** |
| Evidencia suficiente | 0,700 | 0,724 | **0,828** |
| Exactitud del tipo documental | 0,333 | 0,310 | **0,345** |

Se selecciona el clasificador calibrado para decidir si un elemento merece vigilancia. La evaluación leave-one-out evita usar la etiqueta del propio caso como ejemplo durante su predicción. La ejecución final reclasificó 1.049 elementos y seleccionó 649 candidatos.

## Decisión de arquitectura

- `calibrated_watch` será la señal operativa para alimentar el catálogo de vigilancia.
- `calibrated_evidence_sufficient` funcionará como control de evidencia.
- La taxonomía de seis tipos se conserva como atributo auxiliar y no como verdad definitiva, debido a su exactitud de 34,5 %.
- La categoría también se conserva como auxiliar: su exactitud fue 34,5 % en esta muestra.
- No se publican los archivos completos de ejecución en el repositorio porque contienen fragmentos de documentos fuente. Se conservan métricas agregadas y código reproducible.

## Limitaciones

- La muestra contiene 29 casos: 21 positivos y 8 negativos para vigilancia.
- El número de ejemplos por tipo es desigual, especialmente para `HALLAZGO` y `COMPROMISO`.
- La especificidad observada es 50 % (4 de 8 negativos), por lo que la capacidad de rechazo todavía debe interpretarse con cautela.
- El catálogo calibrado aumenta de 330 a 649 candidatos para priorizar cobertura. La cifra representa señales documentales, no riesgos independientes.
