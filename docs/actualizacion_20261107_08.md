# Actualización del 7 y 8 de noviembre de 2026

El README contiene el estado técnico, los denominadores vigentes y las limitaciones verificadas. La cronología se respalda en `results/closure_20261108/merged_work_log.json`, con fecha local de Bogotá y UTC.

## Decisiones

- Mantener consulta original, BGE-M3 y chunking recursivo. No incorporar una rama experimental de recuperación.
- Mantener el corpus publicado. Las actas de evaluación permanecen fuera del repositorio público y no amplían la línea base.
- Detalle de señales público automático, sin carga manual de CSV; filtros y métricas por proyecto.
- Conservar los resultados negativos: casos 3 y 5 no resueltos; desacuerdo 3/4 frente a 5/5 registrado, sin forzar valores.
- Una solicitud no prueba cumplimiento. El control de sesión conserva propuestas originales, marca pendientes los componentes apoyados en un cierre no sustentado y recalcula agregados sin reducir denominadores.
- No modificar el informe hasta concluir la revisión de la solución.

## Evidencia nueva

`src/risk/session_exposure_grounding.py` implementa la revisión conservadora; `app/streamlit_app.py` la aplica a análisis de sesión, incluso los ya existentes, antes de construir vistas. El prompt de valoración explicita que una etiqueta de extracción no prueba cierre y que el cierre de otra actividad no respalda el de esta señal.

El notebook 30 verifica integridad y comportamiento con datos fabricados explícitos. El 31 comprueba entradas para reproducir el enriquecimiento existente, con llamadas API desactivadas. Los notebooks 27 y 29 conservan su contenido histórico con advertencia de alcance; sus salidas no son una nueva evaluación.

La evidencia automática se registra en `results/closure_20261108/software_validation.json`. Es ejecución local de software; los checks de GitHub Actions son evidencia adicional disponible en el PR. No se presenta una ejecución nueva del generador ni una validación experta nueva.

## Límites abiertos

La cobertura 339/515 no es total: 176 señales atribuidas permanecen sin PIRD completo. El control literal no garantiza equivalencia semántica. Los cinco casos conocidos no permiten estimar generalización independiente. No se evaluó utilidad de la app con el experto. Los casos 3 y 5 impiden declarar precisión semántica completa. Estas limitaciones deben quedar explícitas en el informe y la sustentación.
