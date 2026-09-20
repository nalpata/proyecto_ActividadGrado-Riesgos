# Día 14 · Pruebas y congelamiento del backend

## Objetivo

Cerrar una interfaz estable entre el pipeline aprobado y el front, sin recalcular resultados ni exponer evidencia privada.

## Alcance ejecutado

1. Validar el flujo completo y sus cuatro etapas.
2. Verificar rutas y formatos de los agregados aprobados.
3. Manejar ausencia de evidencia, respuesta vacía del modelo y fallo del servicio de respuesta.
4. Registrar errores operativos en JSONL privado, sin pregunta, chunks ni señales.
5. Congelar el contrato público `1.0.0` para el front.
6. Conciliar automáticamente totales, cobertura, categorías y distribución PIRD.

## Contrato congelado

El front consumirá `results/day_14/backend_snapshot_v1.json`. Sus secciones estables son:

- `profile`: PIRD global, nivel, cobertura, estado provisional y totales.
- `categories`: score, nivel y cobertura por categoría.
- `level_distribution`: distribución de las 372 señales puntuadas.
- `sensitivity`: escenarios aprobados de pesos.
- `runtime`: prueba pública sintética del pipeline.
- `data_policy`: garantías de privacidad y política de nulos.

No contiene fragmentos, evidencia, preguntas, respuestas, señales individuales ni credenciales.

## Criterios de cierre

- 649 = 372 puntuadas + 277 pendientes.
- 372 = 79 bajas + 139 medias + 132 altas + 22 críticas.
- Totales por categoría = 649; puntuadas por categoría = 372.
- Cobertura global = 57,32 % y perfil `PROVISIONAL`.
- Los errores de Q&A no interrumpen la serialización del resultado.
- Una respuesta vacía queda marcada explícitamente.
- Todas las pruebas del repositorio finalizan satisfactoriamente.

## Restricciones preservadas

Se mantienen consulta original, BGE-M3 y chunking recursivo. HyDE y reranking siguen descartados. El PIRD no se interpreta como probabilidad y no se imputan datos faltantes.
