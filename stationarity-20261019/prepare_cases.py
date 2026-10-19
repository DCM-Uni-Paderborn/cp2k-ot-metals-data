"""Prepare independent endpoint checks without altering the released campaign."""

import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
ORIGINAL = next(path for path in (
    ROOT.parent / "validation-20261018",
    ROOT.parent / "cp2k-ot-metals-data/validation-20261018",
) if path.exists())
original = json.loads((ORIGINAL / "manifest.json").read_text())
cases = {case["name"]: case for case in original["cases"]}
selected = []
for name, source in (("al-off", "al-no-occupation-preconditioner"),
                     ("al-on", "al-base-cg"), ("cu-on", "cu-base-cg"),
                     ("ni-on", "ni-reduced-lbfgs"), ("al-small-off", "al-no-occupation-preconditioner")):
    case = dict(cases[source], name=name, group="stationarity")
    text = (ORIGINAL / "inputs" / source / "input.inp").read_text()
    if name == "al-small-off":
        case.update(basis="SZV-MOLOPT-SR-GTH", cutoff=80, mesh=[3, 1, 1])
        text = text.replace("DZVP-MOLOPT-SR-GTH", "SZV-MOLOPT-SR-GTH")
        text = text.replace("CUTOFF 300", "CUTOFF 80")
        text = text.replace("MONKHORST-PACK 3 3 3", "MONKHORST-PACK 3 1 1")
    path = ROOT / "inputs" / name / "input.inp"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    case["input_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    selected.append(case)
(ROOT / "data").mkdir(exist_ok=True)
for name in original["data_sha256"]:
    shutil.copy2(ORIGINAL / "data" / name, ROOT / "data" / name)
(ROOT / "manifest.json").write_text(json.dumps(dict(
    date="2026-10-19", source_revision=original["source_revision"],
    data_sha256=original["data_sha256"], cases=selected), indent=2) + "\n")
