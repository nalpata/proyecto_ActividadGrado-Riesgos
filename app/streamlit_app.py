"""Aplicación integrada con discriminación segura por proyecto — Día 18A."""

from __future__ import annotations

import sys
import os
import json
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
    load_public_timeline_summary,
    project_by_name,
    validate_project_scope_summary,
)
from src.frontend.visualizations import (  # noqa: E402
    LEVEL_ORDER,
    build_category_priority_figure,
    build_persistence_figure,
    build_radar_figure,
    build_temporal_role_figure,
    filter_categories,
)
from src.frontend.chat_service import ConversationalRagService, ProjectScopedRetriever, append_history  # noqa: E402
from src.pipeline.end_to_end import BgeM3Retriever, OpenAIRagAnswerer  # noqa: E402
from src.risk.project_resolution import assign_chunks, validate_project_catalog  # noqa: E402

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


@st.cache_data
def get_timeline_summary() -> dict:
    return load_public_timeline_summary(ROOT / "results/day_10/timeline_summary.json")


@st.cache_data
def get_project_scope() -> dict | None:
    """Carga agregados por proyecto solo desde configuración privada del servidor."""

    try:
        raw = st.secrets.get("PROJECT_SCOPE_JSON") or os.getenv("PROJECT_SCOPE_JSON")
    except Exception:
        raw = os.getenv("PROJECT_SCOPE_JSON")
    if not raw:
        return None
    payload = json.loads(raw) if isinstance(raw, str) else dict(raw)
    return validate_project_scope_summary(payload)


@st.cache_data
def get_private_project_catalog() -> dict:
    try:
        raw = st.secrets.get("PROJECT_CATALOG_JSON") or os.getenv("PROJECT_CATALOG_JSON")
    except Exception:
        raw = os.getenv("PROJECT_CATALOG_JSON")
    if not raw:
        raise RuntimeError("El catálogo privado de proyectos no está configurado")
    payload = json.loads(raw) if isinstance(raw, str) else dict(raw)
    return validate_project_catalog(payload)


@st.cache_data
def get_project_chunk_ids() -> dict[str, set[str]]:
    catalog = get_private_project_catalog()
    chunks = pd.read_csv(ROOT / "data/processed/chunks/chunks_recursive.csv")
    assigned = assign_chunks(chunks, catalog)
    mapping = {item["project_id"]: set() for item in catalog["projects"]}
    for row in assigned.itertuples(index=False):
        if row.project_assignment_status not in {"ASSIGNED_CHUNK_EXPLICIT", "ASSIGNED_FILENAME_EXPLICIT"}:
            continue
        project_ids = [value for value in str(row.project_ids).split("|") if value]
        if len(project_ids) == 1:
            mapping[project_ids[0]].add(str(row.chunk_id))
    return mapping


def get_openai_api_key() -> str | None:
    """Obtiene la clave del servidor; nunca desde un campo visible del front."""

    try:
        return st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    except Exception:
        return os.getenv("OPENAI_API_KEY")


@st.cache_resource
def get_chat_service(api_key: str, project_id: str = "", project_name: str = "") -> ConversationalRagService:
    from openai import OpenAI

    retrieval_depth = 50 if project_id else 5
    retriever = BgeM3Retriever(ROOT / "data/processed/embedding/embeddings_bge_m3.parquet", top_k=retrieval_depth)
    if project_id:
        retriever = ProjectScopedRetriever(
            retriever=retriever,
            project_name=project_name,
            allowed_chunk_ids=get_project_chunk_ids().get(project_id, set()),
            top_k=5,
        )
    answerer = OpenAIRagAnswerer(model="gpt-4o-mini", client=OpenAI(api_key=api_key))
    return ConversationalRagService(retriever=retriever, answerer=answerer)


snapshot = get_snapshot()
project_scope = get_project_scope()
st.sidebar.markdown("## ◈ Radar de riesgos")
st.sidebar.caption("Vigilancia documental · prototipo académico")
private_project_names = [item["display_name"] for item in project_scope["catalog"]] if project_scope else []
project_options = [DEMO_PROJECT, *private_project_names, "Nuevo proyecto"]
selected_project = st.sidebar.selectbox("Proyecto", project_options)
if selected_project == "Nuevo proyecto":
    project_name = st.sidebar.text_input("Nombre del proyecto", placeholder="Ej.: Contrato de infraestructura")
    active_project = project_name.strip() or "Nuevo proyecto sin nombre"
else:
    active_project = selected_project
selected_project_view = project_by_name(project_scope, selected_project) if project_scope else None
active_project_id = selected_project_view["project_id"] if selected_project_view else ""
is_processed_project = selected_project != "Nuevo proyecto"
if selected_project_view:
    profile = selected_project_view["profile"]
    view_categories = selected_project_view["categories"]
    view_distribution = selected_project_view["level_distribution"]
    view_timeline = selected_project_view["timeline"]
