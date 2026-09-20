# Resultados del Día 19B

## Resultado funcional

La aplicación incorpora la acción `Analizar riesgos · Día 19B` después de una ingesta exitosa. El procesamiento usa exclusivamente los chunks del proyecto activo, extrae y valida señales, calcula recurrencia y persistencia, evalúa los componentes sustentados y construye el PIRD disponible.

## Integración del trabajo previo

- Día 4B: chunking recursivo aprobado.
- Día 5: taxonomía y contrato del clasificador documental.
- Día 6: validación determinista de evidencia y vigilancia.
- Día 9: embeddings BGE-M3 y recurrencia semántica.
- Día 10: fechas y persistencia sin imputación.
- Día 11: severidad, probabilidad y PIRD con componentes completos.

## Privacidad y trazabilidad

- Se rechaza cualquier lote que contenga chunks de otro proyecto.
- Texto, citas, señales, evaluaciones y vectores permanecen en memoria de sesión.
- La interfaz muestra conteos, cobertura, PIRD global y categorías agregadas.
- Los ejemplos humanos del Día 5 se leen únicamente desde un secreto privado opcional.
- En ausencia de esos ejemplos, el resultado se marca como provisional y no como calibrado.

## Verificación

- 90 pruebas automatizadas aprobadas.
- 18 combinaciones Streamlit renderizadas sin excepciones.
- Prueba integral sintética del 19A→19B con dos documentos, recurrencia, persistencia y PIRD calculado.
- Prueba explícita de rechazo de chunks pertenecientes a otro proyecto.
- Revisión de diferencias sin publicación de documentos, evidencia ni secretos.

## Salida para el Día 19C

La sesión conserva un contrato con `summary`, `classification`, `validation`, `timeline`, `categories`, `usage` y un bloque `private` no renderizado. El Día 19C podrá convertir los agregados del proyecto recién procesado en las vistas de radar, timeline, priorización y perfil, sustituyendo el snapshot consolidado solo dentro de esa sesión.
