# Resultados del Día 18A

## Resultado de asignación

La ejecución privada procesó y concilió todas las señales disponibles. El catálogo real, la cobertura de asignación, los conteos, los PIRD y los niveles por proyecto permanecen en el paquete privado del Día 18A y no se publican en este repositorio.

## Controles verificados

- Se conserva sin cambios la vista consolidada original.
- No se recalcularon severidad, probabilidad, recurrencia ni persistencia.
- Los agregados y las asignaciones por señal permanecen fuera del repositorio.
- El front solo activa los proyectos cuando recibe el catálogo y el resumen mediante secretos del servidor.
- El asistente filtra por chunks asignados explícitamente al proyecto seleccionado.
- 76 pruebas automatizadas aprobadas.
- 45 combinaciones de renderizado aprobadas: 9 vistas del consolidado y 9 vistas para cada proyecto sintético A–D.

## Demostración académica reproducible

Se incorporó `results/day_18/academic_project_demo.json`, un contrato agregado con cuatro proyectos ficticios. La aplicación permite seleccionar cada proyecto y revisar su resumen, radar, filtros, timeline, priorización y perfil. También muestra una comparación metodológica en la vista de métricas.

Los valores son completamente sintéticos y están marcados en el selector, el contenido de la vista y la política del archivo. No replican, escalan ni enmascaran los resultados reales; por ello pueden utilizarse en GitHub, capturas del informe y sustentación sin divulgar la correspondencia confidencial.

## Limitación

La asignación no tiene todavía un Gold Standard humano independiente. Por esta razón se reporta como `PROVISIONAL_PROJECT_DISCRIMINATION` y los casos no resueltos permanecen pendientes, sin imputación.
