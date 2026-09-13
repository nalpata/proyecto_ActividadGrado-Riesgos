from src.preprocessing.build_structural_chunks import is_heading, pack_units, split_long_unit


def test_heading_detection():
    assert is_heading("5.2. Gestión de riesgos")
    assert is_heading("CONCLUSIONES")
    assert not is_heading("La interventoría informó un incumplimiento contractual.")


def test_long_unit_respects_maximum():
    text = " ".join([f"palabra{i}" for i in range(500)])
    parts = split_long_unit(text, 200)
    assert len(parts) == 3
    assert max(len(part.split()) for part in parts) <= 200


def test_pack_units_separates_sections():
    units = [("Riesgos", "riesgo " * 80), ("Compromisos", "compromiso " * 80)]
    chunks = pack_units(units, target_words=160, max_words=210, min_words=30)
    assert len(chunks) == 2
    assert chunks[0]["section_title"] == "Riesgos"
    assert chunks[1]["section_title"] == "Compromisos"
