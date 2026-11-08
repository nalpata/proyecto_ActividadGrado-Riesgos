# Estado frente a los objetivos — 8 de noviembre de 2026

Se mantiene la solución publicada y el diseño RAG seleccionado. Este registro distingue implementación de validación; no declara todos los objetivos completamente validados.

| Objetivo | Evidencia y estado | Límite |
| --- | --- | --- |
| OE1 corpus | 50 archivos, 36 únicos; inventario y detalle público | No se incorporan adjuntos descartados; actas nuevas solo evaluación separada |
| OE2 chunking | Recursivo seleccionado y comparación histórica | No reoptimizado en esta fase |
| OE3 embeddings | Comparación histórica y BGE-M3 seleccionado | Muestras de evaluación acotadas |
| OE4 recuperación | Matriz normalizada/Parquet, alcance antes de Top-5 | Evaluación acotada al entorno documental revisado |
| OE5 RAG | Respuestas con referencias y consulta de sesión | Citas válidas no garantizan fidelidad semántica |
| OE6 HyDE/reranking | Experimentos históricos conservados | No activos en solución seleccionada |
| OE7 extracción | Extracción, puerta de evidencia y resolución de proyecto | Validación experta muestral, no corpus completo |
| OE8 validación | Revisión humana de 40 casos, denominadores en README | No test de proyecto independiente |
| OE9 patrones | Clustering exploratorio y recurrencia documental | No validación general de relaciones semánticas |
| OE10 perfil | 339/515 completas; siete casos revisados; política de faltantes y control de cierre | 176 pendientes; valoración 3/4 del caso 3 aceptada; provisionalidad depende de cobertura |
| OE11 visualización | Radar, detalle, inventario, timeline y filtros por proyecto | Las pruebas de software no prueban utilidad profesional |
| OE12 LangGraph | Grafo histórico de cuatro nodos | Rutas de sesión/QA diferenciadas; no sistema multiagente completo |
| OE13 conversación | Documentos de sesión, trazabilidad y aislamiento | Caso 5 cerrado: NSGA correcto según confirmación de Patricia; alcance muestral |
| OE14 evaluación | Experimentos, revisión humana, regresión y suite automática | Sin evaluación experta de utilidad de app ni generalización independiente |

La etiqueta provisional no se retira para aparentar un cierre: expresa cobertura incompleta. Un componente no evaluable permanece ausente y conserva su señal en el denominador. La revisión del cierre no sustituye propuestas por las etiquetas expertas.

Consultar el README, `docs/actualizacion_20261107_08.md` y `results/closure_20261108/` para resultados, cronología y ejecución reproducible. El informe aún no se modifica.

## Aclaración de cierre — 8 de noviembre de 2026

Patricia confirma tras revisión con el experto que la valoración 3/4 del caso 3 es aceptada y no requiere más trabajo; en el caso 5, NSGA es la respuesta correcta del sistema. Los demás casos revisados fueron aceptados según su confirmación. Estas aclaraciones sustituyen la descripción anterior de discrepancia y abstención pendiente; no constituyen una nueva ejecución ni permiten inferir validación general.

Las ocho marcas del control automático de cierre son observaciones técnicas, no ocho errores confirmados por el experto ni una revisión obligatoria pendiente para avanzar al informe. Se conservan los resultados históricos del control sin modificar valoraciones ni agregados. Patricia refiere seis casos revisados, mientras el registro disponible enumera cinco; no se añade un caso sin evidencia ni se recalculan métricas.

Siguiente etapa acordada: actualizar el informe con los resultados aceptados, las cifras vigentes y las limitaciones metodológicas conservadas.
