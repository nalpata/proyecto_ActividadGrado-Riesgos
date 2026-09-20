# Día 13 · Automatización de extremo a extremo

## Objetivo

Conectar el grafo del Día 12 con los artefactos reales seleccionados para producir, en una sola ejecución, una respuesta RAG trazable y un perfil agregado de riesgo.

## Configuración definitiva

El plan inicial mencionaba HyDE y reranking como componentes posibles. Los experimentos de los días 3 y 4 los descartaron. La automatización usa consulta original, BGE-M3, chunking recursivo y Top-k, sin reabrir esas decisiones.

## Flujo

```text
Pregunta
  -> Retrieval BGE-M3
  -> Respuesta RAG con fuentes
  -> Catálogo calibrado privado
  -> Puerta determinista
  -> Perfil agregado congelado del Día 11
  -> Salida integrada y checkpoint privado
```

El catálogo calibrado y las evaluaciones individuales se suministran en tiempo de ejecución y no se publican. El perfil agregado se carga desde los resultados públicos aprobados.

## Reanudación

Cada solicitud puede guardarse en un checkpoint JSON privado. La reanudación evita repetir retrieval, validación y llamadas al LLM. Las carpetas `runtime/`, `checkpoints/` y `results/private/` están excluidas de Git.

## Salida

La salida privada contiene `qa_result`, `risk_result` y `execution`. La función `public_execution_summary` deriva un resumen sin respuesta, fuentes textuales, evidencia ni señales individuales.

## Criterios de cierre

1. Retrieval usa embeddings BGE-M3 existentes y admite filtro documental.
2. La respuesta RAG cita fuentes y declara ausencia de evidencia.
3. El catálogo calibrado privado alimenta la puerta determinista existente.
4. El perfil conserva PIRD 52,16, nivel ALTO, cobertura 57,3 % y condición PROVISIONAL.
5. La ejecución puede reanudarse desde checkpoint.
6. Las pruebas públicas no requieren clave ni datos privados.
