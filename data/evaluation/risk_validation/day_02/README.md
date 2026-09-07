# Día 2 · Catálogo operativo de señales de riesgo

## Objetivo

Transformar los 156 candidatos del baseline y las decisiones del validador v2
en un insumo trazable para el radar y la aplicación Streamlit.

## Regla de decisión

1. Para los 35 registros de la muestra adjudicada se usa `human_final`.
2. Para los 121 registros restantes se usa la decisión del validador v2.
3. Una señal automática se incluye solo si el validador la acepta y considera
   suficiente su evidencia.
4. La deduplicación no borra filas: marca `duplicate_group` y define
   `operational_is_primary` para evitar doble conteo en el radar.

## Archivos

- `operational_risk_catalog.csv`: catálogo completo y trazable.
- `radar_by_category.csv`: agregado que consumirá inicialmente el radar.
- `risk_review_queue.csv`: decisiones automáticas de baja confianza o evidencia
  insuficiente.
- `operational_catalog_summary.json`: controles y cifras de ejecución.

## Interpretación del radar

El puntaje por categoría está entre 0 y 100 y combina la intensidad media
(70 %) con el mayor riesgo observado (30 %):

```text
radar_score = 100 × (0,70 × promedio_risk_score/9 + 0,30 × máximo_risk_score/9)
```

El puntaje mide exposición documental relativa en este corpus; no representa
una probabilidad estadística de materialización.

## Limitación

Solo 35 de los 156 registros fueron adjudicados por una persona y la muestra
contiene pocos negativos. Las demás decisiones proceden del validador v2. Este
resultado es apropiado para el prototipo académico, no para decisiones
productivas autónomas.
