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
lattice = records["lattice_fft_application"]
assert lattice["mpi_ranks"] == [2, 4]
assert lattice["omp_threads_per_rank"] == 14
assert lattice["repetitions_per_implementation_and_configuration"] == 5
assert lattice["ot_steps_all_runs"] == 36
assert [round(100 * (old - new) / old, 1) for old, new in zip(
    lattice["gathered_kernel_median_s"], lattice["distributed_kernel_median_s"])
    ] == [29.2, 35.9]
for variant in ("gathered", "distributed"):
    assert len(lattice[f"{variant}_kernel_median_s"]) == 2
    assert len(lattice[f"{variant}_total_median_s"]) == 2
    for kernel, total in zip(lattice[f"{variant}_kernel_median_s"],
                             lattice[f"{variant}_total_median_s"]):
        assert 0 < kernel / total < 0.02
for key, tolerance in (("rks", 1e-14), ("roks", 1e-13)):
    pair = records["kpoint_symmetry"][key]
    difference = abs(pair["full_free_energy_Ha"] - pair["reduced_free_energy_Ha"])
    assert abs(difference - pair["absolute_difference_Ha_approx"]) < tolerance
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
