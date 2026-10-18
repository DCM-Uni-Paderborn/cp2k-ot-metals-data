"""Prepare canonical-cell symmetry and constrained-spin comparisons."""

import hashlib
import json
import math

from campaign import ROOT, SYSTEMS, input_text

path = ROOT / "manifest.json"
manifest = json.loads(path.read_text())
names = {case["name"] for case in manifest["cases"]}
al = dict(SYSTEMS["Al"], element="Al", method="CG", eps_scf=1e-7)
length = al["a"] / math.sqrt(2)
al["cell"] = [[length, 0, 0], [length / 2, length * math.sqrt(3) / 2, 0],
              [length / 2, length / (2 * math.sqrt(3)), length * math.sqrt(2 / 3)]]
cases = [dict(al, name="al-canonical-reduced", group="symmetry-controls"),
         dict(al, name="al-canonical-full", group="symmetry-controls", full_grid=True)]
for method in ("CG", "DIAG"):
    cases.append(dict(SYSTEMS["Ni"], element="Ni", method=method, added_mos="-1 -1",
                      name=f"ni-fixed-moment-{method.lower()}", group="symmetry-controls",
                      smear_extra="FIXED_MAGNETIC_MOMENT 1.0"))
for case in cases:
    if case["name"] in names:
        continue
    directory = ROOT / "inputs" / case["name"]
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "input.inp").write_text(input_text(case))
    case["input_sha256"] = hashlib.sha256((directory / "input.inp").read_bytes()).hexdigest()
    manifest["cases"].append(case)
path.write_text(json.dumps(manifest, indent=2) + "\n")
print(f"Manifest now contains {len(manifest['cases'])} cases.")