else:
    profile = snapshot["profile"]
    view_categories = snapshot["categories"]
    view_distribution = snapshot["level_distribution"]
    view_timeline = get_timeline_summary()
st.sidebar.caption(f"Proyecto activo: {active_project}")
if selected_project_view:
    st.sidebar.caption(f"{profile['signals_total']} señales asignadas · cobertura PIRD {profile['scoring_coverage']:.1%}")
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
    if is_processed_project:
        st.success(f"Proyecto procesado · {profile['signals_total']} señales · contrato de datos 1.0.0")
    else:
        st.warning("Proyecto nuevo · pendiente de carga y procesamiento")

elif selected_page == "Resumen ejecutivo":
    if not is_processed_project:
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
        if selected_project_view:
            st.markdown(
                f"""<div class="section-card"><div class="eyebrow">Alcance por proyecto</div>
                <h3>{selected_project_view['display_name']}</h3>
                <p>Perfil calculado únicamente con señales asignadas explícitamente a este proyecto. Los casos ambiguos permanecen pendientes.</p></div>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""<div class="section-card"><div class="eyebrow">Sensibilidad</div>
                <h3>{profile['sensitivity_global_min']:.2f} — {profile['sensitivity_global_max']:.2f}</h3>
                <p>El nivel global permanece ALTO en los escenarios de pesos aprobados.</p></div>""", unsafe_allow_html=True)

elif selected_page == "Radar de riesgos":
    if not is_processed_project:
        st.warning("El radar estará disponible después de procesar los documentos del proyecto.")
    provisional_notice()
    st.subheader("Radar PIRD por categoría")
    categories = pd.DataFrame(view_categories)
    with st.container(border=True):
        f1, f2, f3 = st.columns([1.4, 1, 1])
        chosen_categories = f1.multiselect("Categorías", categories["category"].tolist(), default=categories["category"].tolist())
        available_levels = [level for level in LEVEL_ORDER if level in categories["category_level"].unique()]
        chosen_levels = f2.multiselect("Niveles", available_levels, default=available_levels)
        minimum_coverage = f3.slider("Cobertura mínima", 0, 100, 0, 5, format="%d %%") / 100
    filtered = filter_categories(view_categories, chosen_categories, chosen_levels, minimum_coverage)
    if filtered.empty:
        st.warning("No existen categorías que cumplan los filtros seleccionados.")
    else:
        left, right = st.columns([1.45, 1])
        with left:
            st.plotly_chart(build_radar_figure(filtered), width="stretch", key="category_radar")
        with right:
            st.markdown("#### Lectura del radar")
            st.metric("Categorías visibles", len(filtered))
            st.metric("Mayor PIRD", f"{filtered.iloc[0]['category_score']:.2f}", filtered.iloc[0]["category"])
            low_coverage = int((filtered["scoring_coverage"] < 0.5).sum())
            st.metric("Cobertura inferior a 50 %", low_coverage)
            st.caption("El eje radial representa PIRD de 0 a 100. Una mayor extensión indica mayor prioridad relativa, no una probabilidad de ocurrencia.")
        display = filtered.copy()
        display["scoring_coverage"] = display["scoring_coverage"].map(lambda value: f"{value:.1%}")
        st.dataframe(display.rename(columns={"category": "Categoría", "category_score": "PIRD", "category_level": "Nivel", "scoring_coverage": "Cobertura", "scored_signals": "Puntuadas", "total_signals": "Total"}), width="stretch", hide_index=True)

elif selected_page == "Timeline":
    if not is_processed_project:
        st.warning("El análisis temporal estará disponible después de procesar los documentos del proyecto.")
    temporal = view_timeline
    st.subheader("Continuidad y persistencia documental")
    st.info("La vista pública presenta agregados temporales. No simula una serie cronológica ni imputa fechas ausentes.")
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("Documentos fuente", temporal["source_documents"])
    t2.metric("Señales con fecha", temporal["signals_with_document_date"])
    t3.metric("Señales recurrentes", temporal["temporal_role_counts"].get("RECURRENCIA", 0))
    t4.metric("Persistencia nivel 5", temporal["persistence_level_counts"].get("5", 0))
    left, right = st.columns(2)
    with left:
        st.markdown("#### Rol temporal")
        st.plotly_chart(build_temporal_role_figure(temporal["temporal_role_counts"]), width="stretch")
    with right:
        st.markdown("#### Nivel de persistencia")
        st.plotly_chart(build_persistence_figure(temporal["persistence_level_counts"]), width="stretch")
    st.caption("Los nombres de archivo, fechas por documento y señales individuales no forman parte del front público.")

