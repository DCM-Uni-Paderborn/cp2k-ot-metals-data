"""Check deposited integrity and numerical evidence, not coauthor approval."""

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
checksums = json.loads((ROOT / "SHA256SUMS.json").read_text())
for name, expected in checksums.items():
    path = ROOT / name
    assert path.is_file(), f"Missing archive member: {name}"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, name
model = json.loads((ROOT / "derivative-results.json").read_text())
for key in ("number_error", "constant_energy_gauge_error",
            "projector_trace_response_error", "basis_gauge_cancellation_error",
            "schur_symmetry_error"):
    assert model[key] < 1e-12, key
assert model["coupled_curvature_error"] < 2e-6
for column, tolerance in ((1, 2e-8), (2, 2e-7), (3, 2e-8)):
    assert min(row[column] for row in model["finite_difference_scan"]) < tolerance
campaign = ROOT / "validation-20261018"
manifest = json.loads((campaign / "manifest.json").read_text())
case_by_name = {case["name"]: case for case in manifest["cases"]}
for case in manifest["cases"]:
    path = campaign / "inputs" / case["name"] / "input.inp"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == case["input_sha256"], case["name"]
for name, expected in manifest["data_sha256"].items():
    assert hashlib.sha256((campaign / "data" / name).read_bytes()).hexdigest() == expected, name
for record in (campaign / "runs").glob("*/*/result.json"):
    result = json.loads(record.read_text())
    assert result["launcher_valid"] and result["actual_mpi_ranks"] == result["ranks"], record
    assert hashlib.sha256((record.parent / "input.inp").read_bytes()).hexdigest() == \
        case_by_name[result["case"]]["input_sha256"], record
    assert result["binary_sha256"] in {
        config["binary_sha256"] for config in manifest["executable_configurations"].values()
    }, record
    if result["normal_end"]:
        assert (record.parent / "output.out").is_file(), record
        assert "PROGRAM ENDED AT" in (record.parent / "output.out").read_text(errors="replace")
analysis = json.loads((campaign / "analysis.json").read_text())
assert analysis["completed"] <= analysis["attempts"]
assert not analysis["pending_first_attempts"], "The planned campaign is not complete"
assert len(analysis["force_checks"]) == 4
assert len(analysis["stress_checks"]) == 12
assert len(analysis["dynamics"]) == 8
assert len(analysis["interrupted_dynamics"]) == 6
assert analysis["rejected_launcher_attempts"] == 0
for row in analysis["cases"]:
    if row.get("spin_constraint_satisfied") is False:
        assert not any(pair["case"] == row["case"] for pair in analysis["pairs"]), row["case"]
negative = next(row for row in analysis["pairs"]
                if row["case"] == "al-no-occupation-preconditioner")
assert negative["delta_free_energy_Ha"] > 1e-3, "Do not hide the inequivalent endpoint"
coverage = json.loads((ROOT / "coverage.json").read_text())
supplement = ROOT / "stationarity-20261019"
audit = json.loads((supplement / "analysis.json").read_text())
assert len(audit) == 11
for prefix in ("", "larger", "recovery"):
    directory = supplement / prefix
    local_manifest = json.loads((directory / "manifest.json").read_text())
    configuration = local_manifest["executable_configuration"]
    assert (directory / configuration["source_patch"]).is_file()
    local_cases = {case["name"]: case for case in local_manifest["cases"]}
    for name, expected in local_manifest["data_sha256"].items():
        assert hashlib.sha256((directory / "data" / name).read_bytes()).hexdigest() == expected
    for path in (directory / "runs").glob("*/*/result.json"):
        result = json.loads(path.read_text())
        assert result["normal_end"] and result["scf_converged"], path
        assert result["actual_mpi_ranks"] == result["ranks"] == 2 and result["launcher_valid"]
        assert result["binary_sha256"] == configuration["binary_sha256"]
        assert hashlib.sha256((path.parent / "input.inp").read_bytes()).hexdigest() == \
            local_cases[result["case"]]["input_sha256"]
by_name = {(row["cohort"], row["case"]): row for row in audit}
assert by_name["baseline", "al-off"]["canonical_endpoint_checks"][-1]["frozen_gap_Ha"] > 1e-3
assert by_name["recovery", "al-off"]["canonical_endpoint_checks"][-1]["frozen_gap_Ha"] < 1e-7
assert abs(by_name["larger", "al-eight-cg"]["free_energy_error_Ha"]) < 1e-8
for name in ("al-on", "cu-on", "al-small-off"):
    assert by_name["recovery", name]["free_energy_change_from_baseline_Ha"] == 0.0
    assert by_name["recovery", name]["steps_change_from_baseline"] == 0
for ranks in (1, 2):
    text = (supplement / f"recovery/provenance/unit-np{ranks}.out").read_text()
    assert float(re.search(r"Canonical density metrics error:\s+(\S+)", text)[1]) < 1e-13
print(json.dumps(dict(integrity="passed", files=len(checksums),
                      matrix_checks="passed", campaign_cases=len(manifest["cases"]),
                      retained_attempts=analysis["attempts"], stationarity_controls=len(audit),
                      publication_ready=coverage["publication_ready"]), indent=2))
