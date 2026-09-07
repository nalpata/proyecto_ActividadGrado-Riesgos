from pathlib import Path
import sys

import pandas as pd


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.risk.build_operational_catalog import apply_decisions, build_radar, load_human_decisions


def base_rows():
    return pd.DataFrame([
        {
            "risk_id": "R1", "source_doc_id": "D1", "risk_category": "Calidad",
            "validator_corrected_category": "Calidad", "validator_is_valid": 0,
            "validator_evidence_sufficient": 0, "validator_confidence": 0.9,
            "risk_score": 9,
        },
        {
            "risk_id": "R2", "source_doc_id": "D1", "risk_category": "Cronograma",
            "validator_corrected_category": "Cronograma", "validator_is_valid": 1,
            "validator_evidence_sufficient": 1, "validator_confidence": 0.9,
            "risk_score": 6,
        },
    ])


def test_human_decision_overrides_validator():
    human = pd.DataFrame({"risk_id": ["R1"], "human_final": [1]})
    result = apply_decisions(base_rows(), human)
    row = result.set_index("risk_id").loc["R1"]
    assert row["decision_source"] == "human_adjudication"
    assert row["final_is_valid"] == 1
    assert row["operational_inclusion"] == 1


def test_automatic_decision_requires_sufficient_evidence():
    rows = base_rows()
    rows.loc[rows.risk_id == "R2", "validator_evidence_sufficient"] = 0
    result = apply_decisions(rows, pd.DataFrame(columns=["risk_id", "human_final"]))
    assert result.set_index("risk_id").loc["R2", "operational_inclusion"] == 0


def test_radar_uses_only_primary_included_records():
    rows = apply_decisions(base_rows(), pd.DataFrame({"risk_id": ["R1"], "human_final": [1]}))
    rows["operational_is_primary"] = [1, 1]
    radar = build_radar(rows)
    assert set(radar["category"]) == {"Calidad", "Cronograma"}
    assert radar.set_index("category").loc["Calidad", "radar_score"] == 100.0
