# Día 18A · Discriminación de riesgos por proyecto

## Objetivo

Separar las señales documentales y los perfiles de riesgo por proyecto cuando una misma acta o documento contiene información de varias iniciativas, sin alterar las 649 clasificaciones ni los PIRD históricos.

## Catálogo privado

El catálogo es explícito y versionado fuera del repositorio público. No se aceptan nombres inferidos únicamente por aparecer después de la palabra “proyecto”; esta regla evita falsos positivos producidos por encabezados tabulares.

## Política de asignación

1. Coincidencia explícita en título, señal o evidencia.
2. Coincidencia más próxima a la cita dentro del chunk.
3. Coincidencia única en el chunk.
4. Coincidencia en un nombre de archivo dedicado.
5. Si hay más de un proyecto o no existe evidencia suficiente, conservar `MULTIPROYECTO` o `PENDIENTE_PROYECTO`.

Las asignaciones individuales son privadas. El repositorio y el front reciben únicamente agregados conciliados.

## Integración funcional

- Mantener una vista consolidada de la interventoría.
- Incorporar los proyectos confirmados en el selector del despliegue privado.
- Cambiar resumen, radar, priorización, timeline y perfil según el proyecto seleccionado.
- Restringir el retrieval del asistente a chunks asociados explícitamente con el proyecto.
- Mantener cobertura y condición `PROVISIONAL` visibles.

## Criterios de cierre

- Las 649 señales concilian entre asignadas, ambiguas y pendientes.
- Ningún caso ambiguo se fuerza a un proyecto.
- Los perfiles por proyecto usan la fórmula PIRD aprobada.
- La aplicación no expone textos, evidencia ni asignaciones individuales.
- GitHub no contiene nombres, valores ni perfiles reales por proyecto.
- La suite automatizada y todas las vistas Streamlit finalizan sin excepciones.
