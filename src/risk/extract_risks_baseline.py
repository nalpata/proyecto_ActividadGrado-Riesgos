"""Reconstruye el baseline de extracción de riesgos del notebook 09.

Mantiene modelo, prompt, temperatura, selección y scoring del experimento de
junio. Guarda checkpoints por chunk para no perder una ejecución interrumpida.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path

import pandas as pd


MODEL = "gpt-4o-mini"
VALID_CATEGORIES = [
    "Contractual", "Cronograma", "Calidad", "Operación", "Despliegues",
    "Gobierno del Proyecto", "Financiero", "Seguridad", "Otro",
]
VALID_LEVELS = ["Baja", "Media", "Alta"]
RISK_KEYWORDS = [
    "riesgo", "incumplimiento", "retraso", "demora", "vencido", "vencimiento",
    "no cumple", "no cumplimiento", "pendiente", "atraso", "desviación", "desviacion",
    "ans", "sla", "compromiso", "hallazgo", "observación", "observacion", "calidad",
    "despliegue", "cierre", "entrega", "entregable", "contrato", "proveedor",
    "interventoría", "interventoria", "plan de cierre",
]


def build_prompt(row: pd.Series) -> str:
    text = str(row["chunk_text"])[:4500]
    return f"""Eres un experto en interventoría, aseguramiento técnico y gestión de riesgos en proyectos de tecnología.

Analiza el siguiente fragmento documental y extrae únicamente riesgos explícitos o razonablemente inferibles a partir del texto.

No inventes riesgos. Si no hay riesgo, devuelve una lista vacía: []

Categorías válidas:
- Contractual
- Cronograma
- Calidad
- Operación
- Despliegues
- Gobierno del Proyecto
- Financiero
- Seguridad
- Otro

Niveles válidos para severity y probability:
- Baja
- Media
- Alta

Devuelve SOLO JSON válido, sin markdown, sin explicación adicional.

Formato esperado:
[
  {{
    "risk_name": "nombre corto del riesgo",
    "risk_category": "una categoría válida",
    "severity": "Baja|Media|Alta",
    "probability": "Baja|Media|Alta",
    "risk_description": "descripción breve del riesgo",
    "evidence": "frase textual o resumen fiel del fragmento que soporta el riesgo",
    "recommended_action": "acción sugerida para mitigar o hacer seguimiento"
  }}
]

Metadatos del fragmento:
- doc_id: {row['doc_id']}
- archivo: {row['filename']}
- tipo_documento: {row['tipo_documento']}
- página: {row['page']}
- chunk_id: {row['chunk_id']}

