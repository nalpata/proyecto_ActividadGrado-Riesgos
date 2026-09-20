# Día 15 · Estructura del front

## Objetivo

Crear la navegación base de la aplicación Streamlit sobre el contrato público congelado del Día 14, sin adelantar la implementación analítica de los días 16 y 17.

## Secciones acordadas

1. Resumen ejecutivo.
2. Radar de riesgos.
3. Timeline.
4. Riesgos priorizados.
5. Perfil del proyecto.
6. Pregunte a sus documentos.
7. Metodología y métricas.

## Diseño de integración

El front carga exclusivamente `results/day_14/backend_snapshot_v1.json`. No accede a fragmentos, evidencia, preguntas, respuestas ni señales individuales. Antes de renderizar, valida la versión `1.0.0`, las conciliaciones y la política de privacidad.

Las vistas de resumen y perfil muestran agregados ya aprobados. Radar, timeline y riesgos priorizados quedan preparados para las visualizaciones del Día 16. La caja conversacional se presenta deshabilitada hasta conectarla al pipeline en el Día 17.

## Criterios de cierre

- Las siete secciones son navegables.
- El PIRD aparece siempre acompañado de cobertura y condición PROVISIONAL.
- La aplicación arranca desde la raíz del repositorio.
- El front rechaza contratos inválidos o incompatibles.
- No se cargan archivos privados ni datasets por señal.
- La suite automatizada y la prueba de arranque de Streamlit finalizan correctamente.
