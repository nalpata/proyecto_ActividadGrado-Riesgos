import json
from pathlib import Path
import pytest
from src.audit.notebook_runner import execute

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize("name", ["30_verificacion_cierre_noviembre_2026.ipynb", "31_reproduccion_enriquecimiento_contexto.ipynb"])
def test_verification_notebooks_execute_without_api(name, tmp_path):
    document=execute(ROOT/"notebooks"/name, tmp_path/name)
    assert document["metadata"]["verification"]["success"]
    assert all(cell["execution_count"] for cell in document["cells"] if cell["cell_type"]=="code")
    output=str(document)
    assert "error" not in [o["output_type"] for c in document["cells"] for o in c.get("outputs",[])]
    if name.startswith("30"):
        assert "SYNTHETIC_SOFTWARE_CONTROL" in output
    else:
        assert "Sin llamadas API" in output


def test_runner_records_failed_cell_and_raises(tmp_path):
    source=tmp_path/"bad.ipynb"
    source.write_text(json.dumps({"cells":[{"cell_type":"code","source":["raise ValueError('failure')"]}]}))
    target=tmp_path/"result.ipynb"
    with pytest.raises(ValueError, match="failure"):
        execute(source,target)
    assert not json.loads(target.read_text())["metadata"]["verification"]["success"]
