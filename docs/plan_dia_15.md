# Día 15 · Estructura del front

## Objetivo

Crear la navegación base de la aplicación Streamlit sobre el contrato público congelado del Día 14, sin adelantar la implementación analítica de los días 16 y 17.

## Secciones acordadas

Se conservan las siete vistas analíticas acordadas y se agregan dos entradas necesarias para que la aplicación sea reutilizable:

1. Portada del sistema.
2. Proyectos y documentos.
3. Resumen ejecutivo.
4. Radar de riesgos.
5. Timeline.
6. Riesgos priorizados.
7. Perfil del proyecto.
8. Pregunte a sus documentos.
9. Metodología y métricas.

## Diseño de integración

El front carga exclusivamente `results/day_14/backend_snapshot_v1.json`. No accede a fragmentos, evidencia, preguntas, respuestas ni señales individuales. Antes de renderizar, valida la versión `1.0.0`, las conciliaciones y la política de privacidad.

Las vistas de resumen y perfil muestran agregados ya aprobados. Radar, timeline y riesgos priorizados quedan preparados para las visualizaciones del Día 16. La caja conversacional se presenta deshabilitada hasta conectarla al pipeline en el Día 17.

## Criterios de cierre

- Las siete secciones son navegables.
- Existe una portada explicativa y un módulo para seleccionar/crear proyectos.
- El usuario puede cargar PDF/DOCX en la sesión; el procesamiento se conectará en el Día 18.
- El PIRD aparece siempre acompañado de cobertura y condición PROVISIONAL.
- La aplicación arranca desde la raíz del repositorio.
- El front rechaza contratos inválidos o incompatibles.
- No se cargan archivos privados ni datasets por señal.
- La suite automatizada y la prueba de arranque de Streamlit finalizan correctamente.
