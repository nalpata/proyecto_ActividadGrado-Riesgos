# Día 17 · Asistente conversacional documental

## Objetivo

Habilitar consultas sobre los documentos del proyecto mediante el retrieval directo BGE-M3 y la generación RAG aprobados, con respuestas sustentadas y fuentes visibles.

## Flujo

1. El usuario formula una pregunta sobre el proyecto activo.
2. BGE-M3 recupera hasta cinco fragmentos relevantes con la consulta original.
3. El modelo responde únicamente con esos fragmentos.
4. La interfaz presenta respuesta, documentos, páginas y scores de similitud.
5. Si no existe evidencia, el sistema informa que no puede responder.

## Controles

- No se utilizan HyDE ni reranking.
- La clave OpenAI se obtiene únicamente de Streamlit Secrets o del entorno del servidor.
- La aplicación no solicita ni muestra la clave.
- El historial no almacena textos de chunks, identificadores internos ni evidencia completa.
- Los fallos producen un mensaje controlado sin publicar detalles privados.
- Los proyectos nuevos permanecen deshabilitados hasta tener un índice documental.

## Criterios de cierre

- El chat acepta preguntas y conserva un historial acotado por proyecto.
- Las respuestas sustentadas incluyen fuentes.
- La ausencia de evidencia y los errores están controlados.
- La clave no aparece en el repositorio ni en la interfaz.
- La suite completa y las nueve vistas Streamlit pasan.
