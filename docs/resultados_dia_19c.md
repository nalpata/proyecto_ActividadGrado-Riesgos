# Resultados del Día 19C

## Resultado funcional

Las vistas analíticas cambian automáticamente al contrato agregado del proyecto recién procesado. El usuario puede navegar desde `Proyectos y documentos` hacia el resumen, radar, timeline, priorización y perfil sin perder el resultado calculado en la sesión.

## Privacidad

- El adaptador del front descarta el bloque privado antes de construir las vistas.
- Solo conserva métricas, categorías, distribución por nivel y conteos temporales.
- No incorpora el proyecto nuevo al snapshot público ni al repositorio.
- El asistente permanece bloqueado para el proyecto nuevo hasta implementar un retriever exclusivo de sesión.

## Validación controlada del Día 19B

El 20 de septiembre de 2026 se ejecutó el flujo publicado con un PDF totalmente sintético, sin información personal ni de clientes:

- 1 documento, 1 página y 1 chunk.
- embedding BGE-M3 de 1.024 dimensiones.
- 2 señales extraídas, 2 validadas y 2 puntuadas.
- cobertura PIRD de 100 %.
- PIRD global 44,51, nivel MEDIO y estado CALCULADO.
- clasificación correctamente rotulada como provisional por ausencia de los 29 ejemplos humanos privados.

## Verificación

- Pruebas unitarias para contrato agregado, distribución PIRD y estado pendiente.
- Control explícito de ausencia de evidencia privada en la salida del front.
- Validación del bloqueo conversacional para impedir recuperación desde el corpus equivocado.
- 93 pruebas automatizadas aprobadas.
- 18 vistas base y 6 vistas dinámicas renderizadas sin excepciones.
