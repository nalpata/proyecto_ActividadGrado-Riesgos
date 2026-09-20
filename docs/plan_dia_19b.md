# Día 19B · Recálculo de riesgos por proyecto

## Objetivo

Consumir la salida en memoria del Día 19A para identificar y validar señales documentales y recalcular el perfil PIRD del proyecto activo sin mezclar proyectos ni publicar evidencia privada.

## Flujo

1. Validar que todos los chunks pertenezcan al proyecto activo.
2. Aplicar la extracción documental v2 y comprobar que cada cita sea literal.
3. Clasificar por tipo, vigilancia, suficiencia y categoría.
4. Aplicar la puerta determinista: evidencia verificada, suficiente y vigilancia positiva.
5. Generar embeddings BGE-M3 de las señales aceptadas.
6. Calcular recurrencia entre documentos con umbral coseno 0,70.
7. Calcular persistencia solo con fechas documentales válidas en el nombre del archivo.
8. Evaluar severidad y probabilidad únicamente cuando la cita las sustente.
9. Calcular PIRD cuando estén presentes sus seis componentes.
10. Mostrar únicamente agregados seguros en la interfaz.

## Controles metodológicos

- Máximo 100 chunks por ejecución.
- Cero imputación de fecha, severidad o probabilidad.
- Separación estricta por `project_id` antes de llamar al modelo.
- Evidencia y resultados por señal solo en memoria de sesión.
- Calibración humana activa únicamente si los ejemplos privados se suministran mediante `CALIBRATION_EXAMPLES_JSON`.
- Sin ejemplos privados, clasificación rotulada como provisional.
- El Día 19B muestra una vista agregada previa; la sustitución del radar global corresponde al Día 19C.

## Criterios de cierre

- El flujo 19A→19B termina con agregados por proyecto.
- Las señales sin componentes suficientes permanecen pendientes.
- La aplicación informa el estado real de calibración.
- La suite automatizada y las combinaciones de vistas no presentan regresiones.
- Ningún contenido privado nuevo queda incluido en GitHub.
