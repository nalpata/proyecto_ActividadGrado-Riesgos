# Día 6 · Agente validador

## Objetivo

Implementar una segunda revisión automática que determine si existe evidencia suficiente, si la evidencia soporta la señal, si requiere vigilancia y por qué se acepta o rechaza.

## Reutilización del trabajo anterior

El validador v1/v2 del Día 1 y el clasificador calibrado del Día 5 ya producen las estimaciones semánticas. El Día 6 las integra en una puerta determinista, reproducible y sin nuevas llamadas a OpenAI.

## Regla final

Un elemento se acepta únicamente cuando:

1. `calibrated_watch = 1`.
2. `calibrated_evidence_sufficient = 1`.
3. La evidencia textual está presente y fue verificada contra el chunk.

La confianza se conserva como información explicativa. No se usa como umbral porque todavía no se ha evaluado su calibración probabilística.

## Salidas

- `validation_decisions.csv`: todas las decisiones y sus razones.
- `validated_surveillance_catalog.csv`: elementos aceptados.
- `validation_rejections.csv`: elementos rechazados.
- `validation_agent_summary.json`: controles y distribución agregada.

## Interpretación

Los rechazos automáticos son elementos excluidos por las reglas operativas; no deben presentarse todos como falsos positivos confirmados. La reducción real de falsos positivos se reporta con las 29 etiquetas humanas del Día 5: Precision 81,8 %, con 4 falsos positivos, 18 verdaderos positivos, 4 verdaderos negativos y 3 falsos negativos.
