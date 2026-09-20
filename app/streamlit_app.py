"""Estructura de navegación del front — Día 15."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.frontend.dashboard_data import NAVIGATION, load_front_snapshot  # noqa: E402

st.set_page_config(page_title="Radar de Riesgos Documentales", page_icon="◈", layout="wide", initial_sidebar_state="expanded")
st.markdown(
    """
    <style>
    .stApp { background: #F6F7FA; }
    [data-testid="stSidebar"] { background: #111827; }
    [data-testid="stSidebar"] * { color: #F9FAFB; }
    .hero { padding: 1.3rem 1.5rem; border-radius: 16px; color: white;
            background: linear-gradient(110deg, #111827 0%, #173B63 62%, #147D92 100%); margin-bottom: 1rem; }
    .hero h1 { margin: 0; font-size: 2rem; }
    .hero p { margin: .45rem 0 0; color: #DCE7F2; }
    .notice { padding: .8rem 1rem; border-left: 4px solid #D39A2C;
              border-radius: 8px; background: #FFF8E8; color: #5F461A; }
    .section-card { padding: 1rem; border: 1px solid #E5E7EB; border-radius: 12px;
                    background: white; min-height: 132px; }
    .eyebrow { text-transform: uppercase; letter-spacing: .08em; color: #5B6574;
               font-size: .75rem; font-weight: 700; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def get_snapshot() -> dict:
    return load_front_snapshot(ROOT / "results/day_14/backend_snapshot_v1.json")


snapshot = get_snapshot()
profile = snapshot["profile"]
st.sidebar.markdown("## ◈ Radar de riesgos")
st.sidebar.caption("Vigilancia documental · prototipo académico")
selected_page = st.sidebar.radio("Navegación", NAVIGATION, label_visibility="collapsed")
st.sidebar.divider()
st.sidebar.markdown(f"**Contrato de datos:** `{snapshot['schema_version']}`")
st.sidebar.markdown(f"**Backend:** {snapshot['contract_status']}")
st.sidebar.caption("Solo se cargan resultados agregados y publicables.")

st.markdown(
    f"""<div class="hero"><div class="eyebrow" style="color:#A9DCE5">Perfil inteligente de riesgo</div>
    <h1>{selected_page}</h1><p>Monitoreo ejecutivo con trazabilidad, cobertura visible y privacidad por diseño.</p></div>""",
    unsafe_allow_html=True,
)


def provisional_notice() -> None:
    st.markdown(
        f"""<div class="notice"><strong>Resultado provisional.</strong> El PIRD es un índice relativo de
        priorización, no una probabilidad. Cobertura actual: {profile['scoring_coverage']:.1%}.</div>""",
        unsafe_allow_html=True,
    )


if selected_page == "Resumen ejecutivo":
    provisional_notice()
    st.write("")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("PIRD global", f"{profile['global_pird']:.2f}", profile["global_level"])
    col2.metric("Cobertura", f"{profile['scoring_coverage']:.1%}")
    col3.metric("Señales puntuadas", f"{profile['signals_scored']:,}")
    col4.metric("Pendientes", f"{profile['signals_pending']:,}")
    st.subheader("Lectura ejecutiva")
    left, right = st.columns([1.35, 1])
    with left:
        st.markdown(
            f"""<div class="section-card"><div class="eyebrow">Estado del proyecto</div>
            <h3>{profile['global_level']} · {profile['profile_status']}</h3>
            <p>El perfil consolida {profile['signals_scored']} señales completas de un total de
            {profile['signals_total']}. Las categorías que requieren mayor atención agregada son
            {', '.join(profile['top_categories'])}.</p></div>""", unsafe_allow_html=True)
    with right:
        st.markdown(
            f"""<div class="section-card"><div class="eyebrow">Sensibilidad</div>
            <h3>{profile['sensitivity_global_min']:.2f} — {profile['sensitivity_global_max']:.2f}</h3>
            <p>El nivel global permanece ALTO en los escenarios de pesos aprobados.</p></div>""", unsafe_allow_html=True)

elif selected_page == "Radar de riesgos":
    provisional_notice()
    st.subheader("Perfil agregado por categoría")
    categories = pd.DataFrame(snapshot["categories"])
    st.bar_chart(categories.set_index("category")["category_score"], horizontal=True)
    st.dataframe(categories.rename(columns={"category": "Categoría", "category_score": "PIRD", "category_level": "Nivel", "scoring_coverage": "Cobertura", "scored_signals": "Puntuadas", "total_signals": "Total"}), width="stretch", hide_index=True)
    st.caption("La visualización avanzada, filtros y radar polar corresponden al Día 16.")

elif selected_page == "Timeline":
    st.info("La navegación está habilitada. La evolución temporal y sus filtros se incorporarán en el Día 16.")
    st.subheader("Principio de presentación")
    st.write("El timeline mostrará recurrencia y persistencia sin imputar fechas inválidas o ausentes.")

elif selected_page == "Riesgos priorizados":
    st.info("La navegación está habilitada. La tabla priorizada se integrará en el Día 16.")
    st.write("Las señales individuales permanecerán fuera del snapshot público y se cargarán solo en el entorno privado autorizado.")

elif selected_page == "Perfil del proyecto":
    provisional_notice()
    st.subheader("Distribución del PIRD")
    distribution = pd.DataFrame(snapshot["level_distribution"])
    st.bar_chart(distribution.set_index("pird_level")["signal_count"])
    st.dataframe(distribution, width="stretch", hide_index=True)
    st.subheader("Escenarios de sensibilidad")
    st.dataframe(pd.DataFrame(snapshot["sensitivity"]), width="stretch", hide_index=True)

elif selected_page == "Pregunte a sus documentos":
    st.info("La interfaz conversacional se conectará al pipeline congelado en el Día 17.")
    st.text_input("Escriba una pregunta", disabled=True, placeholder="Ej.: ¿Qué retrasos requieren vigilancia?")
    st.button("Consultar documentos", disabled=True, type="primary")
    st.caption("Las respuestas exigirán evidencia y mostrarán sus fuentes; no se responderá cuando no exista soporte documental.")

else:
    st.subheader("Metodología")
    st.write("Consulta original → BGE-M3 → extracción calibrada → validación determinista → perfil PIRD.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Pruebas aprobadas", "51")
    c2.metric("Contrato backend", snapshot["schema_version"])
    c3.metric("Estado", snapshot["contract_status"])
    st.subheader("Controles vigentes")
    st.markdown("- HyDE y reranking permanecen descartados.\n- No se imputan fechas, severidad ni probabilidad.\n- El Gold Standard humano no cubre severidad/probabilidad 1–5.\n- El front público consume únicamente agregados sin evidencia privada.")

st.divider()
st.caption("Proyecto de maestría · Sistema RAG y Perfil Inteligente de Riesgo · Día 15")
