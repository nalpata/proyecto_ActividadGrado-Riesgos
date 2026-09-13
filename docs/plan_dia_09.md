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

La recurrencia no se define por el número bruto de frases. Se utiliza el número de documentos independientes en los que aparece la familia:

| Nivel | Documentos distintos |
|---:|---:|
| 1 | 1 |
| 2 | 2 |
| 3 | 3–4 |
| 4 | 5–7 |
| 5 | 8 o más |

Esta variable expresa propagación documental de una familia, no probabilidad ni severidad.

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
