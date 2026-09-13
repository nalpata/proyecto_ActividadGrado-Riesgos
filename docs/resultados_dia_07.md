# Día 7 · Evaluación del núcleo

## Objetivo

Comparar la extracción inicial, el prompt mejorado y la extracción con validación para seleccionar la configuración final del núcleo RAG y de riesgos.

## Comparabilidad

El valor histórico de Precision 64,6 % se conserva como referencia de la extracción inicial. No dispone de muestra, etiquetas negativas ni matriz de confusión reproducible; por tanto, no es posible calcular responsablemente Recall o F1 ni usarlo como comparación pareada.

El prompt mejorado v2 y la extracción con validación sí se evaluaron sobre las mismas 29 etiquetas humanas: 21 positivas y 8 negativas.

## Resultados

| Configuración | Muestra comparable | Precision | Recall | F1 | Accuracy | Especificidad |
|---|---|---:|---:|---:|---:|---:|
| Extracción inicial histórica | No | 64,6 % | No calculable | No calculable | No calculable | No calculable |
| Prompt mejorado v2 | Sí, n=29 | 81,8 % | 42,9 % | 56,3 % | 51,7 % | 75,0 % |
| Extracción + validación | Sí, n=29 | **81,8 %** | **85,7 %** | **83,7 %** | **75,9 %** | 50,0 % |

Frente al prompt v2, la validación recupera nueve verdaderos positivos adicionales y produce dos falsos positivos adicionales. Mantiene la misma Precision porque ambas cantidades aumentan proporcionalmente. La especificidad se considera preliminar porque solo existen ocho negativos.

## Configuración seleccionada

### Recuperación

- Consulta original.
- Embeddings `BAAI/bge-m3`.
- Chunking recursivo existente.
- Sin HyDE.
- Sin reranking.

### Riesgos

- Extracción documental v2.
- Clasificador calibrado con ejemplos humanos.
- Evaluación leave-one-out.
- Agente validador con vigilancia positiva, evidencia suficiente y evidencia verificada.
- Tipo documental y categoría como atributos auxiliares.

## Conclusión

Se selecciona **extracción + validación** porque obtiene el mayor F1 y Recall en la comparación pareada, manteniendo la Precision del prompt mejorado. Esta configuración constituye el núcleo final que alimentará las siguientes etapas del prototipo.
