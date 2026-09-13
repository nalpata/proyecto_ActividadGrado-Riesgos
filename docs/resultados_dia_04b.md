# Resultados · Día 4B · Chunking estructural

## Resultado de la construcción

La ejecución en Colab procesó los 36 documentos sin errores y generó 560 chunks estructurales. La estrategia redujo el promedio de 263,6 a 150,2 palabras, la mediana de 303 a 164 y el máximo de 378 a 210. Ningún chunk estructural superó 210 palabras.

## Métricas automáticas

| Configuración | P@1 | P@3 | P@5 | Hit@3 | Hit@5 | MRR |
|---|---:|---:|---:|---:|---:|---:|
| normal_current | 0,750 | 0,767 | 0,740 | 0,950 | 1,000 | 0,846 |
| normal_structural | 0,500 | 0,600 | 0,630 | 1,000 | 1,000 | 0,717 |

El chunking estructural conservó Hit@5 y elevó Hit@3, pero redujo la precisión en todas las posiciones y disminuyó el MRR. Encontró fragmentos relevantes, aunque los colocó junto con más resultados irrelevantes y en peores posiciones.

## Auditoría humana ciega

Se evaluaron los resultados Top-1 de 12 preguntas seleccionadas por sus diferencias entre métodos. La auditora no vio el método ni la etiqueta automática.

| Configuración | Relevantes | Tasa de relevancia | Chunks atómicos | Tasa de atomicidad |
|---|---:|---:|---:|---:|
| normal_current | 10/12 | 83,3 % | 7/12 | 58,3 % |
| normal_structural | 10/12 | 83,3 % | 5/12 | 41,7 % |

En la comparación pareada de relevancia, cada método ganó una pregunta y empataron en diez. En atomicidad, el chunking actual ganó cuatro preguntas, el estructural dos y empataron seis.

## Decisión

Se conserva el **chunking recursivo actual**. La reducción de longitud de la variante estructural no produjo una mejora de relevancia y tampoco aumentó la atomicidad percibida. Además, deterioró Precision@1, Precision@3, Precision@5 y MRR.

La estrategia final de recuperación después de los Días 3, 4A y 4B es:

- Consulta original.
- Embeddings BGE-M3.
- Chunking recursivo actual.
- Sin HyDE.
- Sin reranking.

## Limitaciones

- La auditoría humana fue dirigida a 12 preguntas con diferencias entre métodos y no es una muestra aleatoria.
- Se evaluó un Top-1 por método y pregunta, para un total de 24 fragmentos.
- El acuerdo del juez v3 con la auditoría fue 54,2 % en esta muestra difícil. La decisión final combina métricas automáticas con las etiquetas humanas.
- Los fragmentos completos, las respuestas individuales y la llave ciega no se publican en el repositorio público.
