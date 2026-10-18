"""Compare an alternative product minimizer without changing the physical trajectory."""

import hashlib
import json

from campaign import ROOT, input_text

manifest = json.loads((ROOT / "manifest.json").read_text())
known = {c["name"] for c in manifest["cases"]}
cases = []
for original in manifest["cases"]:
    if original.get("run_type") != "MD" or original.get("group") != "thermal-properties":
        continue
    name = original["name"] + "-lbfgs"
    if name in known:
        continue
    case = dict(original, name=name, group="motion-minimizers", method="LBFGS", added_mos="AUTO")
    directory = ROOT / "inputs" / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "input.inp").write_text(input_text(case))
    case["input_sha256"] = hashlib.sha256((directory / "input.inp").read_bytes()).hexdigest()
    cases.append(case)
manifest["cases"].extend(cases)
(ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
