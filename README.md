# Sistema inteligente de vigilancia de riesgo documental basado en RAG

Proyecto de grado de **Patricia Patiño**, Magíster en Inteligencia Artificial, Pontificia Universidad Católica de Chile.

El prototipo consulta documentos de aseguramiento técnico e interventoría, identifica señales documentales y construye perfiles de riesgo con evidencia trazable. Su evaluación combina experimentos de recuperación, revisión humana y pruebas de software. **La solución está implementada, pero los resultados no permiten afirmar validación semántica completa ni generalización a proyectos independientes.**

## Aplicación y versión

[Abrir Streamlit](https://proyectoactividadgrado-riesgos-2fkvw9givjkq6qclxdgq9b.streamlit.app/).
La aplicación utiliza la rama `dia-17-asistente-conversacional`; el nombre es histórico. La interfaz presenta las funciones del sistema, sin organizar su metodología por días de desarrollo. `main` conserva la documentación y se sincroniza mediante PR.

Se mantiene el diseño seleccionado: **consulta original + embeddings BGE-M3 + chunking recursivo + similitud matricial, Top-5**. Los filtros de proyecto y documento se aplican antes del ranking. HyDE y reranking se mantienen como experimentos históricos, no como componentes activos. No se incorpora recuperación experimental.

## Datos y resultados publicados

| Indicador | Estado vigente |
| --- | --- |
| Inventario | 50 archivos, 36 documentos únicos, 345 chunks |
| Señales totales | 649 |
| Atribuidas a un proyecto único | 515 |
| Señales con PIRD calculado | 339/515 (65,83 %) |
| Señales atribuidas pendientes | 176 |
| Otras señales sin atribución única | 134 |
| DataR | 267/404 calculadas; PIRD 51,50, ALTO |

La cobertura se calcula sobre las señales atribuidas de forma única, sin retirar las pendientes del denominador. El snapshot histórico de septiembre (372/649; 57,32 %; PIRD 52,16) se conserva como antecedente y no se presenta como el resultado vigente. El PIRD es un índice metodológico de vigilancia, no una probabilidad estadística de incumplimiento.

El detalle público se carga automáticamente desde `data/evaluation/risk_details/signals_published.csv`, verificado con [su manifiesto](config/risk_detail_manifest.json). No se exige carga manual de CSV. Los documentos adicionales descartados no amplían la línea base. Las dos actas reservadas se utilizaron en una sesión de evaluación separada; sus originales y trazas privadas no se publican aquí.

## Trabajo del 7 y 8 de noviembre de 2026

Fechas en **America/Bogota**. El [registro de PR fusionados](results/closure_20261108/merged_work_log.json) contiene horas UTC, hora local, commit y enlace de cada cambio.

| Fecha | Trabajo y evidencia |
| --- | --- |
| 7 de noviembre | PR20–31: consulta de documentos de sesión, aislamiento entre proyectos, diagnóstico de errores, compatibilidad del recuperador, caché del modelo, resolución de proyectos, catálogo, recálculo, exposición temporal, estados metodológicos y enriquecimiento con contexto. |
| 8 de noviembre | PR32–37: incorporación de siete revisiones expertas, avisos de alcance, interfaz y sincronización de documentación. PR38: detalle público automático. PR39: procedencia de componentes. PR40: inventario del proyecto nuevo. |
| 8 de noviembre | PR41: inventario de sesión, diagnóstico, progreso y rúbricas. PR42: alcance documental con filtro por fecha. Evaluación posterior conserva los errores observados; no se declaran solucionados por pasar pruebas de software. |
| Actualización de cierre | Control conservador de cierres no respaldados, notebooks de verificación y reproducción, pruebas adicionales y actualización de README y matriz de objetivos. |

Las siete revisiones expertas completaron 332→339 señales valoradas. Esto no equivale a revisión humana de las 339 valoraciones ni de todas las señales.

## Flujo implementado

1. Inventario, extracción PDF/DOCX, chunking recursivo y embeddings BGE-M3.
2. Recuperación por similitud sobre matriz normalizada; la ruta vigente usa Parquet y búsqueda matricial. No utiliza un servicio Chroma/Qdrant activo.
3. Respuestas con referencias a fuentes recuperadas. La puerta de citas comprueba referencias existentes, no equivalencia semántica completa.
4. Extracción y validación de señales, resolución de proyecto y componentes PIRD con política estricta de faltantes.
5. Perfil, radar, detalle, timeline, inventario y conversación filtrados por proyecto. Un proyecto nuevo no hereda los indicadores de la línea base.

La implementación histórica de LangGraph tiene cuatro nodos; no se presenta como si toda ruta de consulta y procesamiento de sesión pasara por el mismo grafo. El clustering es exploratorio y la recurrencia documental no constituye validación general de relaciones semánticas.

### Control del cierre de exposición

Una solicitud emitida o un compromiso registrado no acreditan su cumplimiento. Si una propuesta afirma cierre y no existe cierre afirmativo en la evidencia verificada de esa señal, sus componentes de severidad y probabilidad quedan pendientes. Se conservan los valores y la justificación originales en auditoría, se mantiene el denominador y se concilian los agregados. No se reemplaza la valoración del modelo por 5/5 para hacerla coincidir con el experto.

El control es conservador y basado en expresiones literales; no garantiza que toda afirmación semántica quede correctamente interpretada. No modifica perfiles históricos ni constituye una nueva ejecución del modelo.

## Evaluación y límites

La revisión humana histórica incluyó 40 casos, con distintos denominadores según evaluabilidad:

| Criterio | n | Resultado |
| --- | ---: | --- |
| Vigilancia | 34 | Exactitud 0,8529; precisión 0,9259; recall 0,8929; F1 0,9091 |
| Evidencia suficiente | 38 | Exactitud 0,9211; todos los casos evaluables fueron positivos según experto, sin estimación de especificidad |
| Tipo | 40 | Exactitud 0,9250 |
| Categoría | 40 | Exactitud 0,9000 |
| Proyecto | 31 | Exactitud 0,8387; en 24 atribuciones únicas evaluables hubo 24 coincidencias |
| Severidad | 15 | MAE 0,0667; acuerdo exacto 0,9333 |
| Probabilidad | 18 | MAE 0,3333; acuerdo exacto 0,7778 |

Los denominadores no se extrapolan al corpus completo. La evaluación experta de utilidad de la aplicación no se realizó por acuerdo con el revisor.

La comprobación posterior usó dos actas fuera de los experimentos anteriores, del mismo entorno de proyectos. El experto OC confirmó referencias el 8 de noviembre. Después de los ajustes PR41–42:

| Caso | Observación |
| --- | --- |
| 1 y 2 | Respuestas confirmadas correctas |
| 3 | Sigue sin resolver: la consulta omite/contradice una señal relevante; la extracción encuentra una alerta, pero la valora 3/4 frente a 5/5 del experto |
| 4 | No se publica una penalidad sin evidencia; el bloqueo de una salida sin cita no prueba por sí solo razonamiento correcto |
| 5 | Persiste una abstención indebida sobre la atribución a NSGA |

La última sesión antes del control de cierre tuvo 88 extracciones, 39 aceptadas, 27 calculadas y 12 pendientes (69,23 %); su agregado 32,96 mezcla proyectos y no se atribuye como PIRD de uno solo. Una solicitud distinta recibió 2/1 con una justificación de cierre no respaldada: el control añadido la deja pendiente, conservando la propuesta. [Registro agregado de evaluación](results/closure_20261108/evaluation_summary.json).

En la comprobación de Streamlit posterior al control, la misma sesión conservó 39 señales y pasó a 19 valoradas y 20 pendientes (48,72 %): ocho propuestas requieren revisión de cierre. La solicitud quedó sin S/P ni PIRD; la alerta principal conservó 3/4. No fue una ejecución nueva del LLM ni un cambio de la línea base.

Estos casos ya conocidos sirven para regresión, no para afirmar un test independiente. Las pruebas de software no sustituyen la revisión experta ni resuelven automáticamente los casos 3 y 5.

## Notebooks, pruebas y reproducción

- [27 — Perfil inteligente](notebooks/27_perfil_inteligente_dia_11_colab.ipynb) y [29 — Automatización](notebooks/29_automatizacion_end_to_end_dia_13_colab.ipynb): antecedentes históricos, con advertencias de versión. No se ejecutaron nuevamente sus llamadas LLM.
- [30 — Verificación del cierre](notebooks/30_verificacion_cierre_noviembre_2026.ipynb): integridad de la línea base, control fabricado de cierre y lectura de observaciones históricas. Sin API.
- [31 — Reproducción del enriquecimiento](notebooks/31_reproduccion_enriquecimiento_contexto.ipynb): verifica 176 entradas pendientes; cálculo API desactivado por defecto, resultados separados y revisión antes de publicar.
- [Pruebas del control de cierre](tests/test_session_exposure_grounding.py) y [pruebas de notebooks](tests/test_closure_notebooks.py).
- [Evidencia de ejecución de software](results/closure_20261108/software_validation.json): comando, entorno, conteo real, hashes y fecha. Los outputs de los notebooks 30–31 provienen de ejecución secuencial de Python ordinario, sin kernel IPython.

```bash
pip install -r requirements-test.txt
python -m pytest -q
python -m src.audit.notebook_runner --notebook notebooks/30_verificacion_cierre_noviembre_2026.ipynb --output /tmp/verificacion_cierre.ipynb
python -m src.audit.notebook_runner --notebook notebooks/31_reproduccion_enriquecimiento_contexto.ipynb --output /tmp/verificacion_enriquecimiento.ipynb
streamlit run app/streamlit_app.py
```

Para generación real se requieren las dependencias de `requirements.txt` y la configuración de credenciales en el entorno de ejecución. Nunca incluir claves en notebooks, commits o salidas.

[Estado frente a objetivos](docs/cierre_noviembre_2026.md) · [Detalle de actualización](docs/actualizacion_20261107_08.md).
