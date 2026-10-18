"""Create fast physical constraint checks and separately identified corrected Ni cases."""

import hashlib
import json

from campaign import ROOT, SYSTEMS, input_text

manifest = json.loads((ROOT / "manifest.json").read_text())
known = {c["name"] for c in manifest["cases"]}
base = dict(SYSTEMS["Al"], element="Al", spin=True, multiplicity=2, mesh=[2, 1, 1],
            basis="SZV-MOLOPT-SR-GTH-q3", potential="GTH-PADE-q3", functional="PADE",
            cutoff=40, temperature=1000, eps_scf=1e-7, added_mos="-1 -1")
cases = []
for moment, label in ((-100, "common"), (-1, "integer"), (0, "zero"), (0.5, "fractional")):
    for method in ("CG", "DIAG"):
        cases.append(dict(base, name=f"al-spin-{label}-{method.lower()}", group="spin-probes",
                          method=method, smear_extra=f"FIXED_MAGNETIC_MOMENT {moment}"))
for method in ("CG", "DIAG"):
    cases.append(dict(SYSTEMS["Ni"], element="Ni", method=method, added_mos="-1 -1",
                      name=f"ni-fixed-moment-corrected-{method.lower()}", group="spin-probes",
                      smear_extra="FIXED_MAGNETIC_MOMENT 1.0"))
for case in cases:
    if case["name"] in known:
        continue
    directory = ROOT / "inputs" / case["name"]
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "input.inp").write_text(input_text(case))
    case["input_sha256"] = hashlib.sha256((directory / "input.inp").read_bytes()).hexdigest()
    case["source_configuration"] = "spin-constraint-correction"
    manifest["cases"].append(case)
(ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
