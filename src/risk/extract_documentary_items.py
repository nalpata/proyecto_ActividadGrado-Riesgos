"""Extrae y clasifica elementos documentales con evidencia textual verificable."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import unicodedata
from pathlib import Path

import pandas as pd


MODEL = "gpt-4o-mini"
EXTRACTION_VERSION = "v2"
ITEM_TYPES = [
    "RIESGO", "HECHO_OCURRIDO", "COMPROMISO", "ACCION_CORRECTIVA",
    "HALLAZGO", "INFORMACION_CONTEXTUAL",
]
CATEGORIES = [
    "Contractual", "Cronograma", "Calidad", "Operación", "Despliegues",
    "Gobierno del Proyecto", "Financiero", "Seguridad", "Otro", "No aplica",
]
EXPOSURE_STATUS = ["ABIERTA", "CERRADA", "INDETERMINADA", "NO_APLICA"]


RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "documentary_item_extraction",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item_type": {"type": "string", "enum": ITEM_TYPES},
                            "title": {"type": "string"},
                            "statement": {"type": "string"},
                            "evidence_quote": {"type": "string"},
                            "evidence_sufficient": {"type": "integer", "enum": [0, 1]},
                            "surveillance_candidate": {"type": "integer", "enum": [0, 1]},
                            "exposure_status": {"type": "string", "enum": EXPOSURE_STATUS},
                            "risk_category": {"type": "string", "enum": CATEGORIES},
                            "responsible": {"type": "string"},
                            "explicit_date": {"type": "string"},
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                            "justification": {"type": "string"},
                        },
                        "required": [
                            "item_type", "title", "statement", "evidence_quote", "evidence_sufficient",
                            "surveillance_candidate", "exposure_status", "risk_category",
                            "responsible", "explicit_date", "confidence", "justification",
                        ],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["items"],
            "additionalProperties": False,
        },
    },
}


def normalize_for_match(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return re.sub(r"\s+", " ", text).strip()


def evidence_is_verbatim(evidence: str, chunk_text: str) -> bool:
    evidence_norm = normalize_for_match(evidence).strip(" .,:;\"'“”")
    chunk_norm = normalize_for_match(chunk_text)
    return bool(evidence_norm) and evidence_norm in chunk_norm


def build_prompt(row: pd.Series) -> str:
    return f"""Actúa como analista documental de interventoría y gestión de proyectos tecnológicos.

Extrae de este fragmento un máximo de cuatro elementos sustantivos y atómicos. Clasifica cada uno por su función principal. No uses conocimiento externo, no completes vacíos y no inventes consecuencias, responsables, fechas ni acciones.

DEFINICIONES EXCLUYENTES:
- RIESGO: condición incierta o exposición que podría afectar objetivos, plazo, costo, calidad, operación, seguridad, gobierno o contrato.
- HECHO_OCURRIDO: evento, desviación o incumplimiento que ya sucedió. Puede seguir abierto, pero no debe reescribirse como posibilidad futura.
- COMPROMISO: obligación, entrega o actuación prometida o acordada, con o sin responsable o fecha.
- ACCION_CORRECTIVA: respuesta, mitigación, recomendación, solicitud o plan dirigido a corregir o reducir una condición adversa.
- HALLAZGO: observación, deficiencia, vulnerabilidad o no conformidad constatada, sin presentarse principalmente como evento ocurrido ni como posibilidad futura.
- INFORMACION_CONTEXTUAL: descripción neutral, estado administrativo, reunión, cifra o antecedente que no constituye por sí mismo ninguna clase anterior.

