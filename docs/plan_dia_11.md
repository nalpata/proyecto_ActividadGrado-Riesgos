# Día 11 · Perfil Inteligente de Riesgo del Proyecto

## Objetivo

Completar severidad y probabilidad mediante una rúbrica explícita, calcular el PIRD individual cuando estén disponibles los seis componentes y consolidar el perfil ejecutivo.

## Control previo

El catálogo no contenía severidad ni probabilidad estandarizadas. Un modelo evalúa ambos componentes únicamente desde la descripción y la evidencia. Recurrencia y persistencia no se muestran durante esta evaluación para evitar doble conteo y circularidad.

El modelo puede declarar un componente no sustentado. En ese caso queda nulo y el PIRD individual no se calcula.

## Agregación

El score por categoría combina 70 % del PIRD promedio y 30 % del percentil 90. El score global combina 70 % del promedio simple de categorías y 30 % de la categoría con mayor score.

Este diseño evita que una categoría domine solo por contener más documentos o señales.

## Salidas

- PIRD individual y estado de cálculo.
- Perfil agregado por categoría.
- Score y nivel global.
- Principales categorías.
- Señales altas, críticas y persistentes.
- Base para recomendaciones y visualización ejecutiva.

## Limitación

No existe todavía un Gold Standard humano independiente para severidad y probabilidad. Los resultados deben presentarse como evaluación estructurada asistida por IA, no como estimación probabilística observada.
