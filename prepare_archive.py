"""Record the verification environment and checksums after inspecting a data update."""

import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path

ROOT = Path(__file__).resolve().parent
environment = {
    "experiment": "independent finite-matrix validation, not CP2K",
    "python": platform.python_version(),
    "system": platform.system(),
    "release": platform.release(),
    "machine": platform.machine(),
    "packages": {name: importlib.metadata.version(name)
                 for name in ("numpy", "scipy", "matplotlib")},
}
(ROOT / "environment.json").write_text(json.dumps(environment, indent=2) + "\n")
names = ["README.txt", "coverage.json", "environment.json", "requirements.txt",
         "verify_derivatives.py", "verify_archive.py", "prepare_archive.py",
         "recorded-results.json", "derivative-results.json", "derivative-plot.tex",
         "convergence-plot.tex", "supplement-readme.txt"]
checksums = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
             for name in names}
(ROOT / "SHA256SUMS.json").write_text(json.dumps(checksums, indent=2) + "\n")
print(f"Recorded {len(checksums)} archive checksums.")
