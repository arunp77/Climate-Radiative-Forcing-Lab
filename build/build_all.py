"""Regenerate every derived artefact: processed data, web tables, validation report.

Run from the repository root with the project virtualenv:  python build/build_all.py

Not included (slow or needs a download; run by hand when the physics changes): build_spectra.py, run_fair.py,
stratospheric_adjustment.py, halocarbon_check.py, cloud_sensitivity.py.
"""
import runpy
from pathlib import Path

here = Path(__file__).resolve().parent
for script in ("extract_ar6_concentrations.py", "export_web_data.py", "build_metrics.py", "build_observations.py", "validation_report.py", "build_docs.py"):
    print(f"--- {script}")
    runpy.run_path(str(here / script), run_name="__main__")
