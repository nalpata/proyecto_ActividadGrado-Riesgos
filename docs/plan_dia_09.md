# Día 9 · Clustering semántico y recurrencia

## Objetivo

Identificar familias semánticas exploratorias entre las 649 señales aceptadas y derivar una medida reproducible de recurrencia para el PIRD.

## Diseño

1. Representar título, descripción y evidencia mediante `BAAI/bge-m3`.
2. Normalizar los embeddings y evaluar K-Means entre 2 y 12 clusters.
3. Repetir cada candidato con cinco semillas.
4. Seleccionar `k` por el menor rango promedio de Silhouette coseno, Calinski-Harabasz, Davies-Bouldin y estabilidad ARI.
5. Extraer términos representativos y categoría predominante para apoyar el nombramiento humano de las familias.
6. Comparar clusters y categorías existentes mediante ARI, NMI y pureza.

## Recurrencia para el PIRD

La primera ejecución mostró que los clusters globales aparecían en 11 o más documentos y asignaban nivel 5 a todas las señales. La recurrencia se corrigió para usar vecindarios semánticos locales: cuenta cuántos **otros documentos** contienen al menos una señal con similitud coseno igual o superior a 0,70.

| Nivel | Documentos distintos |
|---:|---:|
| 1 | 0 |
| 2 | 1 |
| 3 | 2–3 |
| 4 | 4–6 |
| 5 | 7 o más |

Esta variable expresa propagación documental de una familia, no probabilidad ni severidad.

El umbral 0,70 es una hipótesis operacional explícita. Se reportará su sensibilidad entre 0,68 y 0,72 antes de congelar el Día 9.

## Controles metodológicos

- Los clusters son familias exploratorias, no verdad de terreno.
- K-Means asigna toda señal a un cluster; por ello se reportan métricas e interpretabilidad.
- La categoría existente no se utiliza para construir clusters, solo para compararlos.
- Los textos y las asignaciones por señal permanecen fuera del repositorio público.
- La denominación automática por términos debe revisarse conceptualmente antes de congelar las familias.

## Salidas

- Embeddings y asignaciones privadas.
- Métricas de selección de `k`.
- Resumen agregado por cluster.
- Comparación frente a categorías.
- Nivel de recurrencia por señal para integrarlo posteriormente al PIRD.

## Resultado del experimento

La regla combinada seleccionó `k=6`. La estabilidad fue 0,776, pero la separación absoluta fue baja (Silhouette coseno 0,077). La correspondencia con las categorías existentes también fue baja: ARI 0,050, NMI 0,140 y pureza 0,414.

Los seis grupos se interpretan como temas exploratorios asociados a cronograma y entregas; requerimientos e interventoría; incumplimientos y cierre; gestión contractual; planeación y operación; y recursos financieros. No sustituyen la taxonomía actual.

Con el vecindario semántico local y umbral 0,70, los niveles de recurrencia fueron: 266 señales en nivel 1, 157 en nivel 2, 128 en nivel 3, 55 en nivel 4 y 43 en nivel 5. Esta distribución sí discrimina señales y se utilizará como entrada del PIRD.

La sensibilidad entre 0,68 y 0,72 confirma que el umbral afecta la distribución. Por tanto, 0,70 se conserva como parámetro operacional explícito y constituye una limitación del modelo.
