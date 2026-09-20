# Día 18B · Integración y experiencia de usuario

## Objetivo

Cerrar el Día 18 original conectando el asistente con la rama conversacional del pipeline final y completando los controles de experiencia de usuario, sin recalcular ni alterar el perfil PIRD aprobado.

## Alcance

1. Ejecutar las consultas mediante `EndToEndPipeline.run_qa`.
2. Mantener la configuración seleccionada: consulta original, BGE-M3, Top-k y respuesta RAG.
3. Mostrar carga, ausencia de evidencia y errores mediante mensajes diferenciados.
4. Incorporar preguntas demostrativas seleccionables.
5. Validar la recepción de PDF/DOCX y explicar el alcance académico de la carga.
6. Conservar el radar sobre el corpus procesado y el contrato congelado.

## Decisión metodológica

Una consulta conversacional no vuelve a ejecutar extracción, validación ni perfilamiento. Esas etapas producirían un recálculo innecesario del PIRD y romperían el contrato congelado del backend. La rama Q&A reutiliza únicamente retrieval y generación del pipeline final.

La carga de documentos funciona como entrada validada en sesión. La reindexación y recalibración automática de documentos nuevos se declaran fuera del alcance del prototipo académico y como evolución futura.

## Criterios de cierre

- El asistente entra por la clase `EndToEndPipeline`.
- Las fuentes visibles excluyen texto de chunks e identificadores internos.
- Las rutas sin evidencia y con error terminan de forma controlada.
- Las preguntas demostrativas pueden ejecutarse con un clic.
- No permanece texto que anuncie la integración como pendiente del Día 18.
- La suite automatizada y todas las vistas Streamlit finalizan sin excepciones.
