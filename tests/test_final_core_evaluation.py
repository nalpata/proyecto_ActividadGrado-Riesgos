import pandas as pd

from src.evaluation.evaluate_final_core import binary_metrics


def test_binary_metrics_prompt_v2():
    actual = [1] * 21 + [0] * 8
    predicted = [1] * 9 + [0] * 12 + [1] * 2 + [0] * 6
    result = binary_metrics(actual, predicted)
    assert result == {"n":29, "tp":9, "tn":6, "fp":2, "fn":12,
                      "precision":0.8182, "recall":0.4286, "f1":0.5625,
                      "accuracy":0.5172, "specificity":0.75}


def test_binary_metrics_validated_configuration():
    actual = [1] * 21 + [0] * 8
    predicted = [1] * 18 + [0] * 3 + [1] * 4 + [0] * 4
    result = binary_metrics(actual, predicted)
    assert result["precision"] == 0.8182
    assert result["recall"] == 0.8571
    assert result["f1"] == 0.8372
    assert result["accuracy"] == 0.7586
