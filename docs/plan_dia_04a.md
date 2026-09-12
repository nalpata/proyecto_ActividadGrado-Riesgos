# Plan de trabajo · Día 4A · Reranking multilingüe

## Objetivo

Seleccionar la estrategia final de recuperación comparando BGE-M3 normal y HyDE con y sin reranking multilingüe.

## Configuraciones

1. `normal`: pregunta original y BGE-M3.
2. `hyde`: documento hipotético y BGE-M3.
3. `normal_rerank`: Top-20 normal reordenado con `BAAI/bge-reranker-v2-m3`.
4. `hyde_rerank`: Top-20 HyDE reordenado con el mismo reranker.

Las cuatro configuraciones conservan el mismo corpus, 20 preguntas, Top-5 final y juez v3. El reranker fue seleccionado por su soporte multilingüe y capacidad de cross-encoder.

## Métricas

- Precision@1, Precision@3 y Precision@5.
- Hit@1, Hit@3 y Hit@5.
- MRR.
- Resultados por pregunta.
- Tiempo de inferencia y pares nuevos evaluados.

## Criterio

El reranking se seleccionará si mejora principalmente Precision@5 y MRR frente a la consulta correspondiente, sin deteriorar Hit@5. La conclusión se basará también en resultados pareados por pregunta.

## Separación del Día 4B

El chunking estructural se evaluará después con la estrategia ganadora del Día 4A. Esta separación evita atribuir al reranker una mejora causada por el cambio de chunking.
