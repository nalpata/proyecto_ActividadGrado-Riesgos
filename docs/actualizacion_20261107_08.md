# Actualización del 7 y 8 de noviembre de 2026

El README contiene el estado técnico, los denominadores vigentes y las limitaciones verificadas. La cronología se respalda en `results/closure_20261108/merged_work_log.json`, con fecha local de Bogotá y UTC.

## Decisiones

- Mantener consulta original, BGE-M3 y chunking recursivo. No incorporar una rama experimental de recuperación.
- Mantener el corpus publicado. Las actas de evaluación permanecen fuera del repositorio público y no amplían la línea base.
- Detalle de señales público automático, sin carga manual de CSV; filtros y métricas por proyecto.
- Conservar las observaciones iniciales como historia y registrar la aclaración posterior de Patricia: valoración 3/4 aceptada en el caso 3; NSGA correcto y caso 5 cerrado. No forzar valores ni repetir la evaluación.
- Una solicitud no prueba cumplimiento. El control de sesión conserva propuestas originales, marca pendientes los componentes apoyados en un cierre no sustentado y recalcula agregados sin reducir denominadores.
- Con las aclaraciones de cierre recibidas, avanzar a la actualización del informe con resultados aceptados y límites metodológicos.

## Evidencia nueva

`src/risk/session_exposure_grounding.py` implementa la revisión conservadora; `app/streamlit_app.py` la aplica a análisis de sesión, incluso los ya existentes, antes de construir vistas. El prompt de valoración explicita que una etiqueta de extracción no prueba cierre y que el cierre de otra actividad no respalda el de esta señal.

El notebook 30 verifica integridad y comportamiento con datos fabricados explícitos. El 31 comprueba entradas para reproducir el enriquecimiento existente, con llamadas API desactivadas. Los notebooks 27 y 29 conservan su contenido histórico con advertencia de alcance; sus salidas no son una nueva evaluación.

La evidencia automática se registra en `results/closure_20261108/software_validation.json`. Es ejecución local de software; los checks de GitHub Actions son evidencia adicional disponible en el PR. No se presenta una ejecución nueva del generador ni una validación experta nueva.

## Límites abiertos

La cobertura 339/515 no es total: 176 señales atribuidas permanecen sin PIRD completo. El control literal no garantiza equivalencia semántica. Los casos conocidos no permiten estimar generalización independiente. No se evaluó utilidad de la app con el experto. La aceptación de los casos revisados no demuestra precisión semántica completa sobre el corpus. Estas limitaciones deben quedar explícitas en el informe y la sustentación.

## Comprobación del despliegue

Con PR43 publicado, Streamlit aplicó el control a la sesión existente sin repetir el LLM: 39 aceptadas, 19 valoradas y 20 pendientes (48,72 %). Ocho propuestas fueron marcadas automáticamente; no equivalen a ocho errores confirmados por el experto ni a una revisión obligatoria pendiente. No se eliminan señales. La alerta principal conserva 3/4 y la solicitud queda pendiente. Se detectó y corrigió un aviso visual causado por campos booleanos ausentes convertidos a NaN; la prueba de interfaz comprueba aviso solo en la señal marcada.

## Aclaración posterior comunicada por Patricia

El 8 de noviembre, Patricia confirmó la aceptación experta de severidad 3 y probabilidad 4 en el caso 3 y la respuesta correcta NSGA en el caso 5; los demás casos revisados fueron aceptados. Se rectifica su presentación anterior como pendientes. No se ejecutó nuevamente el modelo ni se modificaron los resultados históricos del control automático. Patricia menciona seis casos revisados; el registro anterior enumera cinco, por lo que no se incorpora un sexto sin detalle ni se recalculan métricas.
