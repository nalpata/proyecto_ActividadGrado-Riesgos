"""Transformaciones públicas y figuras ejecutivas del front del Día 16."""

from __future__ import annotations

from typing import Iterable

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

LEVEL_ORDER = ("CRITICO", "ALTO", "MEDIO", "BAJO")
LEVEL_COLORS = {
    "CRITICO": "#9B1C31",
    "ALTO": "#D97706",
    "MEDIO": "#D4A72C",
    "BAJO": "#167D74",
}


def filter_categories(
    categories: Iterable[dict],
    selected_categories: Iterable[str] | None = None,
    selected_levels: Iterable[str] | None = None,
    minimum_coverage: float = 0.0,
) -> pd.DataFrame:
    """Filtra agregados de categoría sin acceder a señales individuales."""

    frame = pd.DataFrame(categories).copy()
    chosen_categories = list(selected_categories or [])
    chosen_levels = list(selected_levels or [])
    if chosen_categories:
        frame = frame[frame["category"].isin(chosen_categories)]
    if chosen_levels:
        frame = frame[frame["category_level"].isin(chosen_levels)]
    frame = frame[frame["scoring_coverage"] >= minimum_coverage]
    frame = frame[frame["category_score"].notna()]
    return frame.sort_values(["category_score", "scoring_coverage"], ascending=False).reset_index(drop=True)


def build_radar_figure(categories: pd.DataFrame) -> go.Figure:
    """Construye radar PIRD 0–100 con categorías agregadas."""

    figure = go.Figure()
    if not categories.empty:
        labels = categories["category"].tolist()
        values = categories["category_score"].astype(float).tolist()
        figure.add_trace(
            go.Scatterpolar(
                r=values + values[:1],
                theta=labels + labels[:1],
                fill="toself",
                fillcolor="rgba(20,125,146,.20)",
                line={"color": "#147D92", "width": 3},
                marker={"color": "#111827", "size": 7},
                hovertemplate="%{theta}<br>PIRD: %{r:.2f}<extra></extra>",
                name="PIRD por categoría",
            )
        )
    figure.update_layout(
        height=510,
        margin={"l": 60, "r": 60, "t": 35, "b": 35},
        paper_bgcolor="rgba(0,0,0,0)",
        polar={
            "bgcolor": "#FFFFFF",
            "radialaxis": {"range": [0, 100], "tickvals": [20, 40, 60, 80, 100], "gridcolor": "#DDE3EA"},
            "angularaxis": {"gridcolor": "#E5E7EB"},
        },
        showlegend=False,
    )
    return figure


def build_category_priority_figure(categories: pd.DataFrame) -> go.Figure:
    """Ordena categorías por PIRD y conserva el nivel como codificación visual."""

    ordered = categories.sort_values("category_score", ascending=True)
    figure = px.bar(
        ordered,
        x="category_score",
        y="category",
        orientation="h",
        color="category_level",
        color_discrete_map=LEVEL_COLORS,
        labels={"category_score": "PIRD", "category": "Categoría", "category_level": "Nivel"},
        text="category_score",
    )
    figure.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    figure.update_layout(height=max(330, 48 * len(ordered)), xaxis_range=[0, 100], margin={"l": 20, "r": 30, "t": 20, "b": 40})
    return figure


def build_temporal_role_figure(role_counts: dict[str, int]) -> go.Figure:
    """Visualiza el rol temporal agregado sin simular una serie calendario."""

    labels = {
        "APARICION": "Aparición",
        "RECURRENCIA": "Recurrencia",
        "SIN_FECHA_PROPIA": "Sin fecha propia",
        "PENDIENTE_FECHA": "Pendiente de fecha",
    }
    frame = pd.DataFrame(
        [{"Rol temporal": labels.get(key, key.title()), "Señales": value} for key, value in role_counts.items()]
    )
    figure = px.bar(
        frame.sort_values("Señales"), x="Señales", y="Rol temporal", orientation="h",
        color="Señales", color_continuous_scale=["#BFE3E7", "#147D92"], text="Señales",
    )
    figure.update_layout(height=330, coloraxis_showscale=False, margin={"l": 20, "r": 30, "t": 20, "b": 40})
    figure.update_traces(textposition="outside")
    return figure


def build_persistence_figure(persistence_counts: dict[str, int]) -> go.Figure:
    frame = pd.DataFrame(
        [{"Persistencia": f"Nivel {level}", "Señales": count, "level": int(level)} for level, count in persistence_counts.items()]
    ).sort_values("level")
    figure = px.bar(
        frame, x="Persistencia", y="Señales", color="level",
        color_continuous_scale=["#BFE3E7", "#173B63"], text="Señales",
    )
    figure.update_layout(height=330, coloraxis_showscale=False, margin={"l": 20, "r": 20, "t": 20, "b": 40})
    figure.update_traces(textposition="outside")
    return figure
