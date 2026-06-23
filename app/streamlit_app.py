
import pandas as pd
import plotly.express as px
import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title='Radar de Riesgos Documentales',
    page_icon='📄',
    layout='wide'
)

st.title('📄 Radar de Riesgos Documentales')
st.caption('Sistema Inteligente de Vigilancia de Riesgos basado en RAG y LLMs')


@st.cache_data
def load_data():
    base_paths = [
        Path('.'),
        Path('data/evaluation/timeline'),
        Path('../data/evaluation/timeline')
    ]

    def find_file(filename):
        for base in base_paths:
            candidate = base / filename
            if candidate.exists():
                return candidate
        return None

    timeline_path = find_file('timeline_riesgos.csv')
    radar_path = find_file('radar_riesgos_resumen.csv')
    priorizados_path = find_file('riesgos_priorizados.csv')

    if timeline_path is None or radar_path is None or priorizados_path is None:
        st.error('No se encontraron los archivos requeridos. Verifica que estén en data/evaluation/timeline/.')
        st.stop()

    timeline = pd.read_csv(timeline_path)
    radar = pd.read_csv(radar_path)
    priorizados = pd.read_csv(priorizados_path)

    if 'fecha_documento' in timeline.columns:
        timeline['fecha_documento'] = pd.to_datetime(timeline['fecha_documento'], errors='coerce')
    if 'fecha_documento' in priorizados.columns:
        priorizados['fecha_documento'] = pd.to_datetime(priorizados['fecha_documento'], errors='coerce')

    return timeline, radar, priorizados


timeline_df, radar_df, priorizados_df = load_data()

# -----------------------------
# Sidebar filters
# -----------------------------
st.sidebar.header('Filtros')

categorias = sorted(timeline_df['risk_category'].dropna().unique().tolist()) if 'risk_category' in timeline_df.columns else []
prioridades = sorted(timeline_df['risk_priority'].dropna().unique().tolist()) if 'risk_priority' in timeline_df.columns else []
severidades = sorted(timeline_df['severity'].dropna().unique().tolist()) if 'severity' in timeline_df.columns else []

selected_categories = st.sidebar.multiselect('Categoría de riesgo', categorias, default=categorias)
selected_priorities = st.sidebar.multiselect('Prioridad', prioridades, default=prioridades)
selected_severities = st.sidebar.multiselect('Severidad', severidades, default=severidades)

filtered = timeline_df.copy()

if selected_categories and 'risk_category' in filtered.columns:
    filtered = filtered[filtered['risk_category'].isin(selected_categories)]
if selected_priorities and 'risk_priority' in filtered.columns:
    filtered = filtered[filtered['risk_priority'].isin(selected_priorities)]
if selected_severities and 'severity' in filtered.columns:
    filtered = filtered[filtered['severity'].isin(selected_severities)]

# -----------------------------
# KPIs
# -----------------------------
st.subheader('Indicadores generales')

col1, col2, col3, col4 = st.columns(4)

total_riesgos = len(filtered)
riesgos_criticos = len(filtered[filtered['risk_priority'] == 'Crítico']) if 'risk_priority' in filtered.columns else 0
categorias_activas = filtered['risk_category'].nunique() if 'risk_category' in filtered.columns else 0
score_promedio = filtered['risk_score'].mean() if 'risk_score' in filtered.columns and len(filtered) > 0 else 0

col1.metric('Riesgos filtrados', total_riesgos)
col2.metric('Riesgos críticos', riesgos_criticos)
col3.metric('Categorías activas', categorias_activas)
col4.metric('Score promedio', f'{score_promedio:.2f}')

# -----------------------------
# Charts
# -----------------------------
st.subheader('Distribución de riesgos')

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    if 'risk_category' in filtered.columns and len(filtered) > 0:
        cat_df = filtered.groupby('risk_category').size().reset_index(name='cantidad')
        fig = px.bar(
            cat_df.sort_values('cantidad', ascending=False),
            x='risk_category',
            y='cantidad',
            title='Riesgos por categoría',
            labels={'risk_category': 'Categoría', 'cantidad': 'Cantidad'}
        )
        st.plotly_chart(fig, use_container_width=True)

with chart_col2:
    if 'risk_priority' in filtered.columns and len(filtered) > 0:
        prio_df = filtered.groupby('risk_priority').size().reset_index(name='cantidad')
        fig = px.bar(
            prio_df,
            x='risk_priority',
            y='cantidad',
            title='Riesgos por prioridad',
            labels={'risk_priority': 'Prioridad', 'cantidad': 'Cantidad'}
        )
        st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Timeline
# -----------------------------
st.subheader('Timeline de riesgos')

timeline_plot = filtered[filtered['fecha_documento'].notna()].copy() if 'fecha_documento' in filtered.columns else pd.DataFrame()

if len(timeline_plot) > 0:
    fig = px.scatter(
        timeline_plot,
        x='fecha_documento',
        y='risk_category',
        size='risk_score',
        color='risk_priority',
        hover_data=['risk_id', 'risk_name', 'severity', 'probability', 'source_filename'],
        title='Evolución temporal de riesgos documentales'
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info('No hay fechas disponibles para graficar el timeline.')

# -----------------------------
# Radar summary
# -----------------------------
st.subheader('Resumen tipo radar')

if len(filtered) > 0:
    radar_filtered = (
        filtered.groupby('risk_category')
        .agg(
            cantidad_riesgos=('risk_id', 'count'),
            score_promedio=('risk_score', 'mean'),
            score_maximo=('risk_score', 'max')
        )
        .reset_index()
    )
    fig = px.line_polar(
        radar_filtered,
        r='score_promedio',
        theta='risk_category',
        line_close=True,
        title='Radar por score promedio de riesgo'
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(radar_filtered, use_container_width=True)

# -----------------------------
# Prioritized table
# -----------------------------
st.subheader('Riesgos priorizados')

table_cols = [
    'risk_id', 'risk_name', 'risk_category', 'severity', 'probability',
    'risk_score', 'risk_priority', 'fecha_documento_texto',
    'source_filename', 'source_chunk_id', 'evidence', 'recommended_action'
]

available_cols = [c for c in table_cols if c in filtered.columns]

st.dataframe(
    filtered[available_cols].sort_values('risk_score', ascending=False),
    use_container_width=True,
    height=500
)

# -----------------------------
# Evidence explorer
# -----------------------------
st.subheader('Explorador de evidencia documental')

if len(filtered) > 0:
    selected_risk = st.selectbox(
        'Selecciona un riesgo',
        filtered['risk_id'].astype(str).tolist()
    )

    risk_row = filtered[filtered['risk_id'].astype(str) == selected_risk].iloc[0]

    st.markdown(f"**Riesgo:** {risk_row.get('risk_name', '')}")
    st.markdown(f"**Categoría:** {risk_row.get('risk_category', '')}")
    st.markdown(f"**Prioridad:** {risk_row.get('risk_priority', '')}")
    st.markdown(f"**Documento:** {risk_row.get('source_filename', '')}")
    st.markdown(f"**Chunk:** {risk_row.get('source_chunk_id', '')}")
    st.markdown('**Evidencia:**')
    st.info(str(risk_row.get('evidence', '')))
    st.markdown('**Acción recomendada:**')
    st.write(str(risk_row.get('recommended_action', '')))

st.caption('Versión académica inicial. Dashboard generado desde notebooks de extracción, evaluación y timeline de riesgos.')
