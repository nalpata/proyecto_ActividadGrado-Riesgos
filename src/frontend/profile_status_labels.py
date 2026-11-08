"""Separa cálculo, cobertura y alcance de validación sin alterar el PIRD."""

import math


def describe_pird_profile(profile: dict, scope: str = "unverified") -> dict:
    total = int(profile.get("signals_total", profile.get("signals_validated", 0)))
    scored = int(profile.get("signals_scored", 0))
    pending = int(profile.get("signals_pending", total - scored))
    if total < 0 or scored < 0 or pending < 0 or scored + pending != total:
        raise ValueError("Los conteos de cobertura del PIRD no concilian")
    value = profile.get("global_pird")
    has_score = value is not None and math.isfinite(float(value)) and scored > 0
    if total == 0:
        calculation = "Sin señales para puntuar"
        coverage_label = "Sin señales"
    elif scored == 0:
        calculation = "PIRD pendiente de componentes"
        coverage_label = "Sin señales puntuadas"
    elif not has_score:
        calculation = "Consolidación del PIRD pendiente"
        coverage_label = "Completa" if scored == total else "Parcial"
    else:
        calculation = "PIRD calculado sobre señales evaluables"
        coverage_label = "Completa en el conjunto disponible" if scored == total else "Parcial"
    validation_labels = {
        "corpus": "Revisión experta muestral del corpus",
        "session": "Sin revisión experta de estas señales de sesión",
        "synthetic": "Datos sintéticos; sin validación del corpus real",
        "unverified": "Validación experta de este perfil no documentada",
    }
    if scope not in validation_labels:
        raise ValueError("Alcance de validación desconocido")
    return {
        "calculation_label": calculation,
        "coverage_label": coverage_label,
        "coverage_text": f"{scored} de {total} señales ({100 * scored / total:.2f} %)" if total else "0 de 0 señales (sin señales disponibles)",
        "signals_pending": pending,
        "validation_label": validation_labels[scope],
        "validation_note": (
            "La revisión del corpus es interna y muestral; no valida todas las señales ni acredita desempeño en proyectos nuevos."
            if scope == "corpus" else
            "La evaluación del corpus histórico no se transfiere automáticamente a las señales de esta sesión."
            if scope == "session" else
            "Los datos sintéticos demuestran el funcionamiento de las vistas; no son resultados de proyectos reales."
            if scope == "synthetic" else
            "No se dispone de evidencia de revisión experta específica para este perfil."
        ),
        "index_note": ("Los puntajes de esta demostración son sintéticos y no representan evaluaciones de proyectos reales."
                       if scope == "synthetic" else
                       "El PIRD es un índice relativo de priorización, no una probabilidad. Severidad y probabilidad se valoran con una rúbrica asistida por IA; los componentes sin sustento permanecen pendientes."),
    }
