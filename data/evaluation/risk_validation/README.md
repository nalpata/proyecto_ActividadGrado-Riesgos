# Evaluación y validación de riesgos

Esta carpeta contiene los insumos y resultados utilizados para evaluar la extracción estructurada de riesgos.

Si el archivo original de evaluación no está disponible, se debe reconstruir el baseline con `notebooks/09b_reconstruir_baseline_colab.ipynb`. La nueva ejecución se conserva como un experimento distinto del resultado histórico de junio.

## Agente validador

El notebook `notebooks/13_validacion_automatica_riesgos_colab.ipynb` ejecuta una segunda etapa independiente. El validador contrasta cada candidato con el chunk fuente, decide su validez, revisa la categoría, determina suficiencia de evidencia y explica su decisión. Las etiquetas humanas disponibles se reservan para evaluación y no se incluyen en el prompt.

Salidas principales:

- `risk_validation_results.xlsx`: decisiones para los 156 candidatos.
- `validation_review_sample.xlsx`: muestra dirigida de 35 casos.
- `validator_metrics.json`: Precision, Recall, F1 y matriz de confusión sobre etiquetas humanas.
- `validation_log.csv`: trazabilidad de las respuestas.

## Día 1: diagnóstico de falsos positivos

### Entrada requerida

El archivo completo generado en el notebook `09_extraccion_riesgos.ipynb`, idealmente:

```text
riesgos_evaluation_template.xlsx
```

Debe incluir los 96 riesgos extraídos y la columna manual:

```text
riesgo_valido_manual
```

Valores permitidos: `1` para riesgo válido y `0` para falso positivo.

El repositorio conserva actualmente los 62 riesgos válidos usados por el timeline, pero no incluye los 34 falsos positivos. Por eso no se deben reconstruir ni inventar esos registros: se debe recuperar el archivo original de evaluación.

### Ejecución por terminal

Desde la raíz del repositorio:

```bash
python src/evaluation/analyze_false_positives.py \
  --input data/evaluation/risk_validation/riesgos_evaluation_completa.xlsx \
  --output-dir data/evaluation/risk_validation/day_01
```

En Windows PowerShell puede ejecutarse en una sola línea:

```powershell
python src/evaluation/analyze_false_positives.py --input data/evaluation/risk_validation/riesgos_evaluation_completa.xlsx --output-dir data/evaluation/risk_validation/day_01
```

### Salidas

- `plantilla_diagnostico_falsos_positivos.xlsx`: archivo para completar la causa de cada error.
- `false_positives.csv`: únicamente los registros marcados con `0`.
- `by_category.csv`: falsos positivos por categoría de riesgo.
- `by_document.csv`: falsos positivos por documento.
- `by_error_type.csv`: distribución de causas, después de completar la clasificación manual.
- `metricas_baseline_extraccion.json`: total, válidos, falsos positivos y precisión.
- `taxonomia_falsos_positivos.csv`: definiciones de los tipos de error.

### Regla metodológica

La columna `tipo_error_sugerido` es solamente una ayuda heurística. La clasificación válida para el trabajo de grado es `tipo_error_manual`, diligenciada mediante revisión humana de la evidencia.