Fragmento documental:
{text}""".strip()


def parse_json_list(raw_text: str | None) -> list[dict]:
    if not raw_text:
        return []
    text = raw_text.strip().replace("```json", "").replace("```", "").strip()
    candidates = [text]
    match = re.search(r"\[.*\]", text, flags=re.DOTALL)
    if match and match.group(0) != text:
        candidates.append(match.group(0))
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, list):
                return [x for x in parsed if isinstance(x, dict)]
            if isinstance(parsed, dict):
                return [parsed]
        except json.JSONDecodeError:
            continue
    return []


def select_chunks(chunks: pd.DataFrame, max_chunks: int) -> pd.DataFrame:
    required = {"doc_id", "filename", "tipo_documento", "page", "chunk_id", "chunk_text"}
    missing = required - set(chunks.columns)
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {sorted(missing)}")
    pattern = "|".join(re.escape(k) for k in RISK_KEYWORDS)
    selected = chunks[chunks["chunk_text"].str.lower().str.contains(pattern, na=False)].copy()
    return selected.sort_values(["tipo_documento", "doc_id", "page", "chunk_id"]).head(max_chunks)


def call_model(client, prompt: str, retries: int = 3) -> str:
    for attempt in range(1, retries + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": "Extrae riesgos documentales en JSON válido. No inventes información."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
            )
            return response.choices[0].message.content or "[]"
        except Exception:
            if attempt == retries:
                raise
            time.sleep(2 ** attempt)
    return "[]"


def extract(chunks_path: Path, output_dir: Path, max_chunks: int = 60) -> dict:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Falta OPENAI_API_KEY en las variables de entorno.")
    from openai import OpenAI

    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = output_dir / "checkpoint_respuestas.jsonl"
    chunks = pd.read_parquet(chunks_path)
    selected = select_chunks(chunks, max_chunks)
    client = OpenAI()
    risk_records: list[dict] = []
    log_records: list[dict] = []

    for number, (_, row) in enumerate(selected.iterrows(), start=1):
        print(f"[{number}/{len(selected)}] {row['chunk_id']} - {row['filename']}", flush=True)
        record = {"doc_id": row["doc_id"], "filename": row["filename"], "chunk_id": row["chunk_id"]}
        try:
            raw = call_model(client, build_prompt(row))
            parsed = parse_json_list(raw)
            record.update({"status": "ok", "num_risks": len(parsed), "raw_response": raw})
            for risk in parsed:
                risk_records.append({
                    "source_doc_id": row["doc_id"],
                    "source_filename": row["filename"],
                    "source_tipo_documento": row["tipo_documento"],
                    "source_page": row["page"],
                    "source_chunk_id": row["chunk_id"],
                    "risk_name": str(risk.get("risk_name", "")).strip(),
                    "risk_category": risk.get("risk_category") if risk.get("risk_category") in VALID_CATEGORIES else "Otro",
                    "severity": risk.get("severity") if risk.get("severity") in VALID_LEVELS else "Media",
                    "probability": risk.get("probability") if risk.get("probability") in VALID_LEVELS else "Media",
                    "risk_description": str(risk.get("risk_description", "")).strip(),
                    "evidence": str(risk.get("evidence", "")).strip(),
                    "recommended_action": str(risk.get("recommended_action", "")).strip(),
                    "llm_model": MODEL,
                })
        except Exception as exc:
            record.update({"status": "error", "num_risks": 0, "raw_response": str(exc)})
        log_records.append(record)
        with checkpoint.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        time.sleep(0.3)

    risks = pd.DataFrame(risk_records)
    logs = pd.DataFrame(log_records)
    if not risks.empty:
        risks = risks.drop_duplicates(
            subset=["source_chunk_id", "risk_name", "risk_category", "evidence"]
        ).reset_index(drop=True)
        risks.insert(0, "risk_id", [f"RISK_{i:04d}" for i in range(1, len(risks) + 1)])
        score = {"Baja": 1, "Media": 2, "Alta": 3}
        risks["severity_score"] = risks["severity"].map(score).fillna(2)
        risks["probability_score"] = risks["probability"].map(score).fillna(2)
        risks["risk_score"] = risks["severity_score"] * risks["probability_score"]

    evaluation = risks.copy()
    for column in ("riesgo_valido_manual", "categoria_correcta_manual", "comentario_evaluador"):
        evaluation[column] = ""
    risks.to_csv(output_dir / "riesgos_extraidos.csv", index=False, encoding="utf-8-sig")
    risks.to_excel(output_dir / "riesgos_extraidos.xlsx", index=False)
    evaluation.to_excel(output_dir / "riesgos_evaluation_template.xlsx", index=False)
    logs.to_csv(output_dir / "riesgos_extraccion_log.csv", index=False, encoding="utf-8-sig")
    metadata = {
        "modelo": MODEL,
        "temperatura": 0.0,
        "max_chunks": max_chunks,
        "chunks_candidatos_procesados": int(len(selected)),
        "riesgos_unicos_extraidos": int(len(risks)),
        "errores_api": int((logs["status"] == "error").sum()) if not logs.empty else 0,
    }
    (output_dir / "metadata_ejecucion.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunks", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--max-chunks", type=int, default=60)
    args = parser.parse_args()
    print(json.dumps(extract(args.chunks, args.output_dir, args.max_chunks), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
