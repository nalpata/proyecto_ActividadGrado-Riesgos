"""Validador automático de candidatos a riesgo con evidencia documental.

Procesa los candidatos agrupados por chunk para reducir llamadas, conserva un
checkpoint reanudable y evalúa las decisiones contra las etiquetas humanas
disponibles sin utilizarlas dentro del prompt.
"""

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
VALID_CATEGORIES = [
    "Contractual", "Cronograma", "Calidad", "Operación", "Despliegues",
    "Gobierno del Proyecto", "Financiero", "Seguridad", "Otro",
]
ERROR_TYPES = [
    "HECHO_CONSUMADO", "COMPROMISO_NORMAL", "ACCION_CORRECTIVA",
    "CONTEXTO_SIN_RIESGO", "EVIDENCIA_INSUFICIENTE", "INFERENCIA_EXCESIVA",
    "DUPLICADO", "OTRO", "NO_APLICA",
]


def parse_json(raw: str | None) -> dict:
    if not raw:
        return {}
    text = raw.strip().replace("```json", "").replace("```", "").strip()
    try:
        result = json.loads(text)
        return result if isinstance(result, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return {}
        try:
            result = json.loads(match.group(0))
            return result if isinstance(result, dict) else {}
        except json.JSONDecodeError:
            return {}


def normalize_binary(value):
    if pd.isna(value) or str(value).strip() == "":
        return pd.NA
    value = str(value).strip().lower()
    if value in {"1", "1.0", "si", "sí", "true", "valido", "válido"}:
        return 1
    if value in {"0", "0.0", "no", "false", "invalido", "inválido"}:
        return 0
    return pd.NA


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\W+", " ", text).strip()


def build_prompt(chunk_text: str, candidates: pd.DataFrame) -> str:
    compact = []
    for _, row in candidates.iterrows():
        compact.append({
            "risk_id": row["risk_id"],
            "risk_name": row["risk_name"],
            "risk_category": row["risk_category"],
            "risk_description": row["risk_description"],
            "evidence": row["evidence"],
        })
    return f"""Actúa como validador independiente de riesgos en interventoría y aseguramiento técnico de proyectos tecnológicos.

Evalúa cada candidato únicamente contra el fragmento documental. No uses conocimiento externo y no inventes hechos.

Definición operacional para vigilancia documental:
- Riesgo o señal válida: condición incierta, amenaza, incumplimiento, desviación, vulnerabilidad, bloqueo, pendiente crítico o problema documentado que sea relevante para vigilar objetivos, plazo, costo, calidad, operación, seguridad, gobierno o contrato.
- Una desviación o problema ya ocurrido puede aceptarse como señal de riesgo cuando evidencia deterioro, exposición, recurrencia, falta de cierre o necesidad de seguimiento. No exijas que el fragmento formule literalmente una consecuencia futura.
- Un hecho completamente cerrado, neutral y sin valor para la vigilancia se rechaza.
- Un compromiso, solicitud, recomendación o acción correctiva no es por sí mismo un riesgo; sin embargo, puede evidenciar una señal válida cuando revela una deficiencia, pendiente, vulnerabilidad, incumplimiento o condición adversa subyacente.
- La descripción debe estar respaldada por el fragmento. Si exige supuestos no presentes, se rechaza.
- Evalúa la validez y la categoría; no cambies severidad ni probabilidad.

Categorías permitidas: {', '.join(VALID_CATEGORIES)}.
Tipos de error permitidos para candidatos rechazados: {', '.join(ERROR_TYPES[:-1])}.
Para candidatos aceptados usa error_type = "NO_APLICA".

Devuelve SOLO un objeto JSON válido con esta estructura:
{{
  "validations": [
    {{
      "risk_id": "identificador recibido",
      "is_valid_risk": 0,
      "evidence_sufficient": 0,
      "corrected_category": "categoría permitida",
      "category_is_correct": 0,
      "event_status": "FUTURO_INCIERTO|PROBLEMA_CON_EXPOSICION_PENDIENTE|HECHO_CERRADO|ACCION_O_COMPROMISO|INDETERMINADO",
      "error_type": "tipo permitido",
      "confidence": 0.0,
      "justification": "máximo 35 palabras, basada en el fragmento"
    }}
  ]
}}

Reglas de formato:
- is_valid_risk, evidence_sufficient y category_is_correct deben ser 0 o 1.
- confidence debe estar entre 0 y 1 y representa tu certeza sobre la clasificación tomada, no la probabilidad de que el candidato sea válido. Una decisión de rechazo muy segura debe tener confidence alto, por ejemplo 0.9.
- Debe existir exactamente una validación por cada risk_id recibido.

FRAGMENTO DOCUMENTAL:
{str(chunk_text)[:6000]}

CANDIDATOS:
{json.dumps(compact, ensure_ascii=False)}""".strip()


def call_model(client, prompt: str, retries: int = 3) -> str:
    for attempt in range(1, retries + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": "Valida riesgos documentales y responde únicamente JSON válido."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content or "{}"
        except Exception:
            if attempt == retries:
                raise
            time.sleep(2 ** attempt)
    return "{}"


def sanitize_validation(item: dict, original: pd.Series) -> dict:
    def binary(name):
        return 1 if str(item.get(name, "0")).lower() in {"1", "true"} else 0

    category = str(item.get("corrected_category", original["risk_category"])).strip()
    if category not in VALID_CATEGORIES:
        category = original["risk_category"] if original["risk_category"] in VALID_CATEGORIES else "Otro"
    error_type = str(item.get("error_type", "OTRO")).strip().upper()
    if error_type not in ERROR_TYPES:
        error_type = "OTRO"
    try:
        confidence = min(1.0, max(0.0, float(item.get("confidence", 0))))
    except (TypeError, ValueError):
        confidence = 0.0
    is_valid = binary("is_valid_risk")
    if is_valid:
        error_type = "NO_APLICA"
    return {
        "risk_id": original["risk_id"],
        "validator_is_valid": is_valid,
        "validator_evidence_sufficient": binary("evidence_sufficient"),
        "validator_corrected_category": category,
        "validator_category_is_correct": binary("category_is_correct"),
        "validator_event_status": str(item.get("event_status", "INDETERMINADO")).strip(),
        "validator_error_type": error_type,
        "validator_confidence": confidence,
        "validator_justification": str(item.get("justification", "")).strip(),
    }


def compute_metrics(results: pd.DataFrame) -> dict:
    if "riesgo_valido_manual" not in results.columns:
        return {"labeled_records": 0, "message": "No hay etiquetas humanas."}
    labels = results["riesgo_valido_manual"].map(normalize_binary)
    evaluated = results[labels.notna()].copy()
    evaluated["human_label"] = labels[labels.notna()].astype(int)
    if evaluated.empty:
        return {"labeled_records": 0, "message": "No hay etiquetas humanas diligenciadas."}
    y = evaluated["human_label"]
    p = evaluated["validator_is_valid"].astype(int)
    tp = int(((y == 1) & (p == 1)).sum())
    tn = int(((y == 0) & (p == 0)).sum())
    fp = int(((y == 0) & (p == 1)).sum())
    fn = int(((y == 1) & (p == 0)).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "labeled_records": int(len(evaluated)), "human_valid": int((y == 1).sum()),
        "human_invalid": int((y == 0).sum()), "true_positives": tp, "true_negatives": tn,
        "false_positives": fp, "false_negatives": fn, "precision": round(precision, 4),
        "recall": round(recall, 4), "f1": round(f1, 4),
        "accuracy": round((tp + tn) / len(evaluated), 4),
        "warning": "La muestra contiene pocos negativos; completar la muestra dirigida antes de concluir desempeño.",
    }


def select_review_sample(results: pd.DataFrame, size: int = 35) -> tuple[pd.DataFrame, pd.DataFrame]:
    labeled = results["riesgo_valido_manual"].map(normalize_binary)
    results = results.copy()
    results["human_label_normalized"] = labeled
    results["model_human_disagreement"] = (
        labeled.notna() & (labeled.astype("Int64") != results["validator_is_valid"].astype("Int64"))
    ).astype(int)
    unlabeled = results[labeled.isna()].copy()
    chosen = []
    # 15 rechazos de mayor confianza: necesarios para enriquecer la clase negativa.
    rejected = unlabeled[unlabeled["validator_is_valid"] == 0].sort_values("validator_confidence", ascending=False)
    chosen.extend(rejected.head(15).index.tolist())
    # 10 decisiones de menor confianza, sin repetir.
    uncertain = unlabeled.sort_values("validator_confidence", ascending=True)
    for idx in uncertain.index:
        if idx not in chosen:
            chosen.append(idx)
        if len(chosen) >= 25:
            break
    # 10 aceptados de control, distribuidos por categoría cuando sea posible.
    accepted = unlabeled[unlabeled["validator_is_valid"] == 1].sort_values(["risk_category", "validator_confidence"])
    for _, group in accepted.groupby("risk_category", sort=True):
        for idx in group.head(2).index:
            if idx not in chosen:
                chosen.append(idx)
            if len(chosen) >= size:
                break
        if len(chosen) >= size:
            break
    if len(chosen) < size:
        for idx in unlabeled.index:
            if idx not in chosen:
                chosen.append(idx)
            if len(chosen) >= size:
                break
    key = results.loc[chosen[:size]].copy()
    key["control_humano_valido"] = ""
    key["control_humano_categoria_correcta"] = ""
    key["control_humano_comentario"] = ""
    blind_columns = [
        "risk_id", "source_doc_id", "source_filename", "source_page", "source_chunk_id",
        "risk_name", "risk_category", "risk_description", "evidence", "recommended_action",
        "control_humano_valido", "control_humano_categoria_correcta", "control_humano_comentario",
    ]
    return key[blind_columns].copy(), key


def validate(input_xlsx: Path, chunks_path: Path, output_dir: Path, sample_size: int = 35) -> dict:
    from openai import OpenAI

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Falta OPENAI_API_KEY.")
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = output_dir / "validator_checkpoint.jsonl"
    candidates = pd.read_excel(input_xlsx, sheet_name="Revision")
    chunks = pd.read_parquet(chunks_path)
    chunk_map = chunks.set_index("chunk_id")["chunk_text"].to_dict()
    client = OpenAI()
    validations = []
    logs = []

    for number, (chunk_id, group) in enumerate(candidates.groupby("source_chunk_id", sort=True), start=1):
        print(f"[{number}/{candidates['source_chunk_id'].nunique()}] {chunk_id}: {len(group)} candidatos", flush=True)
        prompt = build_prompt(chunk_map.get(chunk_id, ""), group)
        try:
            raw = call_model(client, prompt)
            parsed = parse_json(raw).get("validations", [])
            parsed_by_id = {str(x.get("risk_id")): x for x in parsed if isinstance(x, dict)}
            for _, row in group.iterrows():
                validations.append(sanitize_validation(parsed_by_id.get(str(row["risk_id"]), {}), row))
            log = {"source_chunk_id": chunk_id, "status": "ok", "candidate_count": len(group), "returned_count": len(parsed), "raw_response": raw}
        except Exception as exc:
            for _, row in group.iterrows():
                validations.append(sanitize_validation({}, row))
            log = {"source_chunk_id": chunk_id, "status": "error", "candidate_count": len(group), "returned_count": 0, "raw_response": str(exc)}
        logs.append(log)
        with checkpoint_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(log, ensure_ascii=False) + "\n")
        time.sleep(0.3)

    validation_df = pd.DataFrame(validations)
    results = candidates.merge(validation_df, on="risk_id", how="left", validate="one_to_one")
    # Marca duplicados textuales como señal separada, sin alterar la decisión del validador.
    results["possible_duplicate"] = results.duplicated(
        subset=["source_chunk_id", "risk_category", "risk_description"], keep=False
    ).astype(int)
    metrics = compute_metrics(results)
    blind_sample, sample_key = select_review_sample(results, sample_size)
    logs_df = pd.DataFrame(logs)
    results.to_csv(output_dir / "risk_validation_results.csv", index=False, encoding="utf-8-sig")
    results.to_excel(output_dir / "risk_validation_results.xlsx", index=False)
    blind_sample.to_excel(output_dir / "validation_review_sample_blind.xlsx", index=False)
    sample_key.to_excel(output_dir / "validation_review_sample_key.xlsx", index=False)
    logs_df.to_csv(output_dir / "validation_log.csv", index=False, encoding="utf-8-sig")
    (output_dir / "validator_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    metadata = {
        "model": MODEL, "temperature": 0.0, "candidates": int(len(results)),
        "chunks_evaluated": int(results["source_chunk_id"].nunique()),
        "api_errors": int((logs_df["status"] == "error").sum()), "review_sample_size": int(len(blind_sample)),
    }
    (output_dir / "validator_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"metadata": metadata, "metrics": metrics}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-xlsx", required=True, type=Path)
    parser.add_argument("--chunks", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--sample-size", type=int, default=35)
    args = parser.parse_args()
    print(json.dumps(validate(args.input_xlsx, args.chunks, args.output_dir, args.sample_size), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
