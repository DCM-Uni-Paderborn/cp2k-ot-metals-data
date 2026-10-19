"""Keep recovery-policy controls separate from the unmodified endpoint audit."""

import json
from pathlib import Path
import shutil

root = Path(__file__).resolve().parent
target = root / "recovery"
manifest = json.loads((root / "manifest.json").read_text())
manifest["cases"] = [case for case in manifest["cases"] if case["name"] != "ni-on"]
for case in manifest["cases"]:
    destination = target / "inputs" / case["name"]
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / "inputs" / case["name"] / "input.inp", destination / "input.inp")
shutil.copytree(root / "data", target / "data", dirs_exist_ok=True)
(target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
