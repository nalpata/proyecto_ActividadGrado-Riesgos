# Resultados del Día 18B

## Integración

El asistente quedó conectado a `EndToEndPipeline.run_qa`. Esta ruta ejecuta retrieval BGE-M3 y respuesta RAG, registra la traza de ambas etapas y evita recalcular el perfil PIRD durante una consulta.

## Experiencia de usuario

- Indicador visible mientras se recupera evidencia y se genera la respuesta.
- Mensajes diferenciados para respuesta sustentada, ausencia de evidencia y error.
- Tres preguntas demostrativas seleccionables.
- Validación de recepción y archivos vacíos en la carga PDF/DOCX.
- Textos actualizados para separar capacidad académica y evolución productiva.

## Controles

- 80 pruebas automatizadas aprobadas.
- Renderizado de Streamlit verificado sin excepciones.
- El historial conserva únicamente la pregunta, la respuesta y metadatos públicos de fuentes.
- No almacena texto de chunks ni identificadores internos.
- Una consulta no modifica el radar ni los resultados PIRD congelados.
- La demostración sintética por proyectos continúa separada del corpus documental real.

## Limitación declarada

El prototipo recibe y valida nuevos documentos, pero no los reindexa ni recalcula automáticamente el radar desde la interfaz pública. Esa capacidad requiere un proceso privado de ingestión, control de calidad y aprobación antes de modificar el perfil de riesgo.
