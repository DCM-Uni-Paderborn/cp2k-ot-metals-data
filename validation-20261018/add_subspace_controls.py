"""Exercise a genuine orbital complement with tail-controlled virtual spaces."""

import hashlib
import json

from campaign import ROOT, SYSTEMS, input_text

manifest = json.loads((ROOT / "manifest.json").read_text())
known = {c["name"] for c in manifest["cases"]}
for element in ("Al", "Cu", "Ni"):
    for method in ("CG", "LBFGS", "DIAG"):
        if element == "Al" and method == "CG":
            continue  # The existing al-auto calculation supplies this exact input.
        name = f"{element.lower()}-reduced-{method.lower()}"
        if name in known:
            continue
        case = dict(SYSTEMS[element], element=element, method=method, added_mos="AUTO",
                    name=name, group="variational-subspace")
        path = ROOT / "inputs" / name / "input.inp"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(input_text(case))
        case["input_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest["cases"].append(case)
(ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
