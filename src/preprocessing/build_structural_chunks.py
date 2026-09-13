"""Construye chunks más breves respetando párrafos, títulos, listas y páginas."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


NUMBERED_HEADING_RE = re.compile(r"^\d+(?:\.\d+)*\.?\s+\S+")
UPPER_HEADING_RE = re.compile(r"^[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\-/]{4,}$")
LIST_RE = re.compile(r"^(?:[-•*]|\(?[a-zA-Z0-9]+[.)])\s+")
SENTENCE_RE = re.compile(r"(?<=[.!?;:])\s+(?=[A-ZÁÉÍÓÚÑ0-9])")


def clean_text(text: str) -> str:
    text = (text or "").replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def is_heading(text: str) -> bool:
    value = text.strip()
    words = value.split()
    return 0 < len(words) <= 14 and bool(
        NUMBERED_HEADING_RE.match(value) or UPPER_HEADING_RE.match(value)
    )


def structural_units(text: str) -> list[tuple[str, str]]:
    """Devuelve unidades (sección, texto) sin perder límites de listas/títulos."""
    blocks = [clean_text(x) for x in re.split(r"\n\s*\n", clean_text(text)) if clean_text(x)]
    units: list[tuple[str, str]] = []
    section = ""
    for block in blocks:
        lines = [clean_text(x) for x in block.splitlines() if clean_text(x)]
        if len(lines) == 1 and is_heading(lines[0]):
            section = lines[0]
            continue
        current: list[str] = []
        for line in lines:
            if is_heading(line):
                if current:
                    units.append((section, " ".join(current)))
                    current = []
                section = line
            elif LIST_RE.match(line):
                if current:
                    units.append((section, " ".join(current)))
                current = [line]
            else:
                current.append(line)
        if current:
            units.append((section, " ".join(current)))
    return units or [("", clean_text(text))]


def split_long_unit(text: str, max_words: int) -> list[str]:
    sentences = [x.strip() for x in SENTENCE_RE.split(text) if x.strip()]
    if len(text.split()) <= max_words:
        return [text]
    parts, current = [], []
    for sentence in sentences:
        words = sentence.split()
        if len(words) > max_words:
            if current:
                parts.append(" ".join(current))
                current = []
            parts.extend(" ".join(words[i:i + max_words]) for i in range(0, len(words), max_words))
        elif current and len(current) + len(words) > max_words:
            parts.append(" ".join(current))
            current = words
        else:
            current.extend(words)
    if current:
        parts.append(" ".join(current))
    return parts


def pack_units(units: list[tuple[str, str]], target_words: int = 160,
               max_words: int = 210, min_words: int = 30) -> list[dict]:
    expanded = []
    for section, text in units:
        expanded.extend((section, part) for part in split_long_unit(text, max_words))

    chunks, current, current_section = [], [], ""
    for section, text in expanded:
        words = text.split()
        section_changed = bool(current and section and current_section and section != current_section)
        would_exceed = current and len(current) + len(words) > max_words
        target_reached = current and len(current) >= target_words
        if section_changed or would_exceed or target_reached:
            chunks.append({"section_title": current_section, "chunk_text": " ".join(current)})
            current = []
        if not current:
            current_section = section
        current.extend(words)
    if current:
        if chunks and len(current) < min_words and chunks[-1]["section_title"] == current_section:
            merged = (chunks[-1]["chunk_text"] + " " + " ".join(current)).split()
            if len(merged) <= max_words:
                chunks[-1]["chunk_text"] = " ".join(merged)
            else:
                chunks.append({"section_title": current_section, "chunk_text": " ".join(current)})
        else:
            chunks.append({"section_title": current_section, "chunk_text": " ".join(current)})
    return chunks


def extract_pages(path: Path, extension: str):
    if extension == ".pdf":
        import fitz
        doc = fitz.open(path)
        pages = [(i + 1, page.get_text("text")) for i, page in enumerate(doc)]
        doc.close()
        return pages
    if extension == ".docx":
        from docx import Document
        paragraphs = [p.text for p in Document(path).paragraphs if p.text.strip()]
        return [(1, "\n\n".join(paragraphs))]
    raise ValueError(f"Extensión no soportada: {extension}")


def build(inventory_path: Path, corpus_dir: Path, output_dir: Path,
          target_words: int = 160, max_words: int = 210, min_words: int = 30):
    inventory = pd.read_csv(inventory_path)
    rows, errors = [], []
    for item in inventory.to_dict(orient="records"):
        path = corpus_dir / str(item["filename"])
        counter = 1
        try:
            for page, text in extract_pages(path, str(item["extension"]).lower()):
                for chunk in pack_units(structural_units(text), target_words, max_words, min_words):
                    words = len(chunk["chunk_text"].split())
                    if words < min_words:
                        continue
                    rows.append({
                        "doc_id": item["doc_id"], "filename": item["filename"],
                        "tipo_documento": item["tipo_documento"], "page": page,
                        "chunk_id": f"{item['doc_id']}_SCHUNK_{counter:03d}",
                        "section_title": chunk["section_title"], "chunk_text": chunk["chunk_text"],
                        "chunk_size_words": words, "chunk_size_chars": len(chunk["chunk_text"]),
                        "chunking_strategy": "structural_paragraph_sentence",
                        "target_words": target_words, "max_words": max_words,
                    })
                    counter += 1
        except Exception as exc:
            errors.append({"doc_id": item["doc_id"], "filename": item["filename"], "error": str(exc)})
    output_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    frame.to_csv(output_dir / "chunks_structural.csv", index=False, encoding="utf-8-sig")
    try:
        frame.to_parquet(output_dir / "chunks_structural.parquet", index=False)
    except ImportError:
        # CSV remains the canonical portable output when no Parquet engine is installed.
        pass
    pd.DataFrame(errors, columns=["doc_id", "filename", "error"]).to_csv(
        output_dir / "structural_chunking_errors.csv", index=False
    )
    summary = {
        "documents": int(frame.doc_id.nunique()), "chunks": int(len(frame)),
        "mean_words": round(float(frame.chunk_size_words.mean()), 2),
        "median_words": round(float(frame.chunk_size_words.median()), 2),
        "max_words": int(frame.chunk_size_words.max()), "errors": len(errors),
    }
    print(summary)
    return frame, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--corpus-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--target-words", type=int, default=160)
    parser.add_argument("--max-words", type=int, default=210)
    parser.add_argument("--min-words", type=int, default=30)
    args = parser.parse_args()
    build(args.inventory, args.corpus_dir, args.output_dir, args.target_words, args.max_words, args.min_words)


if __name__ == "__main__":
    main()