elif selected_page == "Riesgos priorizados":
    if not is_processed_project:
        st.warning("La priorización estará disponible después de procesar los documentos del proyecto.")
    provisional_notice()
    st.subheader("Priorización agregada")
    categories = pd.DataFrame(view_categories)
    selected_priority_levels = st.multiselect(
        "Nivel de riesgo", [level for level in LEVEL_ORDER if level in categories["category_level"].unique()],
        default=[level for level in LEVEL_ORDER if level in categories["category_level"].unique()], key="priority_levels",
    )
    prioritized = filter_categories(view_categories, selected_levels=selected_priority_levels)
    st.plotly_chart(build_category_priority_figure(prioritized), width="stretch")
    table = prioritized[["category", "category_score", "category_level", "scoring_coverage", "scored_signals", "total_signals"]].copy()
    table["scoring_coverage"] = table["scoring_coverage"].map(lambda value: f"{value:.1%}")
    st.dataframe(table.rename(columns={"category": "Categoría", "category_score": "PIRD", "category_level": "Nivel", "scoring_coverage": "Cobertura", "scored_signals": "Puntuadas", "total_signals": "Total"}), width="stretch", hide_index=True)
    st.caption("Priorización por categoría. Las señales y evidencias individuales permanecen en el entorno privado autorizado.")

elif selected_page == "Perfil del proyecto":
    provisional_notice()
    st.subheader("Distribución del PIRD")
    distribution = pd.DataFrame(view_distribution)
    st.bar_chart(distribution.set_index("pird_level")["signal_count"])
    st.dataframe(distribution, width="stretch", hide_index=True)
    st.subheader("Escenarios de sensibilidad")
    if selected_project_view:
        st.info("La sensibilidad de pesos continúa reportándose para la vista consolidada; el PIRD por proyecto conserva los pesos aprobados.")
    else:
        st.dataframe(pd.DataFrame(snapshot["sensitivity"]), width="stretch", hide_index=True)

elif selected_page == "Pregunte a sus documentos":
    st.subheader("Asistente documental")
    st.write("Consulte el corpus del proyecto activo. Las respuestas se generan únicamente con evidencia recuperada mediante BGE-M3.")
    if not is_processed_project:
        st.warning("Este proyecto aún no tiene un índice documental. Cargue y procese sus documentos para habilitar las consultas.")
    elif selected_project_view:
        st.info(f"La recuperación está limitada a evidencia asignada explícitamente al proyecto {selected_project_view['display_name']}.")
    api_key = get_openai_api_key()
    if not api_key:
        st.warning("El asistente está listo, pero la clave del modelo aún no está configurada como secreto del servidor.")
        st.caption("Configure `OPENAI_API_KEY` en Streamlit Secrets. La clave no debe escribirse en la aplicación ni publicarse en GitHub.")
    st.markdown("**Preguntas sugeridas**")
    st.caption("• ¿Qué retrasos requieren vigilancia?  ·  ¿Qué incumplimientos aparecen en los documentos?  ·  ¿Qué compromisos continúan pendientes?")

    history_key = f"chat_history::{active_project}"
    if history_key not in st.session_state:
        st.session_state[history_key] = []
    for exchange in st.session_state[history_key]:
        with st.chat_message("user"):
            st.write(exchange["question"])
        with st.chat_message("assistant"):
            st.write(exchange["answer"])
            if exchange["sources"]:
                with st.expander(f"Fuentes utilizadas ({len(exchange['sources'])})"):
                    for source in exchange["sources"]:
                        page = source.get("page") if source.get("page") is not None else "N/D"
                        score = source.get("score")
                        score_label = f" · similitud {score:.3f}" if isinstance(score, (int, float)) else ""
                        st.markdown(f"**[{source['rank']}]** {source.get('filename') or 'Documento'} · página {page}{score_label}")
            elif exchange.get("response_status") != "ERROR":
                st.caption("No se encontraron fuentes suficientes para sustentar una respuesta.")

    question = st.chat_input(
        "Escriba una pregunta sobre los documentos",
        disabled=not api_key or not is_processed_project,
    )
    if question:
        with st.spinner("Recuperando evidencia y preparando la respuesta…"):
            exchange = get_chat_service(api_key, active_project_id, active_project).ask(question)
        st.session_state[history_key] = append_history(st.session_state[history_key], exchange)
        st.rerun()
    st.caption("El asistente no usa conocimiento externo. Verifique siempre la respuesta en las fuentes citadas.")

else:
    st.subheader("Metodología")
    st.write("Consulta original → BGE-M3 → extracción calibrada → validación determinista → perfil PIRD.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Pruebas aprobadas", "74")
    c2.metric("Contrato backend", snapshot["schema_version"])
    c3.metric("Estado", snapshot["contract_status"])
    st.subheader("Controles vigentes")
    st.markdown("- HyDE y reranking permanecen descartados.\n- No se imputan fechas, severidad ni probabilidad.\n- El Gold Standard humano no cubre severidad/probabilidad 1–5.\n- El front público consume únicamente agregados sin evidencia privada.")

st.divider()
st.caption("Proyecto de maestría · Sistema RAG y Perfil Inteligente de Riesgo · Día 18A")
