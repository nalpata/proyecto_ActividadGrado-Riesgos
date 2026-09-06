"""Diagnóstico reproducible de falsos positivos en la extracción de riesgos.

El módulo no decide automáticamente si un riesgo es válido. Normaliza la revisión
humana, propone etiquetas preliminares y genera las tablas necesarias para el
análisis del Día 1.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd


VALID_LABEL_CANDIDATES = (
    "riesgo_valido_manual",
    "risk_valid_manual",
    "es_riesgo_manual",
    "valido_manual",
)

ERROR_TYPES = {
    "HECHO_CONSUMADO": "El texto describe un problema que ya ocurrió, sin formular exposición futura.",
    "COMPROMISO_NORMAL": "Se identificó como riesgo un compromiso o actividad normal sin señal de amenaza.",
    "ACCION_CORRECTIVA": "La extracción confundió una acción, recomendación o plan de mejora con un riesgo.",
    "CONTEXTO_SIN_RIESGO": "El fragmento es descriptivo y no contiene una condición de riesgo.",
    "EVIDENCIA_INSUFICIENTE": "La evidencia no soporta de forma verificable la descripción del riesgo.",
    "INFERENCIA_EXCESIVA": "El riesgo requiere supuestos que no están respaldados por el fragmento.",
    "DUPLICADO": "El mismo riesgo fue extraído varias veces de evidencia equivalente.",
    "OTRO": "La causa no corresponde a las categorías anteriores.",
}


def _normalize_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result.columns = [_normalize_name(c) for c in result.columns]
    return result


def read_table(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo de entrada: {path}")
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError("El archivo debe ser CSV, XLSX o XLS")


def find_valid_label(df: pd.DataFrame) -> str | None:
    return next((c for c in VALID_LABEL_CANDIDATES if c in df.columns), None)


def normalize_binary(series: pd.Series) -> pd.Series:
    mapping = {
        "1": 1, "si": 1, "sí": 1, "true": 1, "verdadero": 1, "valido": 1, "válido": 1,
        "0": 0, "no": 0, "false": 0, "falso": 0, "invalido": 0, "inválido": 0,
    }
    return series.map(lambda x: mapping.get(str(x).strip().lower()) if pd.notna(x) else pd.NA).astype("Int64")


def suggest_error_type(row: pd.Series) -> str:
    text = " ".join(str(row.get(c, "")) for c in ("risk_name", "risk_description", "evidence")).lower()
    if any(x in text for x in ("se recomienda", "se solicita", "plan de acción", "accion correctiva")):
        return "ACCION_CORRECTIVA"
    if any(x in text for x in ("se realizó", "ocurrió", "incumplió", "no entregó", "no se realizó")):
        return "HECHO_CONSUMADO"
    if any(x in text for x in ("compromiso", "actividad", "reunión", "seguimiento")):
        return "COMPROMISO_NORMAL"
    if len(str(row.get("evidence", "")).strip()) < 35:
        return "EVIDENCIA_INSUFICIENTE"
    return "REVISAR_MANUALMENTE"


def prepare_diagnostic(df: pd.DataFrame) -> tuple[pd.DataFrame, str | None]:
    result = normalize_columns(df)
    label_col = find_valid_label(result)
    if label_col:
        result[label_col] = normalize_binary(result[label_col])

    if "risk_id" not in result.columns:
        result.insert(0, "risk_id", [f"RISK_{i:04d}" for i in range(1, len(result) + 1)])

    result["tipo_error_sugerido"] = result.apply(suggest_error_type, axis=1)
    additions = {
        "tipo_error_manual": "",
        "causa_raiz_manual": "",
        "evidencia_suficiente_manual": "",
        "correccion_requerida_manual": "",
        "comentario_diagnostico_manual": "",
    }
    for column, default in additions.items():
        if column not in result.columns:
            result[column] = default
    return result, label_col


def build_summaries(df: pd.DataFrame, label_col: str | None) -> dict[str, pd.DataFrame | dict]:
    summaries: dict[str, pd.DataFrame | dict] = {}
    if label_col is None or df[label_col].notna().sum() == 0:
        summaries["metrics"] = {
            "total_registros": int(len(df)),
            "registros_etiquetados": 0,
            "mensaje": "Falta diligenciar la columna de validez manual.",
        }
        return summaries

    reviewed = df[df[label_col].notna()].copy()
    positives = int((reviewed[label_col] == 1).sum())
    false_positives = int((reviewed[label_col] == 0).sum())
    total = len(reviewed)
    summaries["metrics"] = {
        "total_registros": int(len(df)),
        "registros_etiquetados": int(total),
        "riesgos_validos": positives,
        "falsos_positivos": false_positives,
        "precision_extraccion": round(positives / total, 4) if total else None,
    }

    false_df = reviewed[reviewed[label_col] == 0].copy()
    summaries["false_positives"] = false_df
    if "risk_category" in false_df.columns:
        summaries["by_category"] = (
            false_df.groupby("risk_category", dropna=False).size()
            .reset_index(name="cantidad_falsos_positivos")
            .sort_values("cantidad_falsos_positivos", ascending=False)
        )
    if "source_filename" in false_df.columns:
        summaries["by_document"] = (
            false_df.groupby("source_filename", dropna=False).size()
            .reset_index(name="cantidad_falsos_positivos")
            .sort_values("cantidad_falsos_positivos", ascending=False)
        )
    if false_df["tipo_error_manual"].astype(str).str.strip().ne("").any():
        summaries["by_error_type"] = (
            false_df.assign(tipo_error_manual=false_df["tipo_error_manual"].replace("", pd.NA))
            .groupby("tipo_error_manual", dropna=False).size()
            .reset_index(name="cantidad")
            .sort_values("cantidad", ascending=False)
        )
    return summaries


def export_results(df: pd.DataFrame, summaries: dict, output_dir: str | Path) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_dir / "plantilla_diagnostico_falsos_positivos.csv", index=False, encoding="utf-8-sig")
    df.to_excel(output_dir / "plantilla_diagnostico_falsos_positivos.xlsx", index=False)

    metrics = summaries["metrics"]
    (output_dir / "metricas_baseline_extraccion.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for key, value in summaries.items():
        if isinstance(value, pd.DataFrame):
            value.to_csv(output_dir / f"{key}.csv", index=False, encoding="utf-8-sig")

    taxonomy = pd.DataFrame(
        [{"tipo_error": key, "definicion": value} for key, value in ERROR_TYPES.items()]
    )
    taxonomy.to_csv(output_dir / "taxonomia_falsos_positivos.csv", index=False, encoding="utf-8-sig")


def run(input_path: str | Path, output_dir: str | Path) -> dict:
    source = read_table(input_path)
    diagnostic, label_col = prepare_diagnostic(source)
    summaries = build_summaries(diagnostic, label_col)
    export_results(diagnostic, summaries, output_dir)
    return summaries["metrics"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="CSV/XLSX con todos los riesgos extraídos y su validación manual")
    parser.add_argument("--output-dir", default="data/evaluation/risk_validation/day_01")
    args = parser.parse_args()
    metrics = run(args.input, args.output_dir)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

