from pathlib import Path
import sys

import pandas as pd


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.retrieval.run_hyde_experiment import calculate_metrics, parse_json


def test_parse_json_removes_code_fence():
    assert parse_json('```json\n{"ok": true}\n```') == {"ok": True}


def test_metrics_are_calculated_by_method_and_question():
    rows = []
    labels = {
        "normal": [0, 1, 0, 0, 0],
        "hyde": [1, 1, 0, 0, 0],
    }
    for method, values in labels.items():
        for rank, relevant in enumerate(values, 1):
            rows.append({
                "method": method, "question_id": "Q1", "categoria": "riesgos",
                "rank": rank, "relevant": relevant,
            })
    _, summary = calculate_metrics(pd.DataFrame(rows))
    summary = summary.set_index("method")
    assert summary.loc["normal", "precision_at_1"] == 0.0
    assert summary.loc["normal", "hit_at_3"] == 1.0
    assert summary.loc["normal", "mrr"] == 0.5
    assert summary.loc["hyde", "precision_at_1"] == 1.0
    assert summary.loc["hyde", "mrr"] == 1.0


def test_hit_at_5_is_zero_when_no_relevant_result():
    data = pd.DataFrame([
        {"method": "normal", "question_id": "Q1", "categoria": "x", "rank": rank, "relevant": 0}
        for rank in range(1, 6)
    ])
    _, summary = calculate_metrics(data)
    assert summary.iloc[0]["hit_at_5"] == 0
    assert summary.iloc[0]["mrr"] == 0
