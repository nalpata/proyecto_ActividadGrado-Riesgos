"""Prueba el comportamiento del PIRD bajo alternativas razonables de pesos."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.risk.pird import PIRDInputs, calculate_pird


SCENARIOS = {
    "proposed": {"severity":0.40, "probability":0.25, "recurrence":0.20, "persistence":0.15},
    "equal": {"severity":0.25, "probability":0.25, "recurrence":0.25, "persistence":0.25},
    "severity_heavy": {"severity":0.55, "probability":0.25, "recurrence":0.10, "persistence":0.10},
    "temporal_heavy": {"severity":0.30, "probability":0.20, "recurrence":0.25, "persistence":0.25},
}

CONTROL_CASES = [
    {"case_id":"C1_LIMITADO", "severity":2, "probability":2, "recurrence":1, "persistence":1, "evidence":4, "confidence":4},
    {"case_id":"C2_MODERADO", "severity":3, "probability":3, "recurrence":3, "persistence":2, "evidence":4, "confidence":4},
    {"case_id":"C3_PERSISTENTE", "severity":3, "probability":4, "recurrence":5, "persistence":5, "evidence":5, "confidence":4},
    {"case_id":"C4_CRITICO", "severity":5, "probability":5, "recurrence":4, "persistence":4, "evidence":5, "confidence":5},
]


def analyze() -> tuple[pd.DataFrame, dict]:
    rows=[]
    for scenario, weights in SCENARIOS.items():
        for case in CONTROL_CASES:
            result=calculate_pird(PIRDInputs(**{k:case[k] for k in PIRDInputs.__annotations__}), exposure_weights=weights)
            rows.append({"weight_scenario":scenario, "case_id":case["case_id"],
                         "pird":result["pird"], "risk_level":result["risk_level"]})
    data=pd.DataFrame(rows)
    pivot=data.pivot(index="case_id",columns="weight_scenario",values="pird")
    spread=(pivot.max(axis=1)-pivot.min(axis=1)).round(2)
    level_counts=data.groupby("case_id").risk_level.nunique()
    summary={
        "weight_scenarios":len(SCENARIOS), "control_cases":len(CONTROL_CASES),
        "maximum_score_spread":float(spread.max()),
        "cases_changing_level":int((level_counts>1).sum()),
        "monotonic_order_preserved":all(
            list(group.sort_values("pird").case_id)==["C1_LIMITADO","C2_MODERADO","C3_PERSISTENTE","C4_CRITICO"]
            for _,group in data.groupby("weight_scenario")
        ),
        "interpretation":"Resultados de diseño sobre casos controlados; no son scores de riesgos reales",
    }
    return data,summary


def run(output_dir:Path)->dict:
    output_dir.mkdir(parents=True,exist_ok=True)
    data,summary=analyze()
    data.to_csv(output_dir/"pird_sensitivity_cases.csv",index=False,encoding="utf-8-sig")
    (output_dir/"pird_sensitivity_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--output-dir",required=True,type=Path);a=p.parse_args()
    print(json.dumps(run(a.output_dir),ensure_ascii=False,indent=2))


if __name__=="__main__":main()
