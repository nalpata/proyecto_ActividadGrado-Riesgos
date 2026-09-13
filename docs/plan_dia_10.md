# Día 10 · Timeline, persistencia y preparación del PIRD

## Objetivo

Normalizar la fecha documental, ordenar las señales y calcular persistencia temporal sin convertir fechas mencionadas dentro de la evidencia en fechas del documento.

## Fuentes de fecha

1. Fecha exacta en el nombre del archivo (`YYYYMMDD`, `DDMMYYYY` o mes escrito).
2. Mes en el nombre (`YYYYMM`), conservando precisión `MONTH`.
3. Fecha no disponible, sin imputación.

Los años fuera de 2020–2030 se marcan como anomalía. La fecha explícita de un compromiso se conserva como atributo del evento, pero no reemplaza la fecha documental.

## Variables temporales

- **Aparición:** primera señal semánticamente cercana observada.
- **Recurrencia:** señal posterior de la misma vecindad semántica.
- **Persistencia:** días entre la primera y última señal cercana en documentos fechados.
- **Escalamiento:** queda pendiente mientras no exista severidad temporal estandarizada.

## Persistencia

| Nivel | Regla |
|---:|---|
| 1 | Un único documento fechado o 0 días |
| 2 | 1–30 días |
| 3 | 31–90 días |
| 4 | 91–180 días |
| 5 | Más de 180 días |

La similitud mínima es 0,70, consistente con la recurrencia del Día 9.

## Condición para calcular el PIRD

El catálogo de 649 señales no contiene severidad ni probabilidad estandarizadas. El Día 10 no las inventa. El motor reporta el PIRD como pendiente y deja listas recurrencia, persistencia, evidencia y confianza.

Esta limitación debe permanecer visible en el trabajo final. Una fase posterior podrá enriquecer severidad y probabilidad mediante una rúbrica documentada y evaluación independiente.

## Resultado real

De 35 documentos, 29 pudieron fecharse mediante el nombre de archivo. Esto cubre 614 de las 649 señales. Seis documentos y 35 señales no tienen fecha documental confiable. El token `20140105` fue rechazado por estar fuera del periodo permitido y no se corrigió automáticamente.

La vecindad semántica permitió calcular persistencia para 638 señales: 304 quedaron en nivel 1, 31 en nivel 2, 38 en nivel 3, 24 en nivel 4 y 241 en nivel 5. Once señales permanecen pendientes por falta de fechas propias o vecinas.

Se identificaron 396 observaciones en la primera fecha disponible de su vecindad, 218 recurrencias posteriores, 24 señales sin fecha propia pero con contexto temporal vecino y 11 sin contexto temporal.

El PIRD calculado permanece en cero casos. Las 649 señales están pendientes de severidad y probabilidad estandarizadas. Esto es un control de integridad, no un fallo del motor.
