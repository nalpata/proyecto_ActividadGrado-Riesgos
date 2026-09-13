# Día 8 · Diseño del índice compuesto de riesgo

## Decisión metodológica

El Día 8 especifica y prueba el PIRD, pero no calcula scores definitivos sobre las 649 señales. La recurrencia depende del clustering del Día 9 y la persistencia depende del timeline del Día 10.

## Modelo

El índice de exposición separa la magnitud del riesgo de la confiabilidad de su evaluación:

`IE = 0,40S + 0,25P + 0,20R + 0,15T`

`IC = 0,60E + 0,40C`

`PIRD = 100 × IE × (0,70 + 0,30IC)`

Cada componente utiliza una rúbrica de 1 a 5 y se normaliza a 0–1 mediante `(nivel - 1) / 4`.

## Justificación de pesos

- Severidad recibe 40 % porque representa la magnitud del impacto.
- Probabilidad recibe 25 % porque diferencia una exposición remota de una materialización probable.
- Recurrencia recibe 20 % como señal de repetición independiente.
- Persistencia recibe 15 % para reflejar duración sin dominar la magnitud del impacto.
- Evidencia y confianza no se suman a la exposición: forman un índice de confiabilidad que modula como máximo 30 % del resultado.

Los pesos son una hipótesis metodológica experta, no parámetros aprendidos. Deben someterse a sensibilidad y documentarse como limitación.

## Política de datos faltantes

Si falta cualquier componente, el motor devuelve `PENDIENTE_ENRIQUECIMIENTO` y no calcula el PIRD. Esto evita imputar recurrencia o persistencia antes de los Días 9 y 10.

## Umbrales iniciales

| Nivel | Rango |
|---|---:|
| Bajo | 0 a <25 |
| Medio | 25 a <50 |
| Alto | 50 a <75 |
| Crítico | 75 a 100 |

Los umbrales también son hipótesis de diseño y se revisarán cuando exista el catálogo consolidado.

## Validación del diseño

La prueba de sensibilidad utiliza cuatro casos controlados y cuatro escenarios de pesos: propuesto, iguales, énfasis en severidad y énfasis temporal. Estos casos no representan riesgos reales y no deben incorporarse al radar.
