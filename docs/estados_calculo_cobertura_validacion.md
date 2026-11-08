# Cálculo, cobertura y alcance de validación del PIRD

La etiqueta general «Resultado provisional» mezclaba el estado de implementación con la cobertura del cálculo y su validación. La interfaz separa ahora tres dimensiones:

- Estado de cálculo: calculado sobre señales evaluables, pendiente de componentes, consolidación pendiente o sin señales para puntuar.
- Cobertura: número de señales puntuadas sobre el total disponible, porcentaje y señales pendientes. El denominador permanece intacto.
- Validación: revisión experta muestral del corpus, ausencia de revisión experta de las señales de sesión, datos sintéticos o validación específica no documentada.

Un perfil con puntuación y cobertura inferior al umbral operativo histórico se presenta como calculado sobre las señales evaluables. Su cobertura parcial y los pendientes siguen visibles. Una cobertura del 100 % sobre el conjunto disponible no se transforma en una afirmación de validación completa o representatividad.

La revisión del corpus no se transfiere automáticamente a documentos nuevos o perfiles privados de procedencia distinta. La demostración sintética no presenta sus números como evaluaciones de proyectos reales. El aviso sobre ausencia de ejemplos humanos para la clasificación de una sesión se conserva y describe esa causa concreta.

Los campos internos históricos profile_status, la política de faltantes, los pesos, las puntuaciones y los snapshots publicados no cambian. La nueva capa de presentación lee los conteos existentes y no reevalúa señales ni realiza llamadas LLM. El PIRD sigue siendo un índice relativo; las valoraciones de severidad y probabilidad utilizan una rúbrica asistida por IA.

Este cambio no implica que todas las señales puedan puntuarse o que las limitaciones de validación hayan desaparecido. La recuperación de componentes mediante contexto documental adicional constituye una etapa separada, con procedencia y revisión de aplicabilidad, sin imputación automática.

Las pruebas verifican que la cobertura parcial no oculte un cálculo existente, que una cobertura completa no declare validación completa, que perfiles vacíos no inventen un score y que el alcance de revisión no se atribuya a sesiones nuevas o datos sintéticos. La comprobación de interfaz conserva los valores existentes y expone las tres dimensiones.
