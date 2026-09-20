from pathlib import Path

import pandas as pd

from src.frontend.dashboard_data import load_front_snapshot, load_public_timeline_summary
from src.frontend.visualizations import (
    build_category_priority_figure,
    build_persistence_figure,
    build_radar_figure,
    build_temporal_role_figure,
    filter_categories,
)

ROOT = Path(__file__).resolve().parents[1]


def _snapshot():
    return load_front_snapshot(ROOT / "results/day_14/backend_snapshot_v1.json")


def test_category_filters_use_only_public_aggregates():
    filtered = filter_categories(_snapshot()["categories"], ["Cronograma", "Contractual"], ["ALTO"], 0.5)
    assert filtered["category"].tolist() == ["Cronograma"]
    assert set(filtered.columns) == {
        "category", "total_signals", "scored_signals", "scoring_coverage", "category_score", "category_level"
    }


def test_radar_closes_polygon_and_uses_fixed_zero_to_one_hundred_scale():
    frame = pd.DataFrame(_snapshot()["categories"])
    figure = build_radar_figure(frame)
    assert figure.data[0].r[0] == figure.data[0].r[-1]
    assert figure.layout.polar.radialaxis.range == (0, 100)


def test_priority_chart_preserves_category_count():
    frame = pd.DataFrame(_snapshot()["categories"])
    figure = build_category_priority_figure(frame)
    assert sum(len(trace.x) for trace in figure.data) == len(frame)


def test_public_timeline_has_no_item_level_payload():
    summary = load_public_timeline_summary(ROOT / "results/day_10/timeline_summary.json")
    assert summary["signals"] == 649
    assert "not published" in summary["privacy"]
    assert not {"document_name", "document_date", "signal_id", "evidence"}.intersection(summary)


def test_temporal_figures_reconcile_public_counts():
    summary = load_public_timeline_summary(ROOT / "results/day_10/timeline_summary.json")
    role_figure = build_temporal_role_figure(summary["temporal_role_counts"])
    persistence_figure = build_persistence_figure(summary["persistence_level_counts"])
    assert sum(role_figure.data[0].x) == summary["signals"]
    assert sum(persistence_figure.data[0].y) == summary["signals_with_persistence"]


def test_empty_filter_result_is_supported():
    filtered = filter_categories(_snapshot()["categories"], selected_levels=["CRITICO"])
    assert filtered.empty
    assert len(build_radar_figure(filtered).data) == 0
