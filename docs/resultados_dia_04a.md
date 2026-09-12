# Resultados · Día 4A · Reranking multilingüe

## Resultado automático

El experimento comparó cuatro configuraciones sobre las mismas 20 preguntas, 345 chunks y un Top-5 final. `hyde_rerank` obtuvo el mayor MRR automático (0,900), pero empató con `normal` en Precision@5 (0,740) y su ventaja frente a `normal` fue pequeña e incierta en la comparación pareada.

| Configuración | P@1 | P@3 | P@5 | Hit@3 | Hit@5 | MRR |
|---|---:|---:|---:|---:|---:|---:|
| normal | 0,750 | 0,767 | 0,740 | 0,950 | 1,000 | 0,846 |
| hyde | 0,500 | 0,550 | 0,540 | 0,850 | 1,000 | 0,702 |
| normal_rerank | 0,800 | 0,767 | 0,740 | 0,900 | 1,000 | 0,873 |
| hyde_rerank | 0,800 | 0,783 | 0,740 | 1,000 | 1,000 | 0,900 |

## Auditoría humana ciega

Se seleccionaron 12 preguntas con cambios relevantes de orden. Para cada una se evaluó un fragmento exclusivo del Top-3 de `normal` y otro exclusivo del Top-3 de `hyde_rerank`. La auditora no vio el método ni la etiqueta del juez.

| Configuración | Relevantes | Tasa de relevancia | Chunks atómicos | Tasa de atomicidad |
|---|---:|---:|---:|---:|
| normal | 11/12 | 91,7 % | 10/12 | 83,3 % |
| hyde_rerank | 7/12 | 58,3 % | 3/12 | 25,0 % |

En la comparación pareada, `normal` ganó en relevancia en 5 preguntas, `hyde_rerank` en 1 y empataron en 6. En atomicidad, `normal` ganó en 7 y no perdió ninguna.

## Decisión

La estrategia seleccionada es **BGE-M3 normal, sin HyDE ni reranking**, por cuatro razones:

1. Obtiene la mayor relevancia humana en los casos donde los métodos discrepan.
2. Recupera fragmentos considerablemente más claros y enfocados.
3. Mantiene Hit@5 de 1,000 y métricas automáticas competitivas.
4. Evita el costo y la latencia de generar HyDE y ejecutar un cross-encoder.

El reranker mejora claramente a HyDE frente a HyDE sin reranking, pero no demuestra una mejora estable frente al baseline normal.

## Hallazgo para el Día 4B

Once de los 24 fragmentos auditados no fueron considerados atómicos. La concentración fue mayor en `hyde_rerank` (9 de 12). El siguiente experimento evaluará chunking estructural utilizando únicamente la estrategia seleccionada: BGE-M3 normal.

## Limitaciones

- La auditoría es dirigida y se concentra en casos donde los métodos cambian el Top-3; no representa una muestra aleatoria del corpus.
- Solo se auditaron 24 pares de fragmentos correspondientes a 12 preguntas.
- El acuerdo del juez v3 con la auditoría fue 58,3 % en esta muestra difícil. Por ello la selección final se fundamenta en las etiquetas humanas, no en el promedio automático aislado.
- Los fragmentos documentales completos y la llave ciega no se publican en el repositorio público.
