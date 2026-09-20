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

## Validación pendiente

El entorno de implementación no dispone de `OPENAI_API_KEY`; por ello, la llamada real debe validarse después de configurar la clave como secreto del servidor de Streamlit. La suite usa dobles deterministas y valida el contrato completo sin consumir llamadas externas.
