# Resultados del Día 14

## Estado

Backend estable y contrato público `1.0.0` congelado para iniciar el front del Día 15.

## Verificaciones

- Ejecución privada reportada por la autora: `COMPLETED` en las cuatro etapas.
- PIRD global conservado: 52,16, nivel ALTO.
- Cobertura conservada: 57,32 %, estado PROVISIONAL.
- Conciliación global, por nivel y por categoría aprobada.
- Ausencia de evidencia manejada sin llamada al LLM.
- Respuesta vacía del modelo manejada con estado `EMPTY_MODEL_RESPONSE`.
- Fallo del generador manejado como salida controlada y registro JSONL privado.
- Checkpoints y registros privados permanecen excluidos del repositorio.
- 51 pruebas aprobadas.

## Salida para el front

`results/day_14/backend_snapshot_v1.json` es la única fuente agregada congelada para construir las vistas del Día 15. Los componentes visuales no deben leer archivos por señal ni depender de la estructura interna del pipeline.

## Limitación vigente

El perfil sigue siendo provisional porque la cobertura es inferior al 80 % y el Gold Standard humano existente no incluye etiquetas independientes 1–5 de severidad y probabilidad.
