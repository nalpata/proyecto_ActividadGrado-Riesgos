# Cierre de identidad por proyecto

## Orden de trabajo

1. Conservar identidad documental de proyecto en ingesta, señales, recuperación y perfil.
2. Configurar y verificar el catálogo de proyectos del corpus aprobado; conciliar asignaciones y pendientes.
3. Recalcular analítica por proyecto a partir de artefactos individuales privados, sin mezclar vecindades de proyectos distintos ni sobrescribir el snapshot histórico.
4. Comprobar el flujo integrado y las vistas del despliegue, incluidos estados sin evidencia y cambios de proyecto.
5. Ejecutar evaluación humana y revisar errores de tipo, categoría, severidad y probabilidad con criterios definidos.
6. Cerrar versión y evidencias; después actualizar informe y presentación.

## Primer bloque implementado

El project_id de la sesión identifica el contenedor elegido. detected_project_id identifica la pertenencia documental. Son conceptos diferentes y no se intercambian.

Con un catálogo configurado, los fragmentos se asignan mediante menciones explícitas o nombre de archivo inequívoco. El chat excluye fragmentos ambiguos o de otros proyectos antes de seleccionar el Top-k. Una señal puede resolverse con su cita y contexto cercano aun cuando el fragmento completo sea multiproyecto; esa señal no autoriza por sí sola recuperar todo el fragmento mixto en el chat.

La asignación de señales usa citas verificadas y contexto original, no títulos o justificaciones producidos por el LLM. Las señales se restringen al proyecto antes de calcular recurrencia, persistencia, exposición y PIRD.

Sin catálogo, se mantiene compatibilidad operativa y se declara USER_DECLARED_UNVERIFIED: la selección del usuario no acredita identidad documental. El front muestra esta limitación.

## Catálogo del corpus confirmado por la autora

El catálogo versionado en config/project_catalog.json contiene DataR, Multinube, NSGA, NSGT y PDIS. Multinube conserva los lotes 1, 2 y 3 como subdivisiones; no se duplican señales ni se crean tres proyectos adicionales. No se equiparan automáticamente NGSA y NSGA. Una cita puede identificar un lote; si menciona varios o carece de evidencia, la subdivisión queda ambigua o pendiente.

El modo «Corpus por proyecto» permite recuperar únicamente fragmentos asignados a un proyecto. No depende de disponer de un perfil PIRD privado. Los proyectos sin fragmentos exclusivos devuelven ausencia de evidencia; no amplían la consulta al consolidado. Las vistas analíticas permanecen pendientes mientras no exista un perfil propio calculado.

La conciliación automática de los 345 fragmentos de 36 documentos identifica 237 fragmentos con un proyecto (DataR 186, Multinube 50, NSGA 1, NSGT 0 y PDIS 0), 59 ambiguos y 49 pendientes. Cero fragmentos exclusivos no significa que no existan menciones al proyecto: pueden estar en fragmentos mixtos. Son asignaciones automáticas, no un gold standard ni conteos de riesgos. results/day_20 conserva la conciliación, los identificadores de fragmento y hashes de catálogo y fuente; no incluye texto documental adicional.

Validación de esta etapa: 126 pruebas automatizadas aprobadas. Streamlit AppTest verificó el selector de cinco proyectos, la pantalla del chat, la ausencia de métricas globales en el radar sin perfil y el estado sin fragmentos de NSGT, sin excepciones. No se efectuaron nuevas llamadas a OpenAI en estas comprobaciones.

## Configuración y evidencia pendientes

PROJECT_CATALOG_JSON permite reemplazar el catálogo versionado desde el servidor, con projects (project_id, display_name, aliases), unassigned_project_id y multi_project_id. Sin esa configuración se utiliza el catálogo del corpus confirmado por la autora. Los proyectos nuevos que no pertenecen al catálogo conservan el estado de pertenencia no verificada.

Los 649 registros individuales completos del perfil histórico no están disponibles en esta copia del repositorio. La discriminación y el recálculo completo por proyecto requieren esos artefactos privados; no pueden reconstruirse a partir del agregado global. Los PIRD históricos filtrados conservan componentes calculados sobre el corpus completo y no acreditan recurrencia recalculada por proyecto.

No se incorporaron los documentos adicionales descartados por la autora ni se alteraron embeddings, corpus, pesos o resultados históricos. Esta etapa es implementación y verificación automatizada; todavía no es validación humana de las asignaciones.
