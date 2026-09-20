# Resultados del Día 17

## Estado

El asistente documental quedó conectado al retrieval BGE-M3 y al generador RAG existentes. La aplicación ofrece historial por proyecto, fuentes verificables y manejo controlado de ausencia de evidencia y errores.

## Verificación

- 68 pruebas aprobadas.
- 9 de 9 vistas Streamlit renderizadas sin excepciones.
- Preguntas vacías o mayores a 1.000 caracteres rechazadas.
- Historial limitado a 20 intercambios por proyecto.
- Fuentes públicas limitadas a rango, documento, página y score.
- Sin texto de chunks, identificadores internos ni claves en la interfaz.
- HyDE y reranking continúan excluidos.

## Validación en la aplicación publicada

El 20 de septiembre de 2026 se ejecutó en Streamlit la consulta real `¿Qué retrasos requieren vigilancia según los documentos?`, con la clave configurada únicamente como secreto del servidor.

- La respuesta identificó informes pendientes, requerimientos en riesgo de atraso y riesgos de incumplimiento.
- Se mostraron 5 fuentes recuperadas mediante BGE-M3.
- Cada fuente presentó rango, nombre del documento, página y similitud.
- Los scores observados estuvieron entre 0.569 y 0.602.
- No se expusieron texto de chunks, identificadores internos ni la clave de API.
- La primera consulta cargó correctamente los pesos del modelo y completó la generación RAG.

Con esta ejecución queda validado de extremo a extremo el flujo pregunta → recuperación → respuesta → fuentes.
