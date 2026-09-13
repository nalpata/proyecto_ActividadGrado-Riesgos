import numpy as np
import pandas as pd

from src.risk.semantic_clustering import analyze, evaluate_k, recurrence_level, semantic_recurrence


def test_recurrence_rubric():
    assert [recurrence_level(x) for x in [0, 1, 2, 4, 7]] == [1, 2, 3, 4, 5]


def test_recurrence_uses_other_documents():
    embeddings = np.array([[1, 0], [0.99, 0.01], [0, 1]], dtype=float)
    counts, levels = semantic_recurrence(embeddings, pd.Series(["D1", "D2", "D3"]), threshold=0.90)
    assert counts.tolist() == [1, 1, 0]
    assert levels.tolist() == [2, 2, 1]


def test_k_selection_and_assignments():
    rng = np.random.default_rng(7)
    embeddings = np.vstack([
        rng.normal([1, 0, 0], 0.03, size=(10, 3)),
        rng.normal([0, 1, 0], 0.03, size=(10, 3)),
        rng.normal([0, 0, 1], 0.03, size=(10, 3)),
    ])
    metrics = evaluate_k(embeddings, range(2, 5))
    assert metrics.selected.sum() >= 1
    items = pd.DataFrame({
        "item_id": [f"I{x}" for x in range(30)],
        "statement": (["retraso cronograma entrega"] * 10 + ["seguridad acceso vulnerabilidad"] * 10 + ["factura pago financiero"] * 10),
        "source_doc_id": [f"D{x % 8}" for x in range(30)],
        "calibrated_category": (["Cronograma"] * 10 + ["Seguridad"] * 10 + ["Financiero"] * 10),
    })
    assignments, clusters, _, summary = analyze(items, embeddings)
    assert len(assignments) == 30
    assert assignments.recurrence_level.between(1, 5).all()
    assert clusters.signal_count.sum() == 30
    assert summary["selected_k"] in {2, 3, 4}


def test_missing_columns_are_rejected():
    try:
        analyze(pd.DataFrame({"item_id": ["I1"]}), np.array([[1.0, 0.0]]))
    except ValueError as error:
        assert "Faltan columnas" in str(error)
    else:
        raise AssertionError("Se esperaba ValueError")
