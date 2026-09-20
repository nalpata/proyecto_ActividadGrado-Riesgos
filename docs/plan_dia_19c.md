# Día 19C · Actualización dinámica de vistas

## Objetivo

Usar los agregados producidos por el Día 19B como fuente de las vistas del proyecto recién procesado, sin mezclarlos con el snapshot consolidado ni renderizar evidencia privada.

## Vistas actualizadas

1. Resumen ejecutivo y cobertura PIRD.
2. Radar por categoría y filtros.
3. Timeline agregado de recurrencia y persistencia.
4. Riesgos priorizados por categoría.
5. Distribución del perfil del proyecto.

## Reglas

- El resultado se conserva únicamente en la sesión activa.
- Un proyecto nuevo procesado pasa a estado procesado sin alterar el corpus histórico.
- Las vistas reciben solamente agregados; nunca textos, citas, nombres de documentos o señales individuales.
- Un PIRD incompleto se muestra como pendiente.
- El asistente conversacional se mantiene desactivado para documentos recién cargados hasta contar con recuperación aislada sobre sus embeddings. Esto evita consultar accidentalmente el corpus consolidado.
- Al finalizar la sesión, la aplicación vuelve al snapshot publicado y congelado.

## Criterios de cierre

- Las cinco vistas utilizan el contrato `SESSION-19C` cuando existe un análisis 19B.
- El radar y la priorización soportan proyectos sin categorías calculadas.
- El timeline soporta ausencia de fechas o persistencia.
- La prueba de privacidad confirma que la vista no contiene evidencia ni señales individuales.
- La suite completa y los renders Streamlit terminan sin excepciones.
