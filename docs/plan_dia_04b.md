# Plan de trabajo · Día 4B · Chunking estructural

## Pregunta experimental

¿Dividir los documentos por estructura, párrafos y oraciones mejora la relevancia y la claridad de los fragmentos frente al chunking recursivo actual?

## Control experimental

Se mantiene fija la configuración seleccionada en el Día 4A: consulta original y BGE-M3, sin HyDE ni reranking. Solo cambia el chunking.

## Variantes

- `normal_current`: 345 chunks recursivos, límite de 2.200 caracteres y solapamiento de 300 caracteres.
- `normal_structural`: cortes por página, título, párrafo, lista y oración, con objetivo de 160 palabras y máximo de 210.

## Métricas

- Precision@1, Precision@3 y Precision@5.
- Hit@1, Hit@3 y Hit@5.
- MRR.
- Longitud media, mediana y máxima de los chunks.
- Relevancia humana y atomicidad en una muestra ciega dirigida.

## Decisión

El chunking estructural se adoptará únicamente si conserva o mejora la relevancia y reduce de forma material los fragmentos largos o con múltiples asuntos.
