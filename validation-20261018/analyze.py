"""Derive publication tables from archived inputs and unmodified CP2K outputs."""

import json
from pathlib import Path
import re
import statistics

import numpy as np

from campaign import ROOT, NUMBER, collect

# Match the conversion constants in this CP2K source's common/physcon.F.
BOHR_A = 0.52917720859
HA_J = 2 * 10973731.568527 * 6.62606896e-34 * 299792458
HA_PER_BOHR3_BAR = HA_J / (BOHR_A * 1e-10)**3 / 1e5


def trajectory_statistics(values):
    trajectory = np.asarray(values, dtype=float)
    if trajectory.ndim != 2 or trajectory.shape[1] != 7 or not np.all(np.isfinite(trajectory)):
        raise ValueError("Expected seven finite columns in the CP2K energy file")
    if np.any(np.diff(trajectory[:, 1]) < 0):
        raise ValueError("MD times are not monotone")
    _, indices = np.unique(trajectory[:, 1], return_index=True)
    duplicate_count = len(trajectory) - len(indices)
    if duplicate_count:
        raise ValueError("Repeated times in a trajectory without an MD restart")
    if len(trajectory) < 2:
        raise ValueError("A drift fit requires two distinct MD times")
    time_fs, energy = trajectory[:, 1], trajectory[:, 5]
    drift = float(np.polyfit(time_fs - time_fs.mean(), energy - energy[0], 1)[0])
    return dict(samples=len(energy), time_fs=float(time_fs[-1] - time_fs[0]),
                repeated_identical_samples=duplicate_count,
                conserved_energy_range_Ha=float(np.ptp(energy)),
                endpoint_change_Ha=float(energy[-1] - energy[0]),
                least_squares_drift_Ha_per_fs=drift)


