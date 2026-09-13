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

Después de la ejecución se revisarán distribución de clases, evidencia rechazada, errores, duplicados y consistencia. Se construirá una muestra humana estratificada por tipo para validar clasificación, vigilancia y suficiencia de evidencia.
