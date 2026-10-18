"""Test the same trajectories with a tail-controlled rather than full-AO MO space."""

import hashlib
import json

from campaign import ROOT, input_text

manifest = json.loads((ROOT / "manifest.json").read_text())
known = {c["name"] for c in manifest["cases"]}
cases = []
for original in manifest["cases"]:
    if original.get("run_type") != "MD" or original.get("group") not in ("dynamics", "thermal-properties"):
        continue
    name = original["name"] + "-adaptive"
    if name in known:
        continue
    case = dict(original, name=name, group="adaptive-dynamics", added_mos="AUTO")
    directory = ROOT / "inputs" / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "input.inp").write_text(input_text(case))
    case["input_sha256"] = hashlib.sha256((directory / "input.inp").read_bytes()).hexdigest()
    cases.append(case)
manifest["cases"].extend(cases)
(ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
