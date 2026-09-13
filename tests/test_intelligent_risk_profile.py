import pandas as pd

from src.risk.build_intelligent_risk_profile import build_profile, calculate_item_pird, sanitize


def test_unsupported_components_are_null():
    result = sanitize({"severity": 5, "severity_supported": 0, "probability": 4, "probability_supported": 1, "confidence": 0.8}, "I1")
    assert result["severity"] is None
    assert result["probability"] == 4


def test_pird_is_calculated_only_for_complete_items():
    items = pd.DataFrame({"item_id": ["I1", "I2"], "calibrated_evidence_sufficient": [1, 1], "calibrated_confidence": [0.9, 0.8], "calibrated_category": ["Calidad", "Cronograma"]})
    exposure = pd.DataFrame({"item_id": ["I1", "I2"], "severity": [4, None], "probability": [4, 3]})
    timeline = pd.DataFrame({"item_id": ["I1", "I2"], "recurrence_level": [3, 2], "persistence_level": [4, 2], "document_date": ["2024-01-01", "2024-02-01"], "temporal_role": ["APARICION", "APARICION"]})
    result = calculate_item_pird(items, exposure, timeline)
    assert result.loc[0, "pird_status"] == "CALCULADO"
    assert result.loc[1, "pird_status"] == "PENDIENTE_ENRIQUECIMIENTO"


def test_global_profile_uses_categories():
    scored = pd.DataFrame({
        "item_id": ["I1", "I2", "I3", "I4"], "pird_status": ["CALCULADO"] * 4,
        "pird": [20, 40, 60, 80], "pird_level": ["BAJO", "MEDIO", "ALTO", "CRITICO"],
        "calibrated_category": ["A", "A", "B", "B"], "persistence_level": [1, 4, 4, 5],
    })
    categories, profile = build_profile(scored)
    assert len(categories) == 2
    assert profile["signals_scored"] == 4
    assert 0 <= profile["global_pird"] <= 100
