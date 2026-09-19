# Día 12 · Arquitectura multiagente sencilla

## Objetivo

Implementar en LangGraph un grafo funcional, coordinado, observable y reproducible con cuatro responsabilidades delimitadas: recuperación de evidencia, extracción de candidatos, validación determinista y consolidación del perfil de riesgo.

## Decisiones heredadas

- El retrieval usa consulta original, BGE-M3 y chunking recursivo.
- HyDE, reranking y chunking estructural permanecen descartados como configuración principal.
- La extracción usa la versión documental v2 y la clasificación calibrada del Día 5.
- El validador aplica la puerta determinista del Día 6; no realiza una llamada LLM adicional.
- El perfil conserva el PIRD v1, los faltantes estrictos y la condición provisional del Día 11.
- No se publican fragmentos, evidencia, evaluaciones individuales ni otros artefactos privados.

## Grafo

```text
START
  -> Retrieval Agent
  -> Risk Extractor Agent
  -> Risk Validator Agent
  -> Risk Profiler Agent
  -> END
```

Las rutas `NO_EVIDENCE`, `NO_CANDIDATES`, `NO_VALIDATED_SIGNALS` y `ERROR` terminan de forma controlada y no fabrican resultados posteriores.

## Contrato de estado

El estado compartido mantiene un identificador de solicitud, pregunta, filtro de documentos, chunks recuperados, candidatos, decisiones, señales aceptadas, perfil, estado, errores y traza de ejecución. La traza pública registra cantidades y tiempos, pero no copia texto documental.

## Alcance del Día 12

El Día 12 construye la orquestación y sus contratos. Las operaciones de dominio se inyectan para reutilizar los módulos existentes, permitir pruebas sin credenciales y mantener fuera del repositorio los artefactos privados. La conexión operativa desde documentos hasta el perfil completo corresponde al Día 13.

## Criterios de cierre

1. Los cuatro nodos se ejecutan en el orden definido.
2. Las rutas vacías y los errores terminan de forma explícita.
3. La validación sigue siendo determinista.
4. HyDE y reranking no forman parte de la configuración seleccionada.
5. Las pruebas no requieren clave de OpenAI ni datos privados.
6. El resultado se documenta y se revisa antes de fusionarse con `main`.
