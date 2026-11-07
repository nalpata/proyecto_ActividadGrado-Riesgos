# Cierre técnico de noviembre de 2026

## Condiciones de trabajo

- Terminar y evaluar la solución antes de actualizar el informe.
- Ensayo del 13 de noviembre con la versión final del trabajo.
- Conservar documentos originales íntegros. No anonimizar.
- Se trabaja exclusivamente sobre el corpus y la línea base publicados. Todos los DOCX y ZIP adicionales recibidos en esta conversación quedan excluidos por decisión de la autora.
- No publicar los documentos nuevos en el repositorio público.
- Mantener el baseline histórico 3eedbb01e2af5ff0e42878e20c659fa194ac4c9a para comparación.

## Revisión frente a los objetivos del informe del 28 de septiembre

| Objetivo | Evidencia existente | Cierre por comprobar |
| --- | --- | --- |
| OE1 corpus | Inventario inicial 14; consolidado 36; 50 archivos con 36 hashes únicos | Conciliar corpus publicado y ejemplos de calidad sin ampliarlo |
| OE2 chunking | Comparación recursivo/estructural y auditoría dirigida | Conservar configuración; documentar muestras |
| OE3 embeddings | MiniLM/BGE-M3, 10 preguntas con 100 valoraciones | Validación externa del sistema seleccionado |
| OE4 recuperación | BgeM3Retriever sobre matriz normalizada | Aclarar alcance de base vectorial: la ruta vigente usa parquet y búsqueda matricial |
| OE5 RAG | Generación con fuentes y rama run_qa | Evaluar respuestas reales; plantilla de cinco casos sin diligenciar |
| OE6 HyDE/reranking | Experimentos de 20 preguntas y auditorías dirigidas | Mantener resultados negativos y limitaciones |
| OE7 extracción | Extracción documental v2 y procesamiento de sesión | Revisión experta sobre el corpus aprobado; declarar ausencia de test de otro proyecto |
| OE8 validación | Puerta determinista y métricas sobre muestras históricas | Evaluación independiente de vigilancia, tipo, categoría y evidencia |
| OE9 patrones | Clustering exploratorio; recurrencia entre documentos | Verificación con experto de relaciones semánticas |
| OE10 perfil | PIRD y timeline con política estricta de faltantes | Valoración experta S/P; revisar fechas, cobertura y agregaciones |
| OE11 visualización | Snapshot histórico y SESSION-19C | Comprobar vistas con ejecución real nueva |
| OE12 LangGraph | Cuatro nodos y dependencias inyectadas | Distinguir grafo, ruta histórica y pipeline de sesión; decidir integración requerida |
| OE13 conversación | Chat histórico; recuperador de sesión añadido localmente | Probar generación real, fuentes y navegación de sesión |
| OE14 evaluación | Pruebas de software y experimentos históricos | Ejecutar evaluación con experto y documentar alcance de independencia |

## Cambios locales de esta fase

SessionRetriever usa exclusivamente los chunks y vectores de la ingesta recibida. Rechaza índices mixtos, incompletos o con vectores inválidos. Reutiliza la búsqueda por similitud del retriever aprobado sin abrir archivos históricos.

La interfaz selecciona la ingesta del proyecto activo y habilita su consulta incluso antes de calcular el PIRD. Reprocesar documentos elimina el historial previo y el análisis anterior. El modo sintético de radar sigue sin chat documental.

Pruebas nuevas: ranking, filtro documental, mezcla de proyectos, índices independientes, fuentes del chat y vectores inválidos. Verificación inicial: 99 pruebas aprobadas. Comprobación adicional con Streamlit AppTest: nueve vistas sin excepciones, aviso de alcance de sesión, bloqueo sin credencial y bloqueo del proyecto nuevo al retirar su índice. Esta comprobación es programática; no sustituye inspección visual del despliegue ni generación real.

## Evidencia y dependencias pendientes

No se amplió el corpus ni se recalcularon los resultados históricos. No se utilizaron los adjuntos descartados.

Este entorno no dispone de OPENAI_API_KEY ni CALIBRATION_EXAMPLES_JSON. No copiar secretos al chat o al código. La configuración previamente descrita en Streamlit no se puede inferir como disponible localmente.

La ejecución real con BGE-M3 y el generador, la evaluación del experto, el despliegue y el cierre de los demás objetivos todavía deben verificarse. Las pruebas de software no acreditan calidad semántica ni utilidad profesional.

## Correcciones adicionales

- Filtrar los chunks autorizados antes del Top-k para no perder evidencia del proyecto fuera de un Top-50 global. El conjunto autorizado vacío devuelve cero fuentes.
- Los proyectos nuevos y las ingestas sin análisis no muestran los indicadores del consolidado como propios.
- Las categorías sin PIRD se serializan con puntuación nula.
- Los filtros aceptan categorías vacías y deselección total.
- El generador solo marca evidencia disponible si devuelve citas numéricas existentes; publica únicamente las fuentes citadas. Este control comprueba referencias, no veracidad semántica de la respuesta.
- La suite final alcanza 107 pruebas aprobadas, incluidas navegación de 18 combinaciones de modo/vista y comprobaciones de ausencia de indicadores históricos en proyectos nuevos o reemplazados.

## Pendientes que requieren evidencia real

La configuración actual de la aplicación remota, la generación con la cuenta de la autora y la valoración del experto no se han comprobado en esta fase. No se declara el proyecto completamente validado. La clasificación histórica por tipo/categoría presenta exactitud 0,3448 y debe analizarse con el experto; no se modifica el prompt sin evidencia comparativa.

## Ejecución en GitHub web

Se añade un workflow de GitHub Actions para ejecutar la suite sin credenciales ni llamadas LLM. Instala requirements-test.txt y ejecuta python -m pytest -q. Los resultados históricos y el corpus permanecen sin cambios.
