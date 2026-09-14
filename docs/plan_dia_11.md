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

## Alcance de la validación humana

El proyecto sí cuenta con un Gold Standard humano para validar la inclusión de señales, la necesidad de vigilancia y la suficiencia de la evidencia. Ese conjunto se consolidó durante los Días 1, 2 y 5.

El Gold Standard existente no incluye etiquetas humanas de severidad y probabilidad en escala 1–5, porque estos componentes se definieron posteriormente con el PIRD. Por ello, los niveles del Día 11 deben presentarse como una evaluación estructurada asistida por IA y no como una estimación probabilística observada o una calificación humana validada.

## Resultado real y decisión

El proceso evaluó 649 señales y calculó el PIRD en 372 (57,3 %). Las 277 restantes quedaron pendientes porque faltaba severidad, probabilidad o persistencia sustentada. El score global observado es 52,16, correspondiente al nivel alto.

La cobertura no es homogénea: Financiero 38,9 %, Contractual 48,1 %, Otro 50,0 %, Cronograma 58,4 %, Operación 63,2 %, Calidad 68,2 %, Gobierno del Proyecto y Seguridad 100 %. Por ello, el score global se etiqueta como **provisional**.

La sensibilidad de pesos ubica el score global entre 51,69 y 55,17 y mantiene el nivel alto. Las correlaciones Spearman entre rankings son 0,902–0,997. La conclusión sobre el nivel agregado es estable, pero no elimina el sesgo potencial por datos faltantes.