def analyze():
    collect()
    manifest = json.loads((ROOT / "manifest.json").read_text())
    cases = {c["name"]: c for c in manifest["cases"]}
    recorded = json.loads((ROOT / "results.json").read_text())
    raw = [r for r in recorded if r.get("launcher_valid")]
    first = {r["case"]: r for r in raw if r["repetition"] == 1}
    rows = []
    for case in manifest["cases"]:
        samples = [r for r in raw if r["case"] == case["name"]]
        if not samples:
            continue
        valid = [r for r in samples if r["normal_end"] and r["scf_converged"] and r["returncode"] == 0]
        item = dict(case=case["name"], group=case["group"], attempts=len(samples),
                    converged=len(valid), method=case.get("method"),
                    temperature_K=case.get("temperature"), mesh=case.get("mesh"))
        item["first_returncode"] = samples[0]["returncode"]
        item["last_scf_iteration"] = samples[0].get("last_scf_iteration")
        item["last_scf_residual"] = samples[0].get("last_scf_residual")
        item["iteration_limit_reached"] = samples[0]["iteration_limit_reached"]
        item["stopping_status"] = ("converged" if valid else
                                   "wall-time limit" if samples[0]["returncode"] == 124 else
                                   "SCF limit" if samples[0]["iteration_limit_reached"] else
                                   "program error")
        target_spin = re.search(r"FIXED_MAGNETIC_MOMENT\s+(" + NUMBER + ")", case.get("smear_extra", ""))
        requested_spin = None
        if target_spin:
            setting = float(target_spin[1])
            item["spin_constraint"] = "fixed" if setting >= 0 else ("initial-integer" if setting == -1 else "free")
            if setting >= 0:
                requested_spin = setting
            elif setting == -1:
                requested_spin = float(case.get("multiplicity", 3) - 1)
        item["requested_spin_difference"] = requested_spin
        item["source_configuration"] = case.get("source_configuration", "upstream")
        if valid:
            times = [r["cp2k_time_s"] for r in valid if r.get("cp2k_time_s") is not None]
            item.update(free_energy_Ha=valid[0]["free_energy_Ha"],
                        minus_TS_Ha=valid[0]["minus_TS_Ha"],
                        objective_correction_Ha=valid[0]["objective_correction_Ha"],
                        steps=[r["converged_steps"] for r in valid],
                        electron_count=valid[0].get("electron_count_grid"),
                        mo_count=valid[0]["last_mo_count"], ao_count=valid[0]["ao_count"],
                        kpoint_count=valid[0]["kpoint_count"],
                        full_ks_subspace_rebuilds=[r["full_ks_subspace_rebuilds"] for r in valid],
                        free_energy_range_Ha=max(r["free_energy_Ha"] for r in valid)
                                             - min(r["free_energy_Ha"] for r in valid),
                        integrated_spin=valid[0].get("integrated_spin"),
                        cp2k_times_s=times, median_cp2k_time_s=statistics.median(times) if times else None)
            if requested_spin is not None and item["integrated_spin"] is not None:
                item["spin_constraint_error"] = item["integrated_spin"] - requested_spin
                item["spin_constraint_satisfied"] = abs(item["spin_constraint_error"]) < 1e-6
        rows.append(item)
    pairs = []
    row_by_name = {r["case"]: r for r in rows}
    for row in rows:
        name = row["case"]
        if (not row.get("free_energy_Ha") or cases[name].get("method") == "DIAG"
                or row.get("spin_constraint_satisfied") is False):
            continue
        reference = None
        if name == "al-auto":
            reference = "al-reduced-diag" if "al-reduced-diag" in first else "al-base-diag"
        if row["group"] in {"options", "preconditioners", "ablation", "symmetry"}:
            reference = "al-base-diag"
        if name == "al-gamma":
            reference = "al-explicit-gamma"
        for old in ("-cg", "-lbfgs", "-ot"):
            candidate = name.replace(old, "-diag")
            if candidate != name and candidate in first:
                reference = candidate
                break
        if reference is None and name == "al-force-reference-thermal":
            reference = name + "-diag"
        if (reference in first and first[reference]["normal_end"]
                and first[reference]["scf_converged"] and first[reference]["returncode"] == 0
                and row_by_name[reference].get("spin_constraint_satisfied") is not False
                and first[reference].get("free_energy_Ha") is not None):
            ref = first[reference]
            pairs.append(dict(case=name, reference=reference,
                              delta_free_energy_Ha=row["free_energy_Ha"] - ref["free_energy_Ha"],
                              delta_minus_TS_Ha=(row["minus_TS_Ha"] - ref["minus_TS_Ha"]
                                                 if row["minus_TS_Ha"] is not None and ref["minus_TS_Ha"] is not None else None),
                              delta_objective_correction_Ha=(row["objective_correction_Ha"] - ref["objective_correction_Ha"]
                                                              if row["objective_correction_Ha"] is not None and ref["objective_correction_Ha"] is not None else None),
                              delta_spin=(row["integrated_spin"] - ref["integrated_spin"]
                                          if row["integrated_spin"] is not None and ref["integrated_spin"] is not None
                                          else None),
                              delta_electron_count=(row["electron_count"] - ref["electron_count_grid"]
                                                    if row["electron_count"] is not None and ref.get("electron_count_grid") is not None
                                                    else None)))
    force_checks, stress_checks, dynamics, interrupted_dynamics = [], [], [], []
    for suffix in ("", "-thermal"):
        base = first.get("al-force-reference" + suffix)
        if not base or not base["normal_end"] or not base["scf_converged"] or not base.get("force_rows_Ha_per_bohr"):
            continue
        for step in (0.001, 0.0005):
            minus = first.get(f"al-displacement-{step}--1{suffix}", {})
            plus = first.get(f"al-displacement-{step}-+1{suffix}", {})
            if not all(r.get("normal_end") and r.get("scf_converged") and r.get("returncode") == 0
                       and r.get("free_energy_Ha") is not None for r in (minus, plus)):
                continue
            numerical = -(plus["free_energy_Ha"] - minus["free_energy_Ha"]) / (2 * step / BOHR_A)
            analytical = base["force_rows_Ha_per_bohr"][1][0]
            force_checks.append(dict(case=base["case"], step_A=step,
                                     analytical_Ha_per_bohr=analytical,
                                     numerical_Ha_per_bohr=numerical,
                                     absolute_error_Ha_per_bohr=abs(analytical - numerical)))
        volume = abs(np.linalg.det(cases[base["case"]]["cell"])) / BOHR_A**3
        for i, j in ((0, 0), (1, 1), (2, 2), (0, 1), (0, 2), (1, 2)):
            minus = first.get(f"al-strain-{i}{j}--1{suffix}", {})
            plus = first.get(f"al-strain-{i}{j}-+1{suffix}", {})
            if not all(r.get("normal_end") and r.get("scf_converged") and r.get("returncode") == 0
                       and r.get("free_energy_Ha") is not None for r in (minus, plus)):
                continue
            numerical = -(plus["free_energy_Ha"] - minus["free_energy_Ha"]) / (2e-4 * volume)
            analytical = base["stress_bar"][i][j] / HA_PER_BOHR3_BAR
            stress_checks.append(dict(case=base["case"], component=[i, j], step=1e-4,
                                      analytical_Ha_per_bohr3=analytical,
                                      numerical_Ha_per_bohr3=numerical,
                                      absolute_error_Ha_per_bohr3=abs(analytical - numerical)))
    for row in first.values():
        trajectory = row.get("md_energy_rows")
        if trajectory and row["normal_end"] and row["scf_converged"] and row["returncode"] == 0:
            dynamics.append(dict(case=row["case"], **trajectory_statistics(trajectory),
                                 temperature_K=cases[row["case"]]["temperature"],
                                 method=cases[row["case"]]["method"],
                                 eps_scf=cases[row["case"]].get("eps_scf", 1e-6),
                                 added_mos=cases[row["case"]].get("added_mos", -1)))
        elif cases[row["case"]].get("run_type") == "MD":
            description = cases[row["case"]]
            interrupted_dynamics.append(dict(
                case=row["case"], temperature_K=description["temperature"],
                method=description["method"], timestep_fs=description["timestep_fs"],
                added_mos=description.get("added_mos", -1),
                completed_time_fs=trajectory[-1][1] if trajectory else 0.0,
                requested_time_fs=description["timestep_fs"]*description["md_steps"],
                returncode=row["returncode"], normal_end=row["normal_end"],
                stopping_status=("Time limit" if row["returncode"] == 124 else
                                 "SCF limit" if row["iteration_limit_reached"] else "Program error"),
                last_scf_residual=row.get("last_scf_residual"),
                last_scf_iteration=row.get("last_scf_iteration")))
    summary = dict(cases=rows, pairs=pairs, force_checks=force_checks,
                   stress_checks=stress_checks, dynamics=dynamics,
                   interrupted_dynamics=interrupted_dynamics,
                   attempts=len(raw), completed=sum(r["normal_end"] for r in raw),
                   rejected_launcher_attempts=len(recorded) - len(raw),
                   scf_converged=sum(r["normal_end"] and r["scf_converged"] for r in raw))
    summary["optimization"] = [dict(
        case=name, run_type=cases[name]["run_type"], temperature_K=cases[name]["temperature"],
        nuclear_steps=record["last_nuclear_step"], converged=record["geometry_converged"],
        step_limit_reached=record["nuclear_step_limit_reached"],
        returncode=record["returncode"], scf_solves=len(record["converged_steps"]))
        for name, record in first.items() if cases[name].get("run_type") in {"GEO_OPT", "CELL_OPT"}]
    planned = {c["name"] for c in manifest["cases"]
               if not (c.get("element") == "Ni" and c.get("added_mos") != "-1 -1"
                       and c["group"] != "variational-subspace")}
    summary["planned_first_attempts"] = len(planned)
    summary["pending_first_attempts"] = sorted(planned - first.keys())
    (ROOT / "analysis.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "cases"}, indent=2))


if __name__ == "__main__":
    analyze()
