"""Revisión conservadora de cierres propuestos en análisis de sesión.

No modifica artefactos históricos ni reemplaza niveles por etiquetas expertas.
La literalidad y los marcadores de cierre son controles necesarios, no una
garantía de equivalencia semántica completa entre una cita y una valoración.
"""
from copy import deepcopy
import re
import unicodedata

import pandas as pd

from src.risk.build_intelligent_risk_profile import build_profile

VERSION = "SESSION-CLOSURE-GROUNDING-1"
PENDING_MESSAGE = (
    "Valoración pendiente: la propuesta de cierre no está respaldada por un cierre "
    "afirmativo en la evidencia de esta señal. Requiere revisión documental."
)
CLOSURE = re.compile(
    r"\b(?:cerrad[oa]s?|cerro|cerraron|cierra|cierran|resuelt[oa]s?|resolvio|"
    r"subsanad[oa]s?|finalizad[oa]s?|completad[oa]s?|concluid[oa]s?|cumplid[oa]s?)\b"
)


def affirmed_closure(text: str) -> bool:
    value = ''.join(c for c in unicodedata.normalize('NFKD', str(text))
                    if not unicodedata.combining(c)).casefold()
    for clause in re.split(r"[.;\n!?]|\bpero\b|\bsin embargo\b", value):
        for match in CLOSURE.finditer(clause):
            prefix = clause[max(0, match.start() - 70):match.start()]
            if not re.search(r"\b(?:no|sin|pendiente|falta)\b", prefix):
                return True
    return False


def unsupported_closure(row: dict) -> bool:
    proposed = affirmed_closure(row.get("exposure_justification", "")) or str(
        row.get("exposure_status", "")).upper() == "CERRADA"
    return proposed and not (
        row.get("evidence_verified") == 1 and
        affirmed_closure(row.get("evidence_quote", ""))
    )


def review_session_analysis(analysis: dict) -> dict:
    """Pone propuestas no sustentadas pendientes y concilia todos los agregados."""
    if analysis.get("exposure_grounding_audit", {}).get("version") == VERSION:
        return analysis
    records = analysis.get("private", {}).get("scored_signals", [])
    if not records:
        return analysis
    flagged = [index for index, row in enumerate(records) if unsupported_closure(row)]
    if not flagged:
        return analysis
    if int(analysis["summary"]["signals_validated"]) != len(records):
        raise ValueError("El catálogo de sesión no concilia con el denominador de señales aceptadas")
    result = deepcopy(analysis)
    rows = result["private"]["scored_signals"]
    for index in flagged:
        row = rows[index]
        row["exposure_grounding_original"] = {key: deepcopy(row.get(key)) for key in (
            "severity", "probability", "pird", "pird_level", "pird_status",
            "exposure_justification", "exposure_status",
        )}
        row.update({
            "severity": None, "probability": None, "severity_supported": 0,
            "probability_supported": 0, "pird": None, "pird_level": None,
            "exposure_index": None, "reliability_index": None,
            "pird_status": "PENDIENTE_ENRIQUECIMIENTO",
            "pird_missing_components": ",".join(dict.fromkeys([
                *filter(None, str(row.get("pird_missing_components") or "").split(",")),
                "severity", "probability",
            ])),
            "exposure_review_required": True,
            "exposure_status": "INDETERMINADA",
            "exposure_grounding_issue": "CIERRE_NO_RESPALDADO_EN_LA_EVIDENCIA_DE_LA_SENAL",
            "exposure_justification": PENDING_MESSAGE,
        })
    frame = pd.DataFrame(rows)
    categories, profile = build_profile(frame)
    summary = result["summary"]
    original_summary = deepcopy(summary)
    calculated = int(frame.pird_status.eq("CALCULADO").sum())
    summary.update({
        "signals_scored": calculated, "signals_pending": len(rows) - calculated,
        "scoring_coverage": calculated / len(rows),
        "global_pird": profile.get("global_pird"), "global_level": profile.get("global_level"),
        "profile_status": profile.get("profile_status", "PENDIENTE_COMPONENTES_PIRD"),
    })
    result["categories"] = [] if categories.empty else [{
        "category": row.calibrated_category,
        "category_score": float(row.category_score) if pd.notna(row.category_score) else None,
        "category_level": row.category_level, "scoring_coverage": float(row.scoring_coverage),
        "scored_signals": int(row.scored_signals), "total_signals": int(row.total_signals),
    } for row in categories.itertuples()]
    result["exposure_grounding_audit"] = {
        "version": VERSION, "signals_flagged": len(flagged),
        "item_ids": [rows[index]["item_id"] for index in flagged],
        "original_summary": original_summary,
        "policy": "Mantener denominador; no imputar ni usar etiquetas expertas; conservar propuestas originales.",
    }
    return result
