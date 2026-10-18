"""Add high-temperature property controls and matched generalized-smearing pairs."""

import copy
import hashlib
import json

from campaign import ROOT, SYSTEMS, input_text

path = ROOT / "manifest.json"
manifest = json.loads(path.read_text())
names = {case["name"] for case in manifest["cases"]}
cases = []
for original in manifest["cases"]:
    if original["group"] not in ("finite-difference", "dynamics", "optimization"):
        continue
    case = copy.deepcopy(original)
    case["temperature"] = 3000
    case["mesh"] = [3, 2, 1]
    case["name"] += "-thermal"
    case["group"] = "thermal-properties"
    cases.append(case)
reference = next(case for case in cases if case["name"] == "al-force-reference-thermal")
cases.append(dict(reference, name="al-force-reference-thermal-diag", method="DIAG"))
for smearing in ("GAUSSIAN", "METHFESSEL_PAXTON", "MARZARI_VANDERBILT"):
    for method in ("CG", "DIAG"):
        cases.append(dict(SYSTEMS["Al"], element="Al", method=method,
                          name=f"al-{smearing.lower()}-{method.lower()}", group="general-smearing",
                          smearing=smearing, smear_extra="SIGMA 0.01"))
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
