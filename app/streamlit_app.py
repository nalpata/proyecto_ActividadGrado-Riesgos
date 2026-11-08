"""Aplicación de consulta y vigilancia documental por proyecto."""

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
from src.frontend.session_project_view import build_session_project_view  # noqa: E402
from src.frontend.document_timeline import build_document_timeline  # noqa: E402
from src.frontend.risk_details import load_corpus_risk_details, select_project_risk_details, filter_risk_details
from src.frontend.profile_status_labels import describe_pird_profile  # noqa: E402
from src.frontend.visualizations import (  # noqa: E402
    LEVEL_ORDER,
    build_category_priority_figure,
    build_persistence_figure,
    build_radar_figure,
    build_temporal_role_figure,
    filter_categories,
)
from src.frontend.chat_service import FinalPipelineChatService, ProjectScopedRetriever  # noqa: E402
from src.pipeline.end_to_end import BgeM3Retriever, EndToEndPipeline, OpenAIRagAnswerer  # noqa: E402
from src.pipeline.project_ingestion import ingest_project_documents  # noqa: E402
from src.retrieval.session_retriever import SessionRetriever  # noqa: E402
from src.retrieval.project_retriever import ProjectBgeM3Retriever  # noqa: E402
from src.frontend.runtime_chat import RuntimeChatService, append_runtime_history as append_history  # noqa: E402
from src.frontend.chat_service import ConversationalRagService  # noqa: E402
from src.pipeline.project_risk_processing import process_project_risks  # noqa: E402
from src.risk.project_resolution import assign_chunks, validate_project_catalog  # noqa: E402
from src.risk.corpus_project_catalog import load_catalog, reconcile_chunks, load_recomputed_scope  # noqa: E402

DEMONSTRATION_QUESTIONS = (
    "¿Qué retrasos requieren vigilancia?",
    "¿Qué incumplimientos aparecen en los documentos?",
    "¿Qué compromisos continúan pendientes?",
)

