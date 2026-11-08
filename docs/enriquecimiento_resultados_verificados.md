# Enriquecimiento de exposición: ejecución y revisión documental

## Por qué se revisó el resultado

La etapa del Día22 dejó 293 señales puntuadas y222 pendientes de componentes dentro de515 señales con asignación única. La autora ejecutó en Colab la misma rúbrica de exposición con el fragmento fuente completo para222 casos. El ZIP recibido conserva respuestas, auditoría y resultados. Antes de publicar se reprodujeron exactamente las649 filas,444 decisiones de componente y los agregados a partir del checkpoint, sin nuevas solicitudes al modelo.

La ejecución registró23 lotes: tres de la versión original y20 después de reanudar. El modelo reportado fue gpt-4o-mini-2024-07-18. El checkpoint contabiliza164.118 tokens de entrada y21.265 de salida. Ese registro no demuestra el consumo total de la cuenta: no incluye necesariamente solicitudes fallidas anteriores a guardar un lote.

## Conciliación por identificador

Dos lotes contenían nueve respuestas para diez señales. El primer manejador descartó las propuestas de ambos lotes completos. Se recuperaron las respuestas inequívocas utilizando exclusivamente el item_id esperado y único; una omisión no se completa por posición y una respuesta duplicada o ajena no se aplica. Las dos señales omitidas permanecen pendientes. La nueva conciliación recuperó25 componentes que también superaron los controles de cita y pertenencia al proyecto. Todas las respuestas originales se conservan.

## Revisión documental conservadora

La literalidad de una cita no demuestra por sí sola que sustente el nivel numérico. Se inspeccionaron las150 propuestas que superaron las puertas de identidad, literalidad y alcance. Se separaron73 componentes por problemas documentales: encabezados sin impacto, obligaciones o acciones futuras sin condición adversa específica, impacto añadido por la justificación, discrepancia entre nivel y motivo, cifras sin una referencia que acredite perjuicio, exposición declarada cerrada que se convierte en recurrencia hipotética y una negación del incumplimiento interpretada como impacto crítico.

Las decisiones son una revisión de calidad asistida realizada durante el cierre, no nuevas etiquetas del experto ni una medida de exactitud. Son conservadoras: la cuarentena no afirma que un impacto sea imposible; indica que la propuesta presentada no basta para incorporarlo. Los componentes se restauran al faltante original, sin asignarles otro nivel. No se modifican las valoraciones históricas presentes, la clasificación, las asignaciones, las fechas, la recurrencia, los pesos ni los293 puntajes anteriores.

La revisión, con item_id, componente, valor propuesto, cita y razón, se conserva en el paquete de resultados verificados. `src/risk/review_enriched_exposure.py` reproduce la aplicación de esas decisiones y rechaza cuarentenas duplicadas, cambios de valores históricos o decisiones que no correspondan a la propuesta registrada. Las fuentes y la lista de decisiones se ligan al agregado mediante SHA-256.

## Tres resultados distintos

| Etapa | Componentes nuevos retenidos | Señales puntuadas de515 |
| --- | ---: | ---: |
| Versión publicada del Día22 | 0 | 293 |
| ZIP original del modelo | 125 | 350 |
| Respuestas conciliadas por ID, antes de revisión documental | 150 | 365 |
| Versión propuesta después de cuarentena documental | 77 | 332 |

El resultado propuesto incorpora50 severidades y27 probabilidades, permitiendo39 nuevas puntuaciones:24 de DataR y15 de Multinube. La cobertura conjunta pasa de56,89% a64,47%. Quedan183 señales pendientes de componentes; las134 sin asignación única siguen separadas y no se incorporan a estos perfiles.

| Proyecto | Total | Puntuadas antes | Puntuadas propuestas | Cobertura propuesta | PIRD antes | PIRD propuesto |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| DataR | 404 | 236 | 260 | 64,36% | 49,77 MEDIO | 51,42 ALTO |
| Multinube | 104 | 54 | 69 | 66,35% | 39,87 MEDIO | 40,41 MEDIO |
| NSGA | 6 | 2 | 2 | 33,33% | 38,20 MEDIO | 38,20 MEDIO |
| NSGT | 1 | 1 | 1 | 100,00% | 37,82 MEDIO | 37,82 MEDIO |
| PDIS | 0 | 0 | 0 | Sin señales | Pendiente | Pendiente |

El cambio de nivel de DataR responde a nuevas observaciones puntuables en un índice relativo. No acredita una mejora de exactitud ni representa una probabilidad de incumplimiento. Una ampliación de cobertura cambia la composición de la agregación; no equivale por sí sola a que el riesgo real haya aumentado en el tiempo. El consolidado histórico52,16 y los perfiles de los Días21–22 se conservan.

Las183 pendientes se distribuyen en128 sin severidad/probabilidad,34 sin probabilidad,16 sin severidad y5 sin severidad/probabilidad/persistencia. No se completan para alcanzar una cobertura objetivo. La revisión experta previa permanece congelada sobre su muestra original: las nuevas valoraciones no se presentan como revisadas por el experto ni como prueba externa.

## Publicación y verificación

La propuesta de interfaz consume `results/day_23/project_scope_context_reviewed.json` en el modo Corpus por proyecto y avisa que las nuevas valoraciones no tuvieron revisión experta. Las sesiones, el modo sintético, el RAG, las fechas documentales y el consolidado histórico conservan su alcance. La publicación requiere integrar el PR y verificar la aplicación en vivo; los archivos de esta etapa no certifican que ya se haya desplegado.
