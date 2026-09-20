"""Estructura de navegación del front — Día 15."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.frontend.dashboard_data import (  # noqa: E402
    DEMO_PROJECT,
    NAVIGATION,
    SUPPORTED_DOCUMENT_TYPES,
    load_front_snapshot,
)

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
project_options = [DEMO_PROJECT, "Nuevo proyecto"]
selected_project = st.sidebar.selectbox("Proyecto", project_options)
if selected_project == "Nuevo proyecto":
    project_name = st.sidebar.text_input("Nombre del proyecto", placeholder="Ej.: Contrato de infraestructura")
    active_project = project_name.strip() or "Nuevo proyecto sin nombre"
else:
    active_project = selected_project
st.sidebar.caption(f"Proyecto activo: {active_project}")
st.sidebar.divider()
selected_page = st.sidebar.radio("Navegación", NAVIGATION, label_visibility="collapsed")
st.sidebar.divider()
st.sidebar.markdown(f"**Contrato de datos:** `{snapshot['schema_version']}`")
st.sidebar.markdown(f"**Backend:** {snapshot['contract_status']}")
st.sidebar.caption("Solo se cargan resultados agregados y publicables.")

if selected_page != "Portada":
    st.markdown(
        f"""<div class="hero"><div class="eyebrow" style="color:#A9DCE5">{active_project}</div>
        <h1>{selected_page}</h1><p>Monitoreo ejecutivo con trazabilidad, cobertura visible y privacidad por diseño.</p></div>""",
        unsafe_allow_html=True,
    )


def provisional_notice() -> None:
    st.markdown(
        f"""<div class="notice"><strong>Resultado provisional.</strong> El PIRD es un índice relativo de
        priorización, no una probabilidad. Cobertura actual: {profile['scoring_coverage']:.1%}.</div>""",
        unsafe_allow_html=True,
    )


if selected_page == "Portada":
    st.markdown(
        """<div class="hero" style="padding:2.5rem 2.2rem">
        <div class="eyebrow" style="color:#A9DCE5">Proyecto de Maestría en Inteligencia Artificial</div>
        <h1 style="font-size:2.55rem;line-height:1.12;margin-top:.7rem">
        Sistema inteligente de vigilancia de riesgo documental basado en
        Retrieval-Augmented Generation (RAG) para documentos de aseguramiento técnico
        </h1>
        <p style="font-size:1.08rem;max-width:900px;margin-top:1.2rem">
        Plataforma para organizar documentos técnicos, recuperar evidencia trazable,
        identificar señales que requieren vigilancia y consolidar un perfil inteligente
        de riesgo para apoyar la toma de decisiones.</p></div>""",
        unsafe_allow_html=True,
    )
    st.subheader("¿Qué permite hacer el sistema?")
    c1, c2, c3 = st.columns(3)
    c1.markdown("""<div class="section-card"><div class="eyebrow">Documentos</div><h3>Centralizar</h3><p>Crear proyectos y cargar documentos PDF o DOCX de aseguramiento técnico.</p></div>""", unsafe_allow_html=True)
    c2.markdown("""<div class="section-card"><div class="eyebrow">Inteligencia</div><h3>Vigilar</h3><p>Recuperar evidencia e identificar retrasos, incumplimientos, hallazgos y compromisos.</p></div>""", unsafe_allow_html=True)
    c3.markdown("""<div class="section-card"><div class="eyebrow">Decisión</div><h3>Priorizar</h3><p>Explorar radar, timeline, perfil PIRD y respuestas documentales trazables.</p></div>""", unsafe_allow_html=True)
    st.caption("Seleccione o cree un proyecto en el panel izquierdo para comenzar.")

elif selected_page == "Proyectos y documentos":
    st.subheader("Gestión del proyecto")
    st.write(f"**Proyecto activo:** {active_project}")
    uploaded_files = st.file_uploader(
        "Cargue documentos de aseguramiento técnico",
        type=list(SUPPORTED_DOCUMENT_TYPES),
        accept_multiple_files=True,
        help="Formatos permitidos: PDF y DOCX. En esta fase los archivos permanecen en la sesión y no se publican.",
    )
    if uploaded_files:
        inventory = pd.DataFrame([
            {"Documento": item.name, "Formato": Path(item.name).suffix.upper().lstrip("."), "Tamaño (KB)": round(item.size / 1024, 1), "Estado": "Listo para procesar"}
            for item in uploaded_files
        ])
        st.success(f"{len(uploaded_files)} documento(s) recibido(s) para {active_project}.")
        st.dataframe(inventory, width="stretch", hide_index=True)
        st.info("La extracción, indexación y actualización del perfil se conectarán al pipeline en el Día 18.")
    else:
        st.info("Seleccione uno o varios archivos PDF/DOCX. No se enviarán al repositorio público.")
    st.subheader("Estado del proyecto")
    if active_project == DEMO_PROJECT:
        st.success("Proyecto procesado · 649 señales · contrato de datos 1.0.0")
    else:
        st.warning("Proyecto nuevo · pendiente de carga y procesamiento")

elif selected_page == "Resumen ejecutivo":
    if active_project != DEMO_PROJECT:
        st.warning("Este proyecto todavía no tiene documentos procesados. Cárguelos en Proyectos y documentos.")
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
    if active_project != DEMO_PROJECT:
        st.warning("El radar estará disponible después de procesar los documentos del proyecto.")
    provisional_notice()
    st.subheader("Perfil agregado por categoría")
    categories = pd.DataFrame(snapshot["categories"])
    st.bar_chart(categories.set_index("category")["category_score"], horizontal=True)
    st.dataframe(categories.rename(columns={"category": "Categoría", "category_score": "PIRD", "category_level": "Nivel", "scoring_coverage": "Cobertura", "scored_signals": "Puntuadas", "total_signals": "Total"}), width="stretch", hide_index=True)
    st.caption("Vista preliminar. El radar polar, los filtros y las familias de riesgo corresponden al Día 16.")

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
