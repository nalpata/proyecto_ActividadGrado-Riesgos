# Corrección posterior a la evaluación retenida

La primera evaluación de un proyecto adicional se conserva separada de esta corrección. Se observó una atribución a un proyecto ajeno pese a citar documentos del proyecto de sesión, y baja cobertura tras el control de cierre. Los originales y referencias expertas son privados y no se incorporan aquí.

## Diagnóstico y cambio

- El índice de sesión estaba aislado del histórico, pero la pregunta podía introducir un nombre de otro proyecto. Se aplica, antes del ranking, un filtro de presencia textual para los nombres y alias del catálogo: si un proyecto solicitado no aparece en el texto elegible, la consulta queda sin evidencia. No se usa el nombre arbitrario de la sesión como prueba de pertenencia. Una mención textual es condición necesaria, no validación semántica completa; proyectos no incluidos en el catálogo no tienen esta protección determinista.
- La etiqueta de cierre de la extracción podía diferir del razonamiento de la valoración posterior. La valoración ahora determina `assessed_exposure_status` desde la evidencia, sin recibir la etiqueta anterior como ancla. El control comprueba este estado y la justificación, manteniendo el bloqueo de cierres sin respaldo. No se cambia la rúbrica ni se impone una valoración experta.
- Las sesiones antiguas conservan la política previa: no se restauran automáticamente puntajes anulados ni se alteran auditorías históricas. Una nueva valoración se registra separadamente.
- Se explicita en generación que diferencias de porcentajes se expresan en puntos porcentuales.

## Verificación

Las regresiones sintéticas comprueban proyectos ausentes, alcance documental antes de Top-k, límites de palabra, conservación de consultas ordinarias y discrepancia entre etiqueta de extracción y estado valorado. Las pruebas de software no sustituyen la verificación en la aplicación. La comprobación posterior en los casos conocidos se reportará como regresión y no como un nuevo test independiente.
