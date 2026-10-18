"""Add displacement, homogeneous strain, restart and propagation comparisons."""

import copy
import hashlib
import json
from pathlib import Path

from campaign import ROOT, SYSTEMS, input_text

manifest_path = ROOT / "manifest.json"
manifest = json.loads(manifest_path.read_text())
names = {case["name"] for case in manifest["cases"]}
base = dict(SYSTEMS["Al"], element="Al", method="DIIS", eps_scf=1e-8,
            preconditioner="FULL_ALL", mesh=[3, 1, 1], max_scf=500,
            cell=[[0, 4.05, 4.05], [2.025, 0, 2.025], [2.025, 2.025, 0]],
            coordinates=[[0, 0, 0], [0.025, 2.025, 2.025]])
cases = [dict(base, name="al-force-reference", group="finite-difference")]
for step in (0.001, 0.0005):
    for sign in (-1, 1):
        displaced = copy.deepcopy(base)
        displaced["coordinates"][1][0] += sign * step
        cases.append(dict(displaced, name=f"al-displacement-{step}-{sign:+d}",
                          group="finite-difference", displacement_A=sign * step))
for first, second in ((0, 0), (1, 1), (2, 2), (0, 1), (0, 2), (1, 2)):
    for sign in (-1, 1):
        step = 1e-4 * sign
        deformation = [[float(i == j) for j in range(3)] for i in range(3)]
        deformation[first][second] += step if first == second else step / 2
        if first != second:
            deformation[second][first] += step / 2
        strained = copy.deepcopy(base)
        for key in ("cell", "coordinates"):
            strained[key] = [[sum(row[k] * deformation[k][j] for k in range(3))
                              for j in range(3)] for row in base[key]]
        cases.append(dict(strained, name=f"al-strain-{first}{second}-{sign:+d}",
                          group="finite-difference", strain=[first, second, step]))

for timestep, steps in ((0.25, 40), (0.125, 80)):
    motion = f"""&MOTION
  &MD
    ENSEMBLE NVE
    STEPS {steps}
    TIMESTEP {timestep}
  &END MD
  &PRINT
    &RESTART OFF
    &END RESTART
    &RESTART_HISTORY OFF
    &END RESTART_HISTORY
    &TRAJECTORY
      &EACH
        MD 1
      &END EACH
    &END TRAJECTORY
  &END PRINT
&END MOTION"""
    velocity = "    &VELOCITY\n      0.00010 0 0\n      -0.00010 0 0\n    &END VELOCITY\n"
    cases.append(dict(base, name=f"al-md-{timestep}", group="dynamics", run_type="MD",
                      motion=motion, velocity=velocity, timestep_fs=timestep, md_steps=steps))

for run_type, setting in (("GEO_OPT", "MAX_FORCE 1.0E-4"),
                          ("CELL_OPT", "KEEP_ANGLES TRUE")):
    motion = f"""&MOTION
  &{run_type}
    OPTIMIZER BFGS
    MAX_ITER 15
    {setting}
  &END {run_type}
  &PRINT
    &RESTART OFF
    &END RESTART
    &RESTART_HISTORY OFF
    &END RESTART_HISTORY
  &END PRINT
&END MOTION"""
    cases.append(dict(base, name=f"al-{run_type.lower()}", group="optimization",
                      run_type=run_type, motion=motion))

for method in ("CG", "DIIS", "LBFGS"):
    original = dict(SYSTEMS["Al"], element="Al", method=method, mesh=[3, 1, 1],
                    name=f"al-restart-write-{method.lower()}", group="restart", write_restart=True)
    cases.append(original)
    read = dict(original, name=f"al-restart-read-{method.lower()}", write_restart=False,
                restart_file="initial.kp", depends_on=original["name"])
    cases.append(read)

for case in cases:
    if case["name"] in names:
        continue
    directory = ROOT / "inputs" / case["name"]
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "input.inp").write_text(input_text(case))
    case["input_sha256"] = hashlib.sha256((directory / "input.inp").read_bytes()).hexdigest()
    manifest["cases"].append(case)
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
print(f"Manifest now contains {len(manifest['cases'])} cases.")
