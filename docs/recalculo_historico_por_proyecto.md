# Recálculo histórico por proyecto · versión 1

## Evidencia recuperada

Se recuperaron resultados_perfil_inteligente_dia_11.zip, resultados_clasificador_calibrado_dia_05.zip y resultados_clustering_semantico_dia_09.zip, conservados por la autora. Contienen 649 señales clasificadas, 649 valoraciones de exposición y una matriz de 649 × 1024 embeddings BGE-M3. Los identificadores son únicos, el orden de las señales y del índice vectorial coincide y todos los fragmentos fuente existen en el corpus publicado. Los 26 campos originales de clasificación coinciden entre el Día 5 y el Día 11.

Antes del recálculo se reprodujo el agregado histórico: PIRD 52,16, nivel ALTO, 372 señales puntuadas de 649, cobertura 57,32 %. El histórico conserva su significado como agregado del corpus completo y no se sobrescribe.

## Método

1. Verificar integridad de identificadores, concordancia de campos originales, documentos fuente, dimensiones y valores finitos de embeddings.
2. Asignar cada señal mediante su cita literal y contexto original con el catálogo confirmado. Los títulos y justificaciones generados no determinan su pertenencia.
3. Separar señales pendientes y ambiguas antes de construir vecindades. Mantenerlas en la conciliación con estado PENDIENTE_ASIGNACION_PROYECTO.
4. Reutilizar los embeddings históricos, alineados mediante el índice item_id. Calcular recurrencia y persistencia únicamente entre señales del mismo proyecto, con el umbral coseno aprobado de 0,70 y las reglas temporales existentes.
5. Conservar las valoraciones históricas de severidad y probabilidad, sus faltantes y su justificación. No se hacen nuevas llamadas LLM ni se imputan componentes.
6. Recalcular el PIRD individual y los perfiles con los pesos y fórmulas existentes. Publicar agregados y guardar aparte los registros completos de trazabilidad.

El resultado incluye hashes SHA-256 de las seis fuentes, versión del método y declaración de los componentes reutilizados y recalculados. Si cambia el catálogo activo, el front descarta el perfil anterior para evitar mezclar reglas de asignación distintas.

## Conciliación y resultados

De las 649 señales se asignaron 515 a un único proyecto y quedaron 134 pendientes o ambiguas: 95 sin evidencia de pertenencia suficiente y 39 con contexto o cita multiproyecto. Entre las señales asignadas cambiaron 116 niveles de recurrencia y 65 de persistencia al restringir sus vecindades. Estas diferencias son consecuencias del cambio de alcance del cálculo; no son una medida de exactitud o mejora predictiva.

| Proyecto | Señales asignadas | Puntuadas | Pendientes de componentes | Cobertura | PIRD provisional |
| --- | ---: | ---: | ---: | ---: | ---: |
| DataR | 404 | 234 | 170 | 57,92 % | 49,77 |
| Multinube | 104 | 52 | 52 | 50,00 % | 39,87 |
| NSGA | 6 | 2 | 4 | 33,33 % | 38,20 |
| NSGT | 1 | 1 | 0 | 100,00 % | 37,82 |
| PDIS | 0 | 0 | 0 | 0,00 % | Pendiente |

Los 289 casos puntuados se refieren solo a las 515 señales asignadas; no se comparan como si fueran el mismo universo de las 372 puntuadas en el consolidado histórico. Las 226 pendientes de componentes dentro de proyectos y las 134 pendientes de asignación son dimensiones distintas y no deben confundirse.

Un fragmento multiproyecto puede contener una cita que permita asignar una señal a NSGT. Esa asignación no habilita recuperar el fragmento completo en su chat. Por ello puede existir un perfil de una señal junto con cero fragmentos exclusivos para consultas. No se fuerza el contexto mixto a un proyecto.

## Límites de interpretación

Las asignaciones son automáticas y requieren revisión humana. NSGA y especialmente NSGT tienen muestras muy pequeñas; una cobertura del 100 % sobre una señal no acredita representatividad. Severidad y probabilidad siguen siendo valoraciones de rúbrica asistidas por IA, sin gold standard humano 1–5. Todos los perfiles se mantienen provisionales. Los lotes se conservan como subdivisiones de Multinube y no duplican señales.

Este recálculo no modifica la clasificación, los documentos, el chunking, los embeddings, las rúbricas, los pesos ni los resultados de los experimentos RAG anteriores. Tampoco sustituye la validación del experto.

## Verificación

La suite prueba la exclusión de vecinos de otros proyectos, la preservación de exposición y fuentes históricas, el rechazo de índices incompletos o incompatibles, los pendientes multiproyecto y la invalidación de perfiles si cambia el catálogo. La prueba de interfaz cubre el proyecto sin señales para evitar que herede el PIRD global o falle al dibujar una distribución vacía.

Para reproducir, ejecutar `python -m src.risk.recompute_historical_projects --help` y proporcionar los archivos originales de los tres paquetes, el corpus y el catálogo versionados, junto con rutas de salida separadas. El módulo no acepta sobrescribir sus archivos fuente.
