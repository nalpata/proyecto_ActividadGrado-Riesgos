"""Ejecuta celdas Python ordinarias; no emula IPython ni un kernel Jupyter."""
import argparse
from contextlib import redirect_stdout
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import traceback


def execute(notebook, output):
    notebook, output = Path(notebook).resolve(), Path(output).resolve()
    document = json.loads(notebook.read_text())
    namespace = {"__name__": "__main__", "__file__": str(notebook)}
    count = 0
    failure = None
    for cell in document["cells"]:
        if cell["cell_type"] != "code":
            continue
        count += 1
        source = "".join(cell["source"])
        cell.update(execution_count=count, outputs=[])
        stream = io.StringIO()
        try:
            with redirect_stdout(stream):
                exec(compile(source, f"{notebook.name}:cell{count}", "exec"), namespace)
        except Exception as exc:
            failure = exc
            cell["outputs"].append(dict(output_type="error", ename=type(exc).__name__,
                                        evalue=str(exc), traceback=traceback.format_exc().splitlines()))
        if stream.getvalue():
            cell["outputs"].insert(0, dict(output_type="stream", name="stdout", text=stream.getvalue().splitlines(True)))
        if failure:
            break
    document.setdefault("metadata", {})["verification"] = {
        "engine": "python_exec_no_ipython_kernel", "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "code_cells_executed": count, "success": failure is None,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, ensure_ascii=False, indent=1)+"\n")
    if failure:
        raise failure
    return document


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notebook", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    execute(args.notebook, args.output)
