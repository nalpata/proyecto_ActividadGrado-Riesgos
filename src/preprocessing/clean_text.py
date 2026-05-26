from pathlib import Path
import re
import unicodedata

IN_DIR = Path("data/processed/text")
OUT_DIR = Path("data/processed/clean_text")
OUT_DIR.mkdir(parents=True, exist_ok=True)

PATTERNS_TO_REMOVE = [
    r"Página\s+\d+\s+de\s+\d+",
    r"Page\s+\d+\s+of\s+\d+",
]

def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    for pattern in PATTERNS_TO_REMOVE:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def main():
    for file in IN_DIR.glob("*.txt"):
        cleaned = clean_text(file.read_text(encoding="utf-8", errors="ignore"))
        (OUT_DIR / file.name).write_text(cleaned, encoding="utf-8")
        print(f"OK limpio: {file.name}")

if __name__ == "__main__":
    main()
