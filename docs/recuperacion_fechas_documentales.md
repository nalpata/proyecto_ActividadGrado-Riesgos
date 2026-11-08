# Recuperación de fechas documentales · Día 22

El cálculo temporal anterior infería fechas de los nombres de archivo. Tres PDFs del corpus aprobado contienen una fecha documental explícita que no figuraba en el nombre. Se incorporan como evidencia adicional dentro del mismo corpus, sin agregar documentos ni cambiar las señales o sus valoraciones de exposición.

## Controles y alcance

`config/document_dates_verified.json` registra nombre, fecha ISO, precisión diaria, página, cita literal y SHA-256 de cada PDF. Antes de recalcular se verifica el hash, la presencia de la cita en la página y la correspondencia entre la fecha textual y la fecha declarada. Se rechazan duplicados, rutas externas, páginas inválidas, citas ausentes y sustituciones de fechas ya inferidas que requieran conciliación. Las tres citas fueron revisadas como fecha de emisión o reunión del documento, no como una fecha incidental de un suceso.

El manifiesto aporta fechas a la persistencia calculada exclusivamente dentro del proyecto. Se mantienen el umbral 0,70, los embeddings BGE-M3, las asignaciones, la recurrencia, las rúbricas, los pesos, la clasificación y todos los valores y faltantes de severidad y probabilidad. No se hacen llamadas a modelos. Las fechas de fuentes compartidas no asignan sus señales a un proyecto.

El perfil actualizado se conserva en `results/day_22/project_scope_dates_verified.json`; el perfil anterior del Día 21 y el consolidado histórico permanecen disponibles. La aplicación selecciona la nueva versión solo para el modo Corpus por proyecto. La cronología documental utiliza las mismas fechas verificadas para el corpus; las sesiones no las heredan aunque un archivo tenga el mismo nombre. El consolidado histórico conserva sus agregados temporales originales y su PIRD 52,16.

## Comparación sobre el mismo universo

| Proyecto | Total | Puntuadas antes | Puntuadas después | Cobertura después | PIRD después |
| --- | ---: | ---: | ---: | ---: | ---: |
| DataR | 404 | 234 | 236 | 58,42 % | 49,77 |
| Multinube | 104 | 52 | 54 | 51,92 % | 39,87 |
| NSGA | 6 | 2 | 2 | 33,33 % | 38,20 |
| NSGT | 1 | 1 | 1 | 100,00 % | 37,82 |
| PDIS | 0 | 0 | 0 | Sin señales | Pendiente |

La cobertura conjunta pasa de 289/515 (56,12 %) a 293/515 (56,89 %). Las pendientes de componentes bajan de 226 a 222. Las 134 señales sin asignación única permanecen fuera de estos perfiles.

Se recuperan cuatro puntuaciones: ITEM_00006 (48,17), ITEM_00013 (38,28), ITEM_00077 (47,87) e ITEM_01040 (28,40). Dos puntuaciones previas cambian por persistencia: ITEM_00001 pasa de 53,11 a 60,52 e ITEM_00021 de 43,23 a 50,63. No se pierde ninguna puntuación previa. Los PIRD globales por proyecto mantienen su valor a dos decimales, aunque cambian agregados de categoría y conteos. No debe confundirse estabilidad del índice agregado con ausencia de cambios individuales.

En total cambian 15 fechas de señales y 18 niveles de persistencia. La cronología mantiene 36 documentos, pasa de 30 a 33 con fecha y conserva 3 sin fecha. No se representa esta cronología como una evolución mensual del PIRD.

## Pendientes y límites

Quedan 166 señales sin severidad ni probabilidad, 28 sin severidad, 23 sin probabilidad y 5 sin los tres componentes de severidad, probabilidad y persistencia. Por componente: 199 severidades, 194 probabilidades y 5 persistencias pendientes. La siguiente etapa requiere aportar contexto documental adicional a las valoraciones que carecen de sustento; no corresponde rellenarlas para alcanzar un porcentaje objetivo. La revisión experta muestral previa no se convierte en una validación nueva de estos puntajes recalculados.

## Reproducción

Ejecutar el recálculo histórico con las seis fuentes originales y los parámetros adicionales `--document-dates-json config/document_dates_verified.json --corpus-root data/raw/corpus_actualizado`, especificando rutas de salida separadas. Los tres PDFs deben conservar exactamente sus hashes. Sin estos parámetros se reproduce el comportamiento anterior.