REGLAS:
1. Omite encabezados, firmas, nombres aislados, fechas de reunión, referencias a diapositivas, títulos de tabla y frases administrativas sin valor analítico.
2. Clasifica por lo que la frase documentalmente es. Futuro posible = RIESGO; evento ya ocurrido = HECHO_OCURRIDO; obligación prometida = COMPROMISO; medida para corregir = ACCION_CORRECTIVA; deficiencia constatada = HALLAZGO.
3. Una solicitud o verbo futuro como “validará”, “entregará” o “se realizará” suele ser COMPROMISO. Solo es ACCION_CORRECTIVA cuando el texto declara que busca corregir o mitigar una condición adversa explícita.
4. Una cifra, reunión o actividad realizada es INFORMACION_CONTEXTUAL si no expresa por sí misma una condición adversa, obligación o exposición.
5. surveillance_candidate = 1 únicamente para: RIESGO abierto; HECHO_OCURRIDO o HALLAZGO adverso y no resuelto; COMPROMISO explícitamente vencido, incumplido o crítico pendiente. Una acción correctiva, recomendación o compromiso normal vale 0; extrae por separado la condición adversa que sí requiera vigilancia.
6. Si el texto confirma cierre, solución o ausencia de pendientes, surveillance_candidate debe ser 0 y exposure_status = CERRADA.
7. evidence_quote debe ser una cita literal continua de máximo 45 palabras y debe contener suficiente información para demostrar statement sin depender de otra frase. evidence_sufficient = 1 solo cuando cumple ambas condiciones; en caso contrario no extraigas el elemento.
8. responsible y explicit_date deben quedar vacíos si no están explícitos.
9. risk_category es obligatoria para todas las clases excepto INFORMACION_CONTEXTUAL. Usa No aplica exclusivamente para contexto neutral.
10. confidence representa certeza sobre la clasificación, no gravedad ni probabilidad.
11. Evita duplicar afirmaciones. Si no existe ningún elemento sustantivo, devuelve items = [].

METADATOS:
- doc_id: {row['doc_id']}
- archivo: {row['filename']}
- tipo_documento: {row['tipo_documento']}
- página: {row['page']}
- chunk_id: {row['chunk_id']}

