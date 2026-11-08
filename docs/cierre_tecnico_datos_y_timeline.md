# Conservación de exposición y cronología documental

## Problema y comportamiento corregido

El recálculo por proyecto separa las señales sin pertenencia resuelta. Esa separación descartaba de sus filas de salida los siete campos de valoración de exposición, aunque existieran en el histórico. El cálculo de los perfiles asignados no dependía de esas filas, pero la omisión perjudicaba su trazabilidad y cualquier comparación posterior.

Ahora las filas pendientes conservan severidad, probabilidad, indicadores de sustento, base de evidencia, justificación y confianza de valoración. Siguen con PIRD vacío y estado PENDIENTE_ASIGNACION_PROYECTO. La conservación de exposición no fuerza pertenencia ni autoriza calcular recurrencia o persistencia entre proyectos.

Se verificó con los artefactos históricos: los 649 registros conservan sus valores originales de severidad y probabilidad, incluidos sus faltantes, y el snapshot público por proyecto permanece idéntico. No se realizaron nuevas llamadas LLM.

## Cronología de documentos

La vista Timeline presentaba distribución de roles temporales y niveles de persistencia. Se complementa con documentos por mes y un inventario ordenado de fechas, fuentes, precisión y advertencias. Estos datos se calculan desde el índice documental publicado o desde los documentos de la sesión activa; no se añade un dataset privado al repositorio.

Cada archivo se cuenta una sola vez aunque tenga varios fragmentos. Las fechas se identifican en el nombre mediante las reglas existentes. Las ausentes o fuera del rango permitido permanecen sin asignar. Cuando solo se conoce el mes, se muestra AAAA-MM, sin presentar un día inventado. No se completan meses vacíos ni se interpreta ausencia de documentos como ausencia de riesgo.

Al seleccionar un proyecto, la cronología incluye los documentos que lo mencionan explícitamente en contenido o nombre de archivo, incluso si son compartidos. Esta definición se muestra en la interfaz. El criterio no sustituye la asignación de señales ni el filtro más conservador del chat: que un documento mencione el proyecto no permite recuperar automáticamente sus fragmentos mixtos ni atribuirle todas sus señales.

La serie mide volumen documental; no simula una trayectoria del PIRD ni una probabilidad de riesgo. El modo sintético conserva sus agregados sin inventar fechas. Las cargas de sesión utilizan solo su propio índice.

## Verificación

Las pruebas cubren conservación de exposición en pendientes, exclusión de estos de los perfiles, conteo por documento sin duplicar páginas, fechas inválidas, precisión mensual, documentos compartidos y alcance vacío sin retorno al consolidado. La comprobación de interfaz cubre Timeline consolidado y los cinco proyectos, sin excepciones.

Este bloque no modifica pesos, prompts, clasificación, embeddings, corpus ni resultados históricos publicados. Las valoraciones individuales del experto y sus aclaraciones se conservan en el paquete de evaluación separado, sin incluirlas en este cambio de código.
