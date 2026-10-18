"""Control electronic stopping accuracy independently of the physical trajectory."""

import hashlib
import json

from campaign import ROOT, input_text

manifest = json.loads((ROOT / "manifest.json").read_text())
known = {c["name"] for c in manifest["cases"]}
cases = []
for original in manifest["cases"]:
    if original.get("run_type") != "MD" or original.get("group") != "thermal-properties":
        continue
    name = original["name"] + "-eps7"
    if name in known:
        continue
    case = dict(original, name=name, group="motion-tolerance", added_mos="AUTO", eps_scf=1e-7)
    path = ROOT / "inputs" / name / "input.inp"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(input_text(case))
    case["input_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    cases.append(case)
manifest["cases"].extend(cases)
(ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
