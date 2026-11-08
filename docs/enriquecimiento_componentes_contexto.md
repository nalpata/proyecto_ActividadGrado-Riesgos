# Enriquecimiento de componentes ausentes con contexto · versión 1

## Problema y alcance

Después de incorporar tres fechas documentales verificadas, permanecen 222 señales sin todos los componentes PIRD dentro de las 515 asignadas a un único proyecto. Faltan 199 severidades, 194 probabilidades y 5 persistencias. No son 393 señales distintas: una señal puede carecer de ambos componentes de exposición.

La valoración original de exposición utilizaba la señal y su cita. Esta etapa añade el texto completo del mismo fragmento fuente (144 fragmentos para las 222 señales; máximo observado 2.198 caracteres), conciliado por documento, nombre, página, identificador y cita literal. No se agregan documentos, se cambian asignaciones ni se incorporan páginas vecinas. Los fragmentos compartidos requieren verificar que la nueva cita corresponde al proyecto de la señal.

## Método y controles

Se conserva la rúbrica histórica 1–5 y el modelo configurado en el módulo original, gpt-4o-mini. La solicitud pide únicamente componentes ausentes y admite evidencia insuficiente o no aplicabilidad. La no aplicabilidad queda registrada; no elimina señales del denominador ni crea una nueva regla de elegibilidad del PIRD.

Cada propuesta requiere un valor entero, justificación y cita literal del contexto. Una puerta determinista rechaza respuestas con identificadores incompletos, ajenos o duplicados, niveles fuera de rango, booleanos, estados inconsistentes, citas ausentes y evidencia cuya asignación documental no corresponde al proyecto. La puerta comprueba trazabilidad y alcance; la pertinencia semántica del nivel sigue siendo una valoración del modelo, sin nueva validación experta.

Los valores históricos presentes, las señales, citas originales, asignaciones, recurrencia y persistencia se conservan. Las nuevas citas y razones se guardan por componente en una auditoría separada. Solo las señales con un componente efectivamente recuperado pasan de nuevo por la fórmula PIRD existente. Las puntuaciones ya calculadas se cotejan y deben permanecer idénticas.

Los lotes de hasta 10 señales requieren 23 solicitudes para la cola completa. Se guardan respuestas estructuradas, modelo reportado y tokens en un checkpoint reanudable. El checkpoint se liga mediante hash a señales, contexto, catálogo, perfil base, modelo, rúbrica y código; no se reutiliza ante cambios. El resumen identifica el resultado como no desplegado y sin nueva validación experta. Los resultados anteriores de la muestra experta permanecen como evaluación congelada y no se reinterpretan como prueba independiente del sistema enriquecido.

## Ejecución

El cuaderno Colab entregado contiene las fuentes, el perfil del Día 22, los 649 registros y el subconjunto de fragmentos necesario, con hashes de integridad. No requiere clonar GitHub ni instalar un entorno local. Su ejecución solicita la clave mediante entrada oculta, verifica los archivos y la conciliación de la cola, procesa los lotes y descarga un ZIP de resultados para revisión. No modifica GitHub, Streamlit ni el perfil publicado.

La ejecución con respuestas simuladas valida el recorrido técnico; no constituye la reevaluación real. La reevaluación requiere ejecutar el cuaderno con acceso al servicio del modelo. Ante un error, el cuaderno permite descargar los avances conservados; el checkpoint puede cargarse en una ejecución posterior del mismo cuaderno.

## Productos de una ejecución real

- `signals_context_enriched.csv`: copia versionada de las 649 señales con nuevos componentes sustentados.
- `component_evidence_audit.csv`: propuestas aceptadas o rechazadas, cita, razón, componente y fuente.
- `exposure_context_checkpoint.jsonl`: respuestas y consumo por lote, para reanudación y auditoría.
- `project_scope_context_enriched.json`: perfiles por proyecto recalculados, pendientes de revisión e integración.
- `summary.json`: alcance ejecutado, componentes aceptados, cobertura antes/después, consumo y límites.

La siguiente revisión debe comprobar los valores efectivamente recuperados, las diferencias del perfil y los casos que conservan faltantes. No se anticipa una cobertura final ni se declara que las 222 señales resultarán puntuables.