FRAGMENTO:
{str(row['chunk_text'])[:6500]}""".strip()


def parse_response(raw: str | None) -> list[dict]:
    if not raw:
        return []
    text = raw.strip().replace("```json", "").replace("```", "").strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return []
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []
    return [item for item in parsed.get("items", []) if isinstance(item, dict)] if isinstance(parsed, dict) else []


def sanitize_item(item: dict, row: pd.Series) -> dict | None:
    item_type = str(item.get("item_type", "")).strip().upper()
    if item_type not in ITEM_TYPES:
        return None
    evidence = str(item.get("evidence_quote", "")).strip()
    if item.get("evidence_sufficient") not in {1, True}:
        return None
    if len(evidence.split()) < 4 or not evidence_is_verbatim(evidence, str(row["chunk_text"])):
        return None
    category = str(item.get("risk_category", "No aplica")).strip()
    if category not in CATEGORIES:
        category = "Otro"
    if item_type != "INFORMACION_CONTEXTUAL" and category == "No aplica":
        category = "Otro"
    if item_type == "INFORMACION_CONTEXTUAL":
        category = "No aplica"
    status = str(item.get("exposure_status", "INDETERMINADA")).strip().upper()
    if status not in EXPOSURE_STATUS:
        status = "INDETERMINADA"
    try:
        confidence = min(1.0, max(0.0, float(item.get("confidence", 0))))
    except (TypeError, ValueError):
        confidence = 0.0
    return {
        "source_doc_id": row["doc_id"], "source_filename": row["filename"],
        "source_tipo_documento": row["tipo_documento"], "source_page": row["page"],
        "source_chunk_id": row["chunk_id"], "item_type": item_type,
        "title": str(item.get("title", "")).strip(),
        "statement": str(item.get("statement", "")).strip(),
        "evidence_quote": evidence, "evidence_verified": 1,
        "surveillance_candidate": 1 if item.get("surveillance_candidate") in {1, True} else 0,
        "exposure_status": status, "risk_category": category,
        "responsible": str(item.get("responsible", "")).strip(),
        "explicit_date": str(item.get("explicit_date", "")).strip(),
        "confidence": confidence,
        "justification": str(item.get("justification", "")).strip(),
        "llm_model": MODEL, "extraction_version": EXTRACTION_VERSION,
    }


def load_checkpoint(path: Path) -> tuple[set[str], list[dict], list[dict]]:
    completed, items, logs = set(), [], []
    if not path.exists():
        return completed, items, logs
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("status") == "ok":
            completed.add(str(record.get("source_chunk_id")))
            items.extend(record.get("items", []))
        logs.append({k: record.get(k) for k in ["source_chunk_id", "status", "returned_items", "accepted_items", "rejected_evidence"]})
    return completed, items, logs


def call_model(client, prompt: str, retries: int = 3):
    for attempt in range(1, retries + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": "Clasifica evidencia documental y responde únicamente con el JSON estructurado solicitado."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                response_format=RESPONSE_SCHEMA,
            )
            return response.choices[0].message.content or '{"items":[]}', response.usage
        except Exception:
            if attempt == retries:
                raise
            time.sleep(2 ** attempt)


def extract(chunks_path: Path, output_dir: Path) -> dict:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Falta OPENAI_API_KEY.")
    from openai import OpenAI

    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = output_dir / "documentary_extraction_checkpoint_v2.jsonl"
    chunks = pd.read_parquet(chunks_path).sort_values(["doc_id", "page", "chunk_id"])
    completed, records, prior_logs = load_checkpoint(checkpoint)
    client = OpenAI()
    logs = list(prior_logs)
    prompt_tokens = completion_tokens = 0
    started = time.perf_counter()

    pending = chunks[~chunks.chunk_id.astype(str).isin(completed)]
    for number, (_, row) in enumerate(pending.iterrows(), 1):
        print(f"[{number}/{len(pending)}] {row['chunk_id']}", flush=True)
        try:
            raw, usage = call_model(client, build_prompt(row))
            parsed = parse_response(raw)
            accepted = [x for x in (sanitize_item(item, row) for item in parsed) if x]
            record = {
                "source_chunk_id": row["chunk_id"], "status": "ok",
                "returned_items": len(parsed), "accepted_items": len(accepted),
                "rejected_evidence": len(parsed) - len(accepted), "items": accepted,
            }
            prompt_tokens += int(getattr(usage, "prompt_tokens", 0) or 0)
            completion_tokens += int(getattr(usage, "completion_tokens", 0) or 0)
            records.extend(accepted)
        except Exception as exc:
            record = {"source_chunk_id": row["chunk_id"], "status": "error", "returned_items": 0,
                      "accepted_items": 0, "rejected_evidence": 0, "items": [], "error": str(exc)}
        logs.append({k: record.get(k) for k in ["source_chunk_id", "status", "returned_items", "accepted_items", "rejected_evidence"]})
        with checkpoint.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    items = pd.DataFrame(records)
    if not items.empty:
        items = items.drop_duplicates(subset=["source_chunk_id", "item_type", "evidence_quote"]).reset_index(drop=True)
        items.insert(0, "item_id", [f"ITEM_{i:05d}" for i in range(1, len(items) + 1)])
    logs_df = pd.DataFrame(logs).drop_duplicates("source_chunk_id", keep="last")
    items.to_csv(output_dir / "documentary_items.csv", index=False, encoding="utf-8-sig")
    items.to_excel(output_dir / "documentary_items.xlsx", index=False)
    items[items.get("surveillance_candidate", pd.Series(dtype=int)) == 1].to_csv(
        output_dir / "surveillance_candidates.csv", index=False, encoding="utf-8-sig"
    )
    logs_df.to_csv(output_dir / "documentary_extraction_log.csv", index=False, encoding="utf-8-sig")
    metadata = {
        "model": MODEL, "extraction_version": EXTRACTION_VERSION,
        "chunks_total": int(len(chunks)), "chunks_completed": int((logs_df.status == "ok").sum()),
        "api_errors": int((logs_df.status == "error").sum()), "items": int(len(items)),
        "surveillance_candidates": int(items.surveillance_candidate.sum()) if not items.empty else 0,
        "rejected_nonverbatim_evidence": int(logs_df.rejected_evidence.fillna(0).sum()),
        "prompt_tokens_current_session": prompt_tokens,
        "completion_tokens_current_session": completion_tokens,
        "total_tokens_current_session": prompt_tokens + completion_tokens,
        "elapsed_seconds_current_session": round(time.perf_counter() - started, 3),
    }
    (output_dir / "documentary_extraction_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunks", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    extract(args.chunks, args.output_dir)


if __name__ == "__main__":
    main()
