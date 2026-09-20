# Resultados del Día 19A

## Resultado funcional

La aplicación procesa PDF/DOCX nuevos mediante una acción explícita. La ingesta extrae y limpia el texto, genera chunks recursivos y produce embeddings BGE-M3 normalizados vinculados al proyecto activo.

## Controles implementados

- Validación de PDF/DOCX, archivos vacíos, cantidad y tamaño.
- Detección por hash de duplicados dentro de la misma carga.
- Rechazo controlado de documentos sin texto extraíble.
- Identificadores deterministas por proyecto y contenido.
- Procesamiento parcial cuando al menos un documento es válido.
- Permanencia exclusiva en memoria de sesión.
- Mensaje explícito de que el recálculo de riesgos corresponde al Día 19B.

## Verificación

- 85 pruebas automatizadas aprobadas.
- 18 combinaciones de renderizado verificadas sin excepciones: nueve vistas consolidadas y nueve vistas del modo sintético.
- Pruebas sintéticas de extracción PDF/DOCX, chunking, vectores, duplicados y cargas inválidas.

## Salida para el Día 19B

La sesión conserva un contrato con `documents`, `chunks`, `errors`, `summary` y `configuration`. Cada chunk contiene su proyecto, documento, página, texto limpio, estrategia de fragmentación y embedding normalizado. El Día 19B consumirá este contrato para extraer y validar señales y recalcular el perfil PIRD.
