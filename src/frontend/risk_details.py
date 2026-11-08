"""Detalle por señal en memoria de sesión; el corpus original no se publica."""
from io import BytesIO
import hashlib
import pandas as pd
from src.risk.project_resolution import ASSIGNED_STATUSES, build_public_project_snapshot


def load_corpus_risk_details(payload: bytes, manifest: dict, catalog: dict, scope: dict) -> pd.DataFrame:
    if len(payload) > 5_000_000 or hashlib.sha256(payload).hexdigest() != manifest['sha256']:
        raise ValueError('El archivo no corresponde a la línea base aprobada. Cargue el CSV original sin editarlo.')
    frame = pd.read_csv(BytesIO(payload), encoding='utf-8-sig')
    if len(frame) != manifest['rows'] or frame.item_id.isna().any() or frame.item_id.duplicated().any():
        raise ValueError('El archivo tiene registros incompletos o duplicados.')
    calculated = build_public_project_snapshot(frame, catalog)
    if calculated['assignment']['signals_assigned_single_project'] != manifest['assigned_rows']:
        raise ValueError('Las asignaciones del archivo no concilian con la línea base.')
    if sum(p['profile']['signals_scored'] for p in calculated['projects']) != manifest['scored_rows']:
        raise ValueError('Las puntuaciones del archivo no concilian con la línea base.')
    for expected in scope['projects']:
        actual = next(p for p in calculated['projects'] if p['project_id'] == expected['project_id'])
        for key in ['signals_total', 'signals_scored', 'signals_pending', 'global_pird']:
            if actual['profile'][key] != expected['profile'][key]:
                raise ValueError('El detalle y el perfil publicado no corresponden a la misma versión.')
    return frame


def select_project_risk_details(frame: pd.DataFrame, project_id: str) -> pd.DataFrame:
    """Excluye asignaciones ambiguas/multiproyecto incluso si contienen el ID activo."""
    if frame.empty:
        return frame.copy()
    required = {'project_id', 'project_assignment_status', 'item_id'}
    if not required.issubset(frame.columns):
        raise ValueError('El detalle no tiene asignaciones de proyecto verificables.')
    return frame.loc[(frame.project_id == project_id) &
                     frame.project_assignment_status.isin(ASSIGNED_STATUSES)].copy()


def filter_risk_details(frame: pd.DataFrame, categories=None, levels=None, status='Todas', query='') -> pd.DataFrame:
    selected = frame.copy()
    if categories is not None:
        selected = selected[selected.calibrated_category.isin(categories)]
    if levels is not None:
        selected = selected[selected.pird_level.isin(levels)]
    if status == 'Puntuadas':
        selected = selected[selected.pird_status == 'CALCULADO']
    elif status == 'Pendientes':
        selected = selected[selected.pird_status != 'CALCULADO']
    if query.strip():
        fields = [c for c in ['item_id', 'title', 'statement', 'evidence_quote', 'source_filename'] if c in selected]
        mask = selected[fields].fillna('').astype(str).apply(
            lambda column: column.str.contains(query.strip(), case=False, regex=False)).any(axis=1)
        selected = selected[mask]
    return selected.sort_values(['pird', 'item_id'], ascending=[False, True], na_position='last')
