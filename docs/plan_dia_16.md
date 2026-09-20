# Día 16 · Radar y visualizaciones ejecutivas

## Objetivo

Convertir los agregados públicos congelados en visualizaciones ejecutivas interactivas, sin modificar el backend, recalcular el PIRD ni exponer señales o evidencia individual.

## Alcance

- Radar polar PIRD con escala fija 0–100.
- Filtros por categoría, nivel y cobertura mínima.
- Priorización agregada por categoría.
- Vista temporal de recurrencia, persistencia y disponibilidad de fechas.
- Estados vacíos para combinaciones de filtros sin resultados.
- Asociación de todas las vistas con el proyecto seleccionado.

## Decisiones de integridad

El snapshot público no contiene series calendario ni señales individuales. Por ello, la vista Timeline utiliza únicamente roles temporales y niveles de persistencia agregados. No se fabrican puntos por fecha y la priorización pública se mantiene en el nivel de categoría.

## Criterios de cierre

- El radar cierra correctamente el polígono y conserva una escala comparable 0–100.
- Los filtros afectan radar, indicadores y tabla sin alterar los datos fuente.
- Las visualizaciones temporales concilian con 649 señales.
- El front no accede a evidencia, textos, nombres de documento ni señales individuales.
- La suite completa y el render de las nueve secciones finalizan sin errores.