st.set_page_config(page_title="Radar de Riesgos Documentales", page_icon="◈", layout="wide", initial_sidebar_state="expanded")
st.markdown(
    """
    <style>
    .stApp { background: #F6F7FA; }
    [data-testid="stSidebar"] { background: #111827; }
    [data-testid="stSidebar"] * { color: #F9FAFB; }
    [data-testid="stSidebar"] [data-baseweb="select"] > div { background: #F9FAFB; }
    [data-testid="stSidebar"] [data-baseweb="select"] * { color: #111827 !important; }
    [data-testid="stSidebar"] input[role="combobox"] {
        color: #111827 !important; -webkit-text-fill-color: #111827 !important; caret-color: #111827;
    }
    [data-testid="stSidebar"] .stSelectbox button[aria-label="Open"],
    [data-testid="stSidebar"] .stSelectbox button[aria-label="Open"] * {
        color: #111827 !important; fill: #111827 !important;
    }
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
def get_academic_demo_scope() -> dict:
    """Carga datos fabricados y publicables para demostrar el flujo multiproyecto."""

    path = ROOT / "results/day_18/academic_project_demo.json"
    return validate_project_scope_summary(json.loads(path.read_text(encoding="utf-8")))


@st.cache_data
def get_private_project_catalog() -> dict:
    try:
        raw = st.secrets.get("PROJECT_CATALOG_JSON") or os.getenv("PROJECT_CATALOG_JSON")
    except Exception:
        raw = os.getenv("PROJECT_CATALOG_JSON")
    return load_catalog(ROOT / "config/project_catalog.json", raw)


def get_optional_project_catalog() -> dict | None:
    try:
        return get_private_project_catalog()
    except RuntimeError:
        return None


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


def get_calibration_examples() -> str | list | None:
    """Lee ejemplos humanos solo desde la configuración privada del servidor."""

    try:
        return st.secrets.get("CALIBRATION_EXAMPLES_JSON") or os.getenv("CALIBRATION_EXAMPLES_JSON")
    except Exception:
        return os.getenv("CALIBRATION_EXAMPLES_JSON")


@st.cache_resource
def get_embedding_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("BAAI/bge-m3")


@st.cache_resource(max_entries=8)
def get_chat_service(api_key: str, project_id: str = "", project_name: str = "") -> FinalPipelineChatService:
    from openai import OpenAI

    retriever = ProjectBgeM3Retriever(
        ROOT / "data/processed/embedding/embeddings_bge_m3.parquet",
        top_k=5,
        encoder=get_embedding_model(),
        allowed_chunk_ids=get_project_chunk_ids().get(project_id, set()) if project_id else None,
    )
    answerer = OpenAIRagAnswerer(model="gpt-4o-mini", client=OpenAI(api_key=api_key))
    pipeline = EndToEndPipeline(
        retriever=retriever,
        extractor=lambda chunks: [],
        profiler=lambda signals: {},
        answerer=answerer,
    )
    return RuntimeChatService(pipeline=pipeline)


snapshot = get_snapshot()
private_project_scope = get_project_scope()
corpus_catalog = get_private_project_catalog()
academic_project_scope = get_academic_demo_scope()
st.sidebar.markdown("## ◈ Radar de riesgos")
st.sidebar.caption("Vigilancia documental · prototipo académico")
scope_options = ["Corpus por proyecto", "Demostración académica sintética"]
if private_project_scope:
    scope_options.append("Entorno privado por proyecto")
selected_scope = st.sidebar.radio("1. Seleccione el modo de datos", scope_options)
is_academic_demo = selected_scope == "Demostración académica sintética"
if is_academic_demo:
    project_scope = academic_project_scope
elif selected_scope == "Entorno privado por proyecto":
    project_scope = private_project_scope
elif selected_scope == "Corpus por proyecto":
    project_scope = load_recomputed_scope(ROOT / "results/day_23/project_scope_context_reviewed.json", corpus_catalog)
else:
    project_scope = None
is_corpus_project = selected_scope == "Corpus por proyecto"
scoped_project_names = ([item["display_name"] for item in corpus_catalog["projects"]] if is_corpus_project
                        else [item["display_name"] for item in project_scope["catalog"]] if project_scope else [])
project_options = [*scoped_project_names, "Nuevo proyecto"] if scoped_project_names else [DEMO_PROJECT, "Nuevo proyecto"]
project_selector_label = "2. Seleccione el proyecto sintético" if is_academic_demo else "2. Seleccione el proyecto"
selected_project = st.sidebar.selectbox(project_selector_label, project_options, key=f"active_project::{selected_scope}")
st.sidebar.caption("El proyecto seleccionado filtra todas las vistas y las consultas del asistente.")
if is_academic_demo:
    st.sidebar.caption("Abra esta lista para cambiar entre Proyecto A, B, C y D.")
elif is_corpus_project:
    st.sidebar.caption("Multinube conserva los lotes 1, 2 y 3 como subdivisiones; no se cuentan como proyectos adicionales.")
if selected_project == "Nuevo proyecto":
    project_name = st.sidebar.text_input("Nombre del proyecto", placeholder="Ej.: Contrato de infraestructura")
    active_project = project_name.strip() or "Nuevo proyecto sin nombre"
else:
    active_project = selected_project
selected_project_view = project_by_name(project_scope, selected_project) if project_scope else None
session_ingestion = st.session_state.get(f"project_ingestion::{active_project}")
session_analysis = st.session_state.get(f"project_risk_analysis::{active_project}")
session_project_view = (
    build_session_project_view(session_analysis, active_project)
    if session_analysis and not is_academic_demo else None
)
current_project_view = session_project_view or selected_project_view
active_project_id = current_project_view["project_id"] if current_project_view else ""
if is_corpus_project and selected_project != "Nuevo proyecto":
    active_project_id = next(p["project_id"] for p in corpus_catalog["projects"] if p["display_name"] == selected_project)
has_corpus_profile_pending = is_corpus_project and selected_project != "Nuevo proyecto" and current_project_view is None
is_processed_project = selected_project != "Nuevo proyecto" or session_project_view is not None
if current_project_view:
    profile = current_project_view["profile"]
    view_categories = current_project_view["categories"]
    view_distribution = current_project_view["level_distribution"]
    view_timeline = current_project_view["timeline"]
else:
    profile = {"signals_total": 0, "signals_scored": 0, "signals_pending": 0,
               "scoring_coverage": 0.0, "global_pird": None, "global_level": "PENDIENTE",
               "top_categories": [], "critical_signals": 0, "high_signals": 0}
    view_categories = []
    view_distribution = []
    view_timeline = {"source_documents": 0, "signals_with_document_date": 0,
                     "temporal_role_counts": {}, "persistence_level_counts": {}}
profile_scope = ("synthetic" if is_academic_demo else "session" if session_project_view else
                 "corpus" if selected_scope in {"Consolidado público", "Corpus por proyecto"} else "unverified")
profile_presentation = describe_pird_profile(profile, profile_scope)
st.sidebar.caption(f"Proyecto activo: {active_project}")
if current_project_view:
    st.sidebar.caption(f"{profile['signals_total']} señales asignadas · cobertura PIRD {profile['scoring_coverage']:.1%}")
if is_academic_demo:
    st.sidebar.warning("Datos 100 % sintéticos · no representan el corpus confidencial")
st.sidebar.divider()
selected_page = st.sidebar.radio("Navegación", NAVIGATION, label_visibility="collapsed")
st.sidebar.divider()
st.sidebar.caption("Datos del proyecto seleccionado" if current_project_view else "Proyecto pendiente de análisis")


if selected_page != "Portada":
    st.markdown(
        f"""<div class="hero"><div class="eyebrow" style="color:#A9DCE5">{active_project}</div>
        <h1>{selected_page}</h1><p>Monitoreo ejecutivo con trazabilidad, cobertura visible y privacidad por diseño.</p></div>""",
        unsafe_allow_html=True,
    )
    if is_academic_demo:
        st.info("Demostración académica con valores sintéticos. La estructura reproduce el flujo del sistema; los resultados no pertenecen a proyectos reales.")


def profile_notice() -> None:
    st.markdown(
        f"""<div class="notice"><strong>Estado del cálculo:</strong> {profile_presentation['calculation_label']}<br>
        <strong>Cobertura:</strong> {profile_presentation['coverage_text']} · {profile_presentation['coverage_label']}<br>
        <strong>Señales pendientes de componentes:</strong> {profile_presentation['signals_pending']}<br>
        <strong>Validación:</strong> {profile_presentation['validation_label']}</div>""",
        unsafe_allow_html=True,
    )
    st.caption(profile_presentation["validation_note"])
    st.caption(profile_presentation["index_note"])
    if profile_scope == "corpus" and project_scope and project_scope.get("method", {}).get("exposure_enrichment_version"):
        reviewed_components = int(project_scope.get("method", {}).get("expert_review", {}).get("components_reviewed", 0))
        if reviewed_components > 0:
            st.caption(
                f"Revisión adicional del corpus: {reviewed_components} componentes de severidad o probabilidad "
                "fueron revisados por el experto. Esta revisión es muestral y no valida todas las valoraciones del perfil."
            )
        else:
            st.caption("Las nuevas valoraciones de severidad y probabilidad de esta versión no han tenido revisión experta.")


def render_risk_details() -> None:
    st.subheader("Señales individuales y evidencia")
    if is_academic_demo:
        st.info("La demostración sintética contiene perfiles agregados, sin señales documentales individuales.")
        return
    if session_project_view:
        # The processing envelope already contains only accepted signals for the active session project.
        records = pd.DataFrame(session_analysis.get("private", {}).get("scored_signals", []))
    elif is_corpus_project and project_scope:
        manifest = json.loads((ROOT / "config/risk_detail_manifest.json").read_text(encoding="utf-8"))
        try:
            corpus_details = load_corpus_risk_details(
                (ROOT / "data/evaluation/risk_details/signals_published.csv").read_bytes(),
                manifest, corpus_catalog, project_scope)
        except (OSError, ValueError, KeyError, pd.errors.ParserError):
            st.error("El detalle publicado no concilia con el perfil vigente. No se mostrarán registros de otra versión.")
            return
        records = select_project_risk_details(corpus_details, active_project_id)
        st.caption("Detalle de la línea base conciliado con los perfiles publicados. Las señales ambiguas y multiproyecto quedan excluidas del proyecto activo.")
    else:
        st.info("No hay detalle individual disponible para este modo de datos.")
        return
    if records.empty:
        st.info("Este proyecto no tiene señales individuales asignadas en el conjunto disponible.")
        return
    detail_key = f"{selected_scope}::{active_project}"
    category_options = sorted(records.calibrated_category.dropna().unique().tolist())
    saved_filters = st.session_state.get("risk_detail_filters", {}).get(detail_key, {})
    d1, d2 = st.columns(2)
    selected_categories = d1.multiselect("Categoría de la señal", category_options,
                                      default=[c for c in saved_filters.get("categories", category_options) if c in category_options],
                                      key=f"detail_categories::{detail_key}")
    scoring_status = d2.selectbox("Estado de puntuación", ["Todas", "Puntuadas", "Pendientes"],
                                 index=["Todas", "Puntuadas", "Pendientes"].index(saved_filters.get("status", "Todas")), key=f"detail_status::{detail_key}")
    level_options = [level for level in LEVEL_ORDER if level in records.pird_level.dropna().unique()]
    level_filter_enabled = st.checkbox("Filtrar por nivel PIRD", value=saved_filters.get("use_levels", False), key=f"detail_use_levels::{detail_key}")
    selected_levels = (st.multiselect("Nivel PIRD de la señal", level_options,
                                     default=[v for v in saved_filters.get("levels", level_options) if v in level_options],
                                     key=f"detail_levels::{detail_key}") if level_filter_enabled else None)
    query = st.text_input("Buscar en señal, documento o evidencia", value=saved_filters.get("query", ""), key=f"detail_query::{detail_key}")
    st.session_state.setdefault("risk_detail_filters", {})[detail_key] = {
        "categories": selected_categories, "status": scoring_status, "use_levels": level_filter_enabled,
        "levels": selected_levels or [], "query": query,
    }
    visible = filter_risk_details(records, selected_categories, selected_levels, scoring_status, query)
    st.caption(f"{len(visible)} de {len(records)} señales del proyecto seleccionado.")
    if visible.empty:
        st.info("No hay señales que cumplan los filtros seleccionados.")
        return
    columns = [c for c in ['item_id', 'title', 'calibrated_type', 'calibrated_category', 'pird', 'pird_level',
                          'severity', 'probability', 'recurrence_level', 'persistence_level',
                          'source_filename', 'source_page', 'pird_missing_components'] if c in visible]
    labels = {'item_id': 'ID', 'title': 'Señal', 'calibrated_type': 'Tipo', 'calibrated_category': 'Categoría',
              'pird': 'PIRD', 'pird_level': 'Nivel', 'severity': 'Severidad', 'probability': 'Probabilidad',
              'recurrence_level': 'Recurrencia', 'persistence_level': 'Persistencia',
              'source_filename': 'Documento', 'source_page': 'Página', 'pird_missing_components': 'Componentes faltantes'}
    st.dataframe(visible[columns].rename(columns=labels), width="stretch", hide_index=True)
    st.download_button("Descargar señales filtradas", visible[columns].to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"riesgos_{active_project_id}_filtrados.csv", mime="text/csv", key=f"detail_download::{detail_key}")
    chosen = st.selectbox("Seleccionar señal para ver su evidencia", visible.item_id.tolist(),
                          format_func=lambda item: f"{item} · {visible.loc[visible.item_id == item, 'title'].iloc[0]}",
                          key=f"detail_item::{detail_key}")
    row = visible.loc[visible.item_id == chosen].iloc[0]
    st.markdown("#### Evidencia documental de la señal")
    st.text(str(row.get("statement", "")))
    st.write("Documento:", str(row.get("source_filename", "No disponible")))
    page = row.get("source_page")
    st.write("Página:", str(page) if pd.notna(page) else "No identificada")
    quote = row.get("evidence_quote")
    st.text(str(quote) if pd.notna(quote) else "Sin cita registrada")
    detail_components = [
        {"Componente": name, "Nivel 1–5": row.get(col)}
        for name, col in [("Severidad", "severity"), ("Probabilidad", "probability"),
                          ("Recurrencia", "recurrence_level"), ("Persistencia", "persistence_level")]
    ]
    sufficient = row.get("calibrated_evidence_sufficient")
    confidence = row.get("calibrated_confidence")
    detail_components += [
        {"Componente": "Evidencia", "Nivel 1–5": 5.0 if sufficient == 1 else None},
        {"Componente": "Confianza", "Nivel 1–5": 1 + 4 * float(confidence) if pd.notna(confidence) else None},
    ]
    st.dataframe(pd.DataFrame(detail_components), width="stretch", hide_index=True)
    if row.get("pird_status") == "CALCULADO":
        st.metric("PIRD de la señal", f"{float(row['pird']):.2f}", str(row.get("pird_level", "")))
    else:
        st.info("PIRD pendiente. Componentes faltantes: " + str(row.get("pird_missing_components", "No especificados")))
    for component, label in [("severity", "Severidad"), ("probability", "Probabilidad")]:
        source = row.get(component + "_assessment_source")
        if source == "REVISION_EXPERTA_CONFIRMADA":
            st.caption(f"{label}: nivel confirmado mediante revisión experta de este caso.")
    provenance_path = ROOT / "data/evaluation/risk_details/component_provenance.json"
    provenance = (json.loads(provenance_path.read_text(encoding="utf-8")).get("components", {})
                  if is_corpus_project and not session_project_view else {})
    updated_components = []
    for component, label in [("severity", "Severidad"), ("probability", "Probabilidad")]:
        assessment = provenance.get(f"{row['item_id']}:{component}")
        if assessment and assessment["level"] == row.get(component):
            updated_components.append(component)
            method_label = ("Revisión experta confirmada" if assessment["expert_reviewed"]
                            else "Enriquecimiento documental asistido por IA; sin revisión experta de este componente")
            st.markdown(f"#### Sustento vigente · {label}")
            st.caption(method_label)
            st.write("Documento:", assessment["source_filename"])
            st.write("Página:", str(assessment["source_page"]))
            st.text(assessment["quote"])
            st.text(assessment["justification"])
    justification = row.get("exposure_justification")
    if pd.notna(justification):
        if updated_components:
            with st.expander("Registro histórico de la valoración"):
                st.caption("Este texto se conserva para trazabilidad. El sustento vigente de los componentes actualizados se muestra arriba.")
                st.text(str(justification))
        else:
            st.write("Sustento registrado en la valoración histórica:")
            st.text(str(justification))
    st.caption("Los niveles ausentes permanecen vacíos. El detalle del corpus está publicado y se carga automáticamente para el proyecto seleccionado.")


if ((selected_project == "Nuevo proyecto" or session_ingestion is not None) and session_project_view is None or has_corpus_profile_pending) and selected_page in {
    "Resumen ejecutivo", "Radar de riesgos", "Timeline", "Riesgos priorizados", "Perfil del proyecto",
}:
    st.info("Este proyecto todavía no tiene un perfil calculado. La consulta documental está disponible para proyectos del corpus; el perfil requiere un análisis de sus señales.")
    st.stop()


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
    if is_corpus_project and active_project_id:
        corpus_chunks = pd.read_csv(ROOT / "data/processed/chunks/chunks_recursive.csv")
        _, reconciliation = reconcile_chunks(corpus_chunks, corpus_catalog)
        project_count = next(p["chunks_single_project"] for p in reconciliation["projects"] if p["project_id"] == active_project_id)
        st.info(f"Índice publicado: {project_count} fragmentos asignados automáticamente a este proyecto. Los fragmentos ambiguos o pendientes quedan excluidos de sus consultas.")
        st.caption("La asignación a fragmentos determina el alcance de las consultas. Los documentos compartidos pueden aparecer en más de un proyecto.")
        corpus_documents = build_document_timeline(corpus_chunks, active_project_id, corpus_catalog)
        st.subheader("Documentos del proyecto")
        st.metric("Documentos que mencionan el proyecto", corpus_documents["documents_total"])
        documents_table = pd.DataFrame(corpus_documents["documents"])
        if documents_table.empty:
            st.info("No se encontraron documentos que mencionen este proyecto en el corpus publicado.")
        else:
            document_search = st.text_input("Buscar documento", key=f"document_search::{active_project_id}")
            if document_search:
                documents_table = documents_table[documents_table["filename"].str.contains(document_search, case=False, regex=False)]
            st.dataframe(documents_table[["filename", "document_date"]].rename(
                columns={"filename": "Documento", "document_date": "Fecha identificada en el nombre"}), width="stretch", hide_index=True)
            st.download_button("Descargar inventario filtrado", documents_table.to_csv(index=False).encode("utf-8-sig"),
                               file_name=f"documentos_{active_project_id}.csv", mime="text/csv")
    uploaded_files = st.file_uploader(
        "Cargue documentos de aseguramiento técnico",
        type=list(SUPPORTED_DOCUMENT_TYPES),
        accept_multiple_files=True,
        help="Formatos permitidos: PDF y DOCX. En esta fase los archivos permanecen en la sesión y no se publican.",
    )
    if uploaded_files:
        inventory = pd.DataFrame([
            {
                "Documento": item.name,
                "Formato": Path(item.name).suffix.upper().lstrip("."),
                "Tamaño (KB)": round(item.size / 1024, 1),
                "Estado": "Listo para ingesta" if item.size > 0 else "Archivo vacío",
            }
            for item in uploaded_files
        ])
        valid_documents = int((inventory["Estado"] == "Listo para ingesta").sum())
        if valid_documents == len(uploaded_files):
            st.success(f"{valid_documents} documento(s) recibido(s) para {active_project}.")
        else:
            st.error("Uno o más archivos están vacíos. Corríjalos antes de continuar.")
        st.dataframe(inventory, width="stretch", hide_index=True)
        ingestion_key = f"project_ingestion::{active_project}"
        risk_analysis_key = f"project_risk_analysis::{active_project}"
        process_clicked = st.button(
            "Procesar documentos",
            type="primary",
            disabled=valid_documents != len(uploaded_files),
            width="stretch",
        )
        if process_clicked:
            try:
                with st.status("Procesando documentos…", expanded=True) as processing_status:
                    processing_status.write("Extrayendo y limpiando texto de PDF/DOCX.")
                    processing_status.write("Aplicando chunking recursivo aprobado: 2.200 caracteres y 300 de solapamiento.")
                    processing_status.write("Generando embeddings normalizados con BAAI/bge-m3.")
                    ingestion_result = ingest_project_documents(
                        project_id=active_project_id or active_project,
                        files=[{"name": item.name, "content": item.getvalue()} for item in uploaded_files],
                        encoder=get_embedding_model(),
                        project_catalog=corpus_catalog if active_project_id in {p["project_id"] for p in corpus_catalog["projects"]} else None,
                    )
                    st.session_state[ingestion_key] = ingestion_result
                    st.session_state.pop(risk_analysis_key, None)
                    st.session_state.pop(f"chat_history::{active_project}", None)
                    processing_status.update(label="Procesamiento documental completado", state="complete", expanded=False)
                st.rerun()
            except Exception:
                st.error("No fue posible completar la ingesta. Revise que los archivos contengan texto extraíble e intente nuevamente.")
        ingestion_result = st.session_state.get(ingestion_key)
        if ingestion_result:
            ingestion_summary = ingestion_result["summary"]
            i1, i2, i3, i4 = st.columns(4)
            i1.metric("Documentos procesados", ingestion_summary["documents_processed"])
            i2.metric("Páginas", ingestion_summary["pages"])
            i3.metric("Chunks", ingestion_summary["chunks"])
            i4.metric("Dimensiones BGE-M3", ingestion_summary["embedding_dimensions"])
            st.dataframe(pd.DataFrame(ingestion_result["documents"]), width="stretch", hide_index=True)
            if ingestion_result["errors"]:
                st.warning("La ingesta terminó con advertencias en algunos documentos.")
                st.dataframe(pd.DataFrame(ingestion_result["errors"]), width="stretch", hide_index=True)
            st.success("Documentos procesados. Los fragmentos y vectores están disponibles para este proyecto en la sesión.")
            scope_summary = ingestion_result.get("project_scope", {})
            if scope_summary.get("mode") == "DOCUMENT_EVIDENCE":
                st.caption(f"Fragmentos del proyecto activo: {scope_summary['chunks_active_project']} de {scope_summary['chunks_total']}. Los ambiguos y de otros proyectos no se usan en su chat.")
            else:
                st.warning("Proyecto declarado por el usuario: falta configurar el catálogo documental para verificar a qué proyecto pertenece cada fragmento y señal.")
            api_key = get_openai_api_key()
            if not api_key:
                st.warning("Configure la conexión con OpenAI para analizar los documentos.")
            analyze_clicked = st.button(
                "Analizar riesgos",
                type="primary",
                disabled=not api_key,
                width="stretch",
            )
            if analyze_clicked:
                try:
                    from openai import OpenAI

                    with st.status("Analizando riesgos del proyecto…", expanded=True) as risk_status:
                        risk_status.write("Extrayendo señales y verificando evidencia literal.")
                        risk_status.write("Aplicando clasificación y puerta determinista de validación.")
                        risk_status.write("Calculando recurrencia, persistencia y componentes PIRD disponibles.")
                        analysis = process_project_risks(
                            ingestion_result=ingestion_result,
                            client=OpenAI(api_key=api_key),
                            encoder=get_embedding_model(),
                            calibration_examples=get_calibration_examples(),
                        )
                        st.session_state[risk_analysis_key] = analysis
                        risk_status.update(label="Análisis de riesgos completado", state="complete", expanded=False)
                    st.rerun()
                except Exception:
                    st.error(
                        "No fue posible completar el análisis de riesgos. Verifique la conexión del modelo, "
                        "el límite de 100 chunks y vuelva a intentarlo."
                    )

            analysis = st.session_state.get(risk_analysis_key)
            if analysis:
                risk_summary = analysis["summary"]
                signal_scope = analysis.get("project_scope", {})
                if signal_scope.get("mode") == "DOCUMENT_EVIDENCE":
                    st.caption(f"Elementos documentales asignados al proyecto: {signal_scope['signals_active_project']}; fuera del alcance o pendientes: {signal_scope['signals_excluded_or_pending']}.")
                st.markdown("#### Resultado del análisis de riesgos")
                r1, r2, r3, r4 = st.columns(4)
                r1.metric("Señales extraídas", risk_summary["items_extracted"])
                r2.metric("Señales validadas", risk_summary["signals_validated"])
                r3.metric("Puntuadas", risk_summary["signals_scored"])
                r4.metric("Cobertura PIRD", f"{risk_summary['scoring_coverage']:.1%}")
                if risk_summary["global_pird"] is None:
                    st.warning(
                        "El PIRD permanece pendiente: la evidencia disponible no permite completar todos "
                        "los componentes requeridos. No se imputaron valores."
                    )
                else:
                    st.success(
                        f"PIRD del proyecto: {risk_summary['global_pird']:.2f} · "
                        f"nivel {risk_summary['global_level']} · {describe_pird_profile(risk_summary, 'session')['calculation_label']}"
                    )
                    st.caption(describe_pird_profile(risk_summary, "session")["validation_label"])
                if analysis["classification"]["calibration_status"] == "PROVISIONAL_NO_PRIVATE_EXAMPLES":
                    st.warning(
                        "Clasificación sin ejemplos humanos configurados: los 29 ejemplos de calibración no están "
                        "configurados en el servidor. Se aplicó la misma taxonomía y reglas, sin afirmar "
                        "calibración humana para estos documentos nuevos."
                    )
                elif analysis["classification"]["calibration_status"] == "CALIBRATED":
                    st.caption(
                        f"Clasificación con {analysis['classification']['human_examples_available']} "
                        "ejemplos humanos privados."
                    )
                if analysis["categories"]:
                    st.dataframe(pd.DataFrame(analysis["categories"]), width="stretch", hide_index=True)
                st.caption(
                    "Vista agregada en memoria. La evidencia, los textos y las señales individuales no "
                    "se muestran ni se escriben en el repositorio. Las demás vistas del proyecto se actualizan en esta sesión."
                )
    else:
        st.info("Seleccione uno o varios archivos PDF/DOCX. No se enviarán al repositorio público.")
    st.subheader("Estado del proyecto")
    if uploaded_files and st.session_state.get(f"project_ingestion::{active_project}"):
        st.success("Ingesta documental completada · embeddings BGE-M3 disponibles en la sesión")
    elif has_corpus_profile_pending:
        st.warning("Perfil por proyecto pendiente de cálculo; el índice documental está disponible.")
    elif is_processed_project:
        st.success(f"Proyecto procesado · {profile['signals_total']} señales · contrato de datos 1.0.0")
    else:
        st.warning("Proyecto nuevo · pendiente de carga y procesamiento")

elif selected_page == "Resumen ejecutivo":
    if not is_processed_project:
        st.warning("Este proyecto todavía no tiene documentos procesados. Cárguelos en Proyectos y documentos.")
    profile_notice()
    st.write("")
    col1, col2, col3, col4 = st.columns(4)
    pird_label = f"{profile['global_pird']:.2f}" if profile["global_pird"] is not None else "Pendiente"
    col1.metric("PIRD global", pird_label, profile["global_level"])
    col2.metric("Cobertura", f"{profile['scoring_coverage']:.1%}")
    col3.metric("Señales puntuadas", f"{profile['signals_scored']:,}")
    col4.metric("Pendientes", f"{profile['signals_pending']:,}")
    st.subheader("Lectura ejecutiva")
    left, right = st.columns([1.35, 1])
    with left:
        st.markdown(
            f"""<div class="section-card"><div class="eyebrow">Estado del proyecto</div>
            <h3>{profile['global_level']} · {profile_presentation['calculation_label']}</h3>
            <p>El perfil consolida {profile['signals_scored']} señales completas de un total de
            {profile['signals_total']}. Las categorías que requieren mayor atención agregada son
            {', '.join(profile['top_categories']) or 'pendientes de puntuación'}.</p></div>""", unsafe_allow_html=True)
    with right:
        if session_project_view:
            st.markdown(
                f"""<div class="section-card"><div class="eyebrow">Análisis de documentos de la sesión</div>
                <h3>{session_project_view['display_name']}</h3>
                <p>Las vistas utilizan únicamente los agregados producidos por los documentos recién procesados para este proyecto.</p></div>""",
                unsafe_allow_html=True,
            )
        elif selected_project_view:
            st.markdown(
                f"""<div class="section-card"><div class="eyebrow">Alcance por proyecto</div>
                <h3>{selected_project_view['display_name']}</h3>
                <p>El perfil utiliza las señales del proyecto activo. Los casos ambiguos conservan su asignación pendiente. {profile_presentation['validation_note']}</p></div>""",
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
    profile_notice()
    st.subheader("Radar PIRD por categoría")
    categories = pd.DataFrame(view_categories)
    if categories.empty:
        st.warning("El proyecto no tiene categorías con PIRD calculado todavía.")
    else:
        with st.container(border=True):
            f1, f2, f3 = st.columns([1.4, 1, 1])
            chosen_categories = f1.multiselect("Categorías", categories["category"].tolist(), default=categories["category"].tolist(), key=f"radar_categories::{selected_scope}::{active_project}")
            available_levels = [level for level in LEVEL_ORDER if level in categories["category_level"].unique()]
            chosen_levels = f2.multiselect("Niveles", available_levels, default=available_levels, key=f"radar_levels::{selected_scope}::{active_project}")
            minimum_coverage = f3.slider("Cobertura mínima", 0, 100, 0, 5, format="%d %%", key=f"radar_coverage::{selected_scope}::{active_project}") / 100
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
    st.info("Los indicadores de recurrencia y persistencia se complementan con una cronología de documentos. Las fechas ausentes o inválidas permanecen sin asignar.")
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("Documentos fuente", temporal["source_documents"])
    t2.metric("Señales con fecha", temporal["signals_with_document_date"])
    t3.metric("Señales recurrentes", temporal["temporal_role_counts"].get("RECURRENCIA", 0))
    t4.metric("Persistencia nivel 5", temporal["persistence_level_counts"].get("5", 0))
    left, right = st.columns(2)
    with left:
        st.markdown("#### Rol temporal")
        if temporal["temporal_role_counts"]:
            st.plotly_chart(build_temporal_role_figure(temporal["temporal_role_counts"]), width="stretch")
        else:
            st.warning("No hay roles temporales calculados.")
    with right:
        st.markdown("#### Nivel de persistencia")
        if temporal["persistence_level_counts"]:
            st.plotly_chart(build_persistence_figure(temporal["persistence_level_counts"]), width="stretch")
        else:
            st.warning("No hay niveles de persistencia calculados.")
    if not is_academic_demo:
        st.subheader("Cronología documental")
        if session_ingestion:
            chronology_chunks = pd.DataFrame(session_ingestion["chunks"])
            chronology_catalog = session_ingestion.get("project_catalog")
            chronology_project = session_ingestion["project_id"] if chronology_catalog else None
        else:
            chronology_chunks = pd.read_csv(ROOT / "data/processed/chunks/chunks_recursive.csv")
            chronology_catalog = corpus_catalog
            chronology_project = active_project_id or None
        from src.risk.verified_document_dates import verify_document_dates
        chronology_dates = None if session_ingestion else verify_document_dates(
            json.loads((ROOT / "config/document_dates_verified.json").read_text(encoding="utf-8")),
            ROOT / "data/raw/corpus_actualizado")
        chronology = build_document_timeline(chronology_chunks, chronology_project, chronology_catalog, chronology_dates)
        d1, d2, d3 = st.columns(3)
        d1.metric("Documentos en la cronología", chronology["documents_total"])
        d2.metric("Con fecha identificada", chronology["documents_dated"])
        d3.metric("Sin fecha identificada", chronology["documents_undated"])
        if chronology["monthly_counts"]:
            monthly_documents = pd.DataFrame(chronology["monthly_counts"]).rename(columns={"month": "Mes", "documents": "Documentos"})
            st.bar_chart(monthly_documents.set_index("Mes"), x_label="Mes documental", y_label="Documentos")
        else:
            st.info("No hay fechas identificadas para construir la cronología de estos documentos.")
        if chronology["documents"]:
            chronology_table = pd.DataFrame(chronology["documents"])
            chronology_table["date_source"] = chronology_table["date_source"].map(lambda value: "Nombre de archivo" if str(value).startswith("FILENAME_") else "Contenido documental verificado" if value == "DOCUMENT_BODY_VERIFIED" else "No identificada")
            chronology_table["date_precision"] = chronology_table["date_precision"].map({"DAY": "Día", "MONTH": "Mes"})
            st.dataframe(chronology_table.rename(columns={
                "filename": "Documento", "document_date": "Fecha documental",
                "date_source": "Fuente de fecha", "date_precision": "Precisión",
                "date_warning": "Observación de fecha"}), width="stretch", hide_index=True)
        st.caption("La cronología cuenta documentos, no riesgos. Cuando se selecciona un proyecto, incluye documentos que lo mencionan, también compartidos con otros proyectos; esto no asigna todas sus señales ni habilita esos fragmentos para el chat. Las fechas proceden de nombres de archivo y, para el corpus original, de citas documentales verificadas. Se conserva su precisión y las sesiones no heredan fechas del corpus.")

elif selected_page == "Riesgos priorizados":
    if not is_processed_project:
        st.warning("La priorización estará disponible después de procesar los documentos del proyecto.")
    profile_notice()
    render_risk_details()
    st.subheader("Priorización agregada por categoría")
    categories = pd.DataFrame(view_categories)
    if categories.empty:
        st.warning("El proyecto no tiene riesgos con PIRD calculado todavía.")
    else:
        selected_priority_levels = st.multiselect(
            "Nivel de riesgo", [level for level in LEVEL_ORDER if level in categories["category_level"].unique()],
            default=[level for level in LEVEL_ORDER if level in categories["category_level"].unique()], key=f"priority_levels::{selected_scope}::{active_project}",
        )
        prioritized = filter_categories(view_categories, selected_levels=selected_priority_levels)
        if prioritized.empty:
            st.warning("No existen riesgos que cumplan el filtro seleccionado.")
        else:
            st.plotly_chart(build_category_priority_figure(prioritized), width="stretch")
            table = prioritized[["category", "category_score", "category_level", "scoring_coverage", "scored_signals", "total_signals"]].copy()
            table["scoring_coverage"] = table["scoring_coverage"].map(lambda value: f"{value:.1%}")
            st.dataframe(table.rename(columns={"category": "Categoría", "category_score": "PIRD", "category_level": "Nivel", "scoring_coverage": "Cobertura", "scored_signals": "Puntuadas", "total_signals": "Total"}), width="stretch", hide_index=True)
    st.caption("Priorización agregada por categoría. Las señales individuales y sus evidencias están disponibles en el detalle del proyecto.")

elif selected_page == "Perfil del proyecto":
    profile_notice()
    st.subheader("Distribución del PIRD")
    distribution = pd.DataFrame(view_distribution)
    if distribution.empty:
        st.info("Este proyecto no tiene señales puntuadas para mostrar una distribución.")
    else:
        st.bar_chart(distribution.set_index("pird_level")["signal_count"])
    st.dataframe(distribution, width="stretch", hide_index=True)
    st.subheader("Escenarios de sensibilidad")
    if session_project_view:
        st.info("La sensibilidad no se recalcula para documentos nuevos en esta fase; se conservan los pesos PIRD aprobados.")
    elif selected_project_view:
        st.info("La sensibilidad de pesos continúa reportándose para la vista consolidada; el PIRD por proyecto conserva los pesos aprobados.")
    else:
        st.dataframe(pd.DataFrame(snapshot["sensitivity"]), width="stretch", hide_index=True)

elif selected_page == "Pregunte a sus documentos":
    st.subheader("Asistente documental")
    st.write("Consulte el corpus del proyecto activo. Las respuestas se generan únicamente con evidencia recuperada mediante BGE-M3.")
    if is_academic_demo:
        st.info("El modo sintético demuestra los perfiles y radares. El asistente se desactiva porque no existe un corpus documental sintético asociado.")
    elif session_ingestion:
        st.info("La consulta utiliza únicamente los documentos procesados en esta sesión para el proyecto activo.")
        if session_ingestion.get("project_scope", {}).get("mode") != "DOCUMENT_EVIDENCE":
            st.warning("El alcance corresponde a la selección del usuario; la pertenencia documental al proyecto aún no está verificada.")
    elif not is_processed_project:
        st.warning("Este proyecto aún no tiene un índice documental. Cargue y procese sus documentos para habilitar las consultas.")
    elif active_project_id:
        st.info(f"La recuperación está limitada a fragmentos asignados automáticamente al proyecto {active_project}. Los ambiguos y pendientes quedan excluidos.")
    api_key = get_openai_api_key()
    if not api_key:
        st.warning("El asistente está listo, pero la clave del modelo aún no está configurada como secreto del servidor.")
        st.caption("Configure `OPENAI_API_KEY` en Streamlit Secrets. La clave no debe escribirse en la aplicación ni publicarse en GitHub.")
    st.markdown("**Preguntas sugeridas**")
    st.caption("Seleccione una pregunta demostrativa o escriba una consulta propia.")

    history_key = f"chat_history::{active_project}"
    if history_key not in st.session_state:
        st.session_state[history_key] = []
    for exchange in st.session_state[history_key]:
        with st.chat_message("user"):
            st.write(exchange["question"])
        with st.chat_message("assistant"):
            if exchange.get("response_status") == "ERROR":
                st.error(exchange["answer"])
                if exchange.get("diagnostic_code"):
                    st.caption(f"Diagnóstico técnico: {exchange['diagnostic_code']}")
            elif not exchange.get("evidence_available"):
                st.warning(exchange["answer"])
            else:
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

    assistant_disabled = not api_key or is_academic_demo or (not session_ingestion and (not is_processed_project or session_project_view is not None))
    demo_question = None
    question_columns = st.columns(len(DEMONSTRATION_QUESTIONS))
    for index, prompt in enumerate(DEMONSTRATION_QUESTIONS):
        if question_columns[index].button(
            prompt,
            key=f"demo-question-{index}",
            disabled=assistant_disabled,
            width="stretch",
        ):
            demo_question = prompt

    typed_question = st.chat_input(
        "Escriba una pregunta sobre los documentos",
        disabled=assistant_disabled,
    )
    question = demo_question or typed_question
    if question:
        with st.spinner("Recuperando evidencia y preparando la respuesta…"):
            if session_ingestion:
                from openai import OpenAI

                service = ConversationalRagService(
                    retriever=SessionRetriever(session_ingestion, get_embedding_model()),
                    answerer=OpenAIRagAnswerer(client=OpenAI(api_key=api_key)),
                )
                exchange = service.ask(question)
            else:
                exchange = get_chat_service(api_key, active_project_id, active_project).ask(question)
        st.session_state[history_key] = append_history(st.session_state[history_key], exchange)
        st.rerun()
    st.caption("El asistente no usa conocimiento externo. Verifique siempre la respuesta en las fuentes citadas.")

else:
    st.subheader("Metodología de la solución")
    st.write(f"**Proyecto seleccionado:** {active_project}. Los indicadores de esta página corresponden al modo de datos activo.")
    st.markdown("""
**Consulta documental.** Los PDF y DOCX se transforman en texto y fragmentos mediante chunking recursivo.
BGE-M3 representa los fragmentos y la consulta original. La recuperación selecciona hasta cinco fragmentos;
el filtro del proyecto se aplica antes de seleccionar los resultados. El generador responde con las fuentes recuperadas.
HyDE y reranking fueron evaluados y no forman parte de la configuración seleccionada.

**Señales de riesgo.** El análisis identifica señales documentales, clasifica su tipo y verifica su evidencia.
La severidad y la probabilidad se valoran en escala de 1 a 5 mediante rúbricas asistidas por IA.
La recurrencia semántica se calcula dentro del proyecto con umbral de similitud 0,70.
La persistencia utiliza las fechas documentales disponibles. Los componentes sin sustento quedan pendientes.

**PIRD.** Los niveles de 1 a 5 se normalizan con (nivel − 1) / 4.
La exposición combina severidad (40 %), probabilidad (25 %), recurrencia (20 %) y persistencia (15 %).
La confiabilidad combina evidencia (60 %) y confianza de clasificación (40 %).
El puntaje es 100 × exposición × (0,70 + 0,30 × confiabilidad); se calcula solo con los seis componentes disponibles.
Por categoría se combina 70 % de la media y 30 % del percentil 90 de los puntajes.
El perfil global combina 70 % de la media de categorías evaluables y 30 % de su máximo.
El PIRD expresa prioridad relativa; no estima una probabilidad estadística de incumplimiento.

**Validación y alcance.** La revisión experta del corpus es interna y muestral.
Incluye clasificación, suficiencia de evidencia y valoraciones de componentes en los casos revisados;
no valida automáticamente todo el corpus ni el desempeño en proyectos nuevos.
La consulta conversacional reutiliza el índice y no recalcula el perfil de riesgo.
""")
    st.subheader("Datos del proyecto seleccionado")
    profile_notice()
    m1, m2, m3 = st.columns(3)
    m1.metric("Señales del proyecto", profile["signals_total"])
    m2.metric("Señales puntuadas", profile["signals_scored"])
    m3.metric("Señales pendientes de componentes", profile["signals_pending"])
    if project_scope:
        assignment = project_scope["assignment"]
        st.caption(f"Contexto del conjunto activo: {assignment['signals_total']} señales; "
                   f"{assignment['signals_assigned_single_project']} asignadas a un proyecto y "
                   f"{assignment['signals_pending_or_ambiguous']} con asignación pendiente o ambigua.")
    if view_categories:
        method_table = pd.DataFrame(view_categories)
        st.dataframe(method_table.rename(columns={"category": "Categoría", "category_score": "PIRD",
            "category_level": "Nivel", "scoring_coverage": "Cobertura", "scored_signals": "Puntuadas",
            "total_signals": "Total"}), width="stretch", hide_index=True)
    if is_academic_demo:
        st.warning("Los valores de esta vista son sintéticos y sirven para demostrar la navegación por proyecto.")
    st.caption("Las métricas experimentales y la revisión experta se documentan en el informe académico; la interfaz no atribuye una aprobación general a todas las señales.")

st.divider()
st.caption("Proyecto de maestría · Sistema RAG y Perfil Inteligente de Riesgo")


