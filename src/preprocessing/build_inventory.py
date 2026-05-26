from pathlib import Path
import re
import pandas as pd

RAW_DIR = Path("data/raw")
TEXT_DIR = Path("data/processed/text")
OUT = Path("data/evaluation/inventario_corpus.csv")
OUT.parent.mkdir(parents=True, exist_ok=True)

RISK_TERMS = {
    "retraso": ["retraso", "atraso", "demora", "vencido", "vencimiento", "plazo"],
    "incumplimiento": ["incumplimiento", "incumplir", "no cumplimiento", "incumple"],
    "compromiso": ["compromiso", "pendiente", "responsable"],
    "observacion": ["observación", "observaciones", "hallazgo", "alerta", "requerimiento"],
    "ans": ["ans", "acuerdo de nivel", "nivel de servicio"],
}

def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(name).stem) + ".txt"

def detect_type(filename: str) -> str:
    lower = filename.lower()
    if "acta" in lower or "review" in lower:
        return "Acta"
    if "comunicado" in lower:
        return "Comunicado"
    if "informe" in lower:
        return "Informe"
    if "concepto" in lower:
        return "Concepto"
    return "Otro"

def main():
    rows = []
    for raw in sorted(RAW_DIR.rglob("*")):
        if raw.suffix.lower() not in [".pdf", ".docx"]:
            continue
        txt_path = TEXT_DIR / safe_name(raw.name)
        text = txt_path.read_text(encoding="utf-8", errors="ignore") if txt_path.exists() else ""
        words = re.findall(r"\b\w+\b", text.lower())
        counts = {k: sum(text.lower().count(t) for t in terms) for k, terms in RISK_TERMS.items()}
        rows.append({
            "documento": raw.name,
            "extension": raw.suffix.lower().replace(".", ""),
            "tipo_documental": detect_type(raw.name),
            "tamano_kb": round(raw.stat().st_size/1024, 1),
            "palabras_extraidas": len(words),
            "posible_escaneado": len(text.strip()) < 100,
            **{f"{k}_terms": v for k, v in counts.items()},
            "score_senales_inicial": sum(counts.values()),
            "estado_limpieza": "texto_extraido" if txt_path.exists() else "pendiente",
        })
    pd.DataFrame(rows).to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"Inventario creado en {OUT}")

if __name__ == "__main__":
    main()
