# Evaluación HyDE

Esta carpeta recibirá los resultados del experimento del Día 3.

## Entradas versionadas

- `data/evaluation/gold_questions.csv`: 20 preguntas gold.
- `data/processed/embedding/embeddings_bge_m3.parquet`: 345 chunks con
  embeddings normalizados BGE-M3.

## Salidas esperadas

- `hyde_documents.csv`: documento hipotético de cada pregunta.
- `retrieval_results_evaluated.csv`: top-5 normal y HyDE con juicio de relevancia.
- `metrics_by_question.csv`: métricas por pregunta y método.
- `metrics_by_method.csv`: comparación agregada.
- `experiment_metadata.json`: modelo, tiempos, tokens y costo estimado.
- `human_audit_sample_blind.xlsx`: muestra sin decisiones del juez.
- `human_audit_sample_key.xlsx`: llave técnica para consolidación posterior.
- `hyde_checkpoint.jsonl` y `judge_checkpoint.jsonl`: reanudación segura.

## Referencia histórica

La evaluación anterior de BGE-M3 cubrió 10 preguntas: Precision@5 = 0,66,
Hit@5 = 1,00 y MRR = 0,7083. Esa medición se conserva como antecedente, pero
la comparación del Día 3 recalcula ambos métodos sobre las mismas 20 preguntas
y con un único protocolo de relevancia.

## Costo

El script registra tokens reales reportados por la API. El costo es una
estimación calculada con las tarifas configuradas al ejecutar; debe indicarse
la fecha y verificar las tarifas vigentes antes de incluirlo en el informe.
