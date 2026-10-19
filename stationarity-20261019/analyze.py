"""Validate provenance and summarize the independent stationarity controls."""

import hashlib
import json
from pathlib import Path
import re

root = Path(__file__).resolve().parent
number = r"[-+]?\d*\.?\d+(?:[EeDd][-+]?\d+)?"
records = []
for cohort, directory in (("baseline", root), ("larger", root / "larger"),
                           ("recovery", root / "recovery")):
    manifest = json.loads((directory / "manifest.json").read_text())
    cases = {case["name"]: case for case in manifest["cases"]}
    for path in sorted((directory / "runs").glob("*/*/result.json")):
        record = json.loads(path.read_text())
        case = cases[record["case"]]
        assert record["actual_mpi_ranks"] == record["ranks"] == 2, path
        assert record["launcher_valid"], path
        assert hashlib.sha256((path.parent / "input.inp").read_bytes()).hexdigest() == case["input_sha256"], path
        output = (path.parent / "output.out").read_text()
        metrics = re.findall(r"canonical density residual, frozen free-energy drop, commutator:\s*(" +
                             number + r")\s+(" + number + r")\s+(" + number + r")", output)
        ao = re.findall(r"Number of orbital functions:\s+(\d+)", output)
        if ao:
            record["total_ao_count"] = int(ao[-1])
        record["cohort"] = cohort
        record["canonical_endpoint_checks"] = [dict(
            density_residual=float(item[0]), frozen_gap_Ha=float(item[1]),
            commutator_Ha=float(item[2])) for item in metrics]
        record["input_sha256"] = case["input_sha256"]
        records.append(record)

by_name = {(item["cohort"], item["case"]): item for item in records}
for case in ("al-on", "al-off", "cu-on", "al-small-off"):
    original = by_name.get(("baseline", case))
    corrected = by_name.get(("recovery", case))
    if original and corrected and corrected["normal_end"]:
        assert original["input_sha256"] == corrected["input_sha256"]
        corrected["free_energy_change_from_baseline_Ha"] = corrected["free_energy_Ha"] - original["free_energy_Ha"]
        corrected["steps_change_from_baseline"] = sum(corrected["converged_steps"]) - sum(original["converged_steps"])
larger = by_name.get(("larger", "al-eight-cg"))
reference = by_name.get(("larger", "al-eight-diag"))
if larger and reference:
    assert larger["total_ao_count"] == reference["total_ao_count"] == 104
    assert larger["last_mo_count"] == reference["last_mo_count"] == 16
    larger["free_energy_error_Ha"] = larger["free_energy_Ha"] - reference["free_energy_Ha"]

(root / "analysis.json").write_text(json.dumps(records, indent=2) + "\n")
for record in records:
    print(record["cohort"], record["case"], record["converged_steps"],
          record["free_energy_Ha"], record["canonical_endpoint_checks"])
