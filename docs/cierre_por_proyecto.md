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

Sin catálogo, se mantiene compatibilidad operativa y se declara USER_DECLARED_UNVERIFIED: la selección del usuario no acredita identidad documental. El front muestra esta limitación. No se inventan proyectos ni se publica un catálogo real.

## Configuración y evidencia pendientes

El catálogo privado utiliza PROJECT_CATALOG_JSON con projects (project_id, display_name, aliases), unassigned_project_id y multi_project_id. Debe acordarse la granularidad de los proyectos y sus lotes antes de activarlo.

Los 649 registros individuales completos del perfil histórico no están disponibles en esta copia del repositorio. La discriminación y el recálculo completo por proyecto requieren esos artefactos privados; no pueden reconstruirse a partir del agregado global. Los PIRD históricos filtrados conservan componentes calculados sobre el corpus completo y no acreditan recurrencia recalculada por proyecto.

No se incorporaron los documentos adicionales descartados por la autora ni se alteraron embeddings, corpus, pesos o resultados históricos. Esta etapa es implementación y verificación automatizada; todavía no es validación humana de las asignaciones.
