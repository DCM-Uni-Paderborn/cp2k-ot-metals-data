"""Check deposited file integrity and evidence coverage, not publication readiness."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
checksums = json.loads((ROOT / "SHA256SUMS.json").read_text())
for name, expected in checksums.items():
    path = ROOT / name
    assert path.is_file(), f"Missing archive member: {name}"
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual == expected, f"Checksum mismatch: {name}"

coverage = json.loads((ROOT / "coverage.json").read_text())
records = json.loads((ROOT / "recorded-results.json").read_text())
assert set(coverage["electronic_structure_records"]["groups"]) == set(records) - {"description"}
model = json.loads((ROOT / "derivative-results.json").read_text())
for key in ("number_error", "constant_energy_gauge_error",
            "projector_trace_response_error", "basis_gauge_cancellation_error",
            "schur_symmetry_error"):
    assert model[key] < 1e-12, key
assert model["coupled_curvature_error"] < 2e-6
scan = model["finite_difference_scan"]
for column, tolerance in ((1, 2e-8), (2, 2e-7), (3, 2e-8)):
    assert min(row[column] for row in scan) < tolerance
print(json.dumps({"integrity": "passed", "files": len(checksums),
                  "matrix_checks": "passed",
                  "publication_ready": coverage["publication_ready"],
                  "electronic_structure": coverage["electronic_structure_records"]["status"]},
                 indent=2))
