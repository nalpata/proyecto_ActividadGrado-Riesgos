# Día 19A · Ingesta automática por proyecto

## Objetivo

Convertir los documentos PDF/DOCX cargados por el usuario en chunks y embeddings BGE-M3 asociados al proyecto activo, reutilizando la configuración seleccionada experimentalmente en los días iniciales.

## Flujo

1. Recepción controlada de PDF/DOCX.
2. Validación de formato, tamaño, cantidad, contenido y duplicados.
3. Extracción de texto con PyMuPDF o python-docx.
4. Limpieza y normalización textual.
5. Chunking recursivo de 2.200 caracteres con solapamiento de 300.
6. Embeddings normalizados `BAAI/bge-m3`.
7. Asociación de documentos, chunks y vectores con el proyecto activo.
8. Conservación exclusiva en memoria de la sesión.

## Decisiones preservadas

- Consulta original y BGE-M3.
- Chunking recursivo seleccionado en el Día 4B.
- Sin HyDE, reranking ni chunking estructural.
- Sin publicación de texto, documentos o embeddings.
- Sin recalcular todavía señales o PIRD.

## Límites operativos

- Máximo 10 documentos por ejecución.
- Máximo 20 MB por archivo y 50 MB totales.
- Formatos PDF y DOCX.
- Los PDF escaneados sin capa de texto quedan rechazados y requieren OCR futuro.
- La información se pierde al finalizar la sesión porque no se implementa persistencia privada en esta fase.

## Criterios de cierre

- Los documentos válidos producen texto, chunks y embeddings.
- Los chunks respetan la configuración aprobada.
- Los embeddings están normalizados y asociados al proyecto.
- Los duplicados y archivos inválidos terminan con mensajes controlados.
- Ningún documento ni vector se escribe en GitHub.
- La suite automatizada y la aplicación Streamlit finalizan sin excepciones.
