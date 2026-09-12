# Plan de trabajo · Día 3 · HyDE

## Pregunta experimental

¿La transformación de cada pregunta en un documento hipotético mejora la
recuperación BGE-M3 frente a usar directamente la pregunta original?

## Comparación controlada

| Elemento | Retrieval normal | HyDE |
|---|---|---|
| Corpus | 345 chunks recursivos | Los mismos 345 chunks |
| Embeddings del corpus | BGE-M3 | Los mismos embeddings BGE-M3 |
| Consulta | Pregunta original | Documento hipotético generado desde la pregunta |
| Top-k | 5 | 5 |
| Juez de relevancia | Mismo protocolo ciego | Mismo protocolo ciego |

## Secuencia

1. Generar un documento hipotético por cada una de las 20 preguntas gold.
2. Codificar pregunta original y documento HyDE con `BAAI/bge-m3`.
3. Recuperar los cinco chunks más similares con cada método.
4. Crear el pool único de pares pregunta-chunk.
5. Juzgar relevancia sin informar qué método recuperó el chunk.
6. Calcular Precision@1/3/5, Hit@1/3/5 y MRR.
7. Registrar tiempos, tokens y costo estimado.
8. Producir una muestra ciega para auditar el juez automático.

## Criterio de selección

HyDE se recomendará solo si mejora principalmente MRR y Hit@3 sin deteriorar
materialmente Precision@5. La conclusión se basará en las 20 preguntas y se
reportarán resultados por pregunta, no únicamente el promedio.

## Precaución metodológica

La evaluación de relevancia inicial usa un LLM como juez y genera una muestra
para auditoría humana. No debe presentarse como un gold standard humano nuevo.
