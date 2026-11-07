"""Regenerate every derived artefact: processed data, web tables, validation report.

Run from the repository root with the project virtualenv:  python build/build_all.py
"""
import runpy
from pathlib import Path

here = Path(__file__).resolve().parent
for script in ("extract_ar6_concentrations.py", "export_web_data.py", "validation_report.py"):
    print(f"--- {script}")
    runpy.run_path(str(here / script), run_name="__main__")
