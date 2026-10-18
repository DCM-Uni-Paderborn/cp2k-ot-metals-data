"""Generate, execute and summarize matched CP2K metallic-OT calculations."""

import argparse
import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parent
NUMBER = r"[-+]?\d+(?:\.\d*)?(?:[EeDd][-+]?\d+)?"


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


SYSTEMS = {
    "Al": dict(a=4.05, basis="DZVP-MOLOPT-SR-GTH", basis_file="BASIS_MOLOPT",
               potential="GTH-PBE-q3", functional="PBE", electrons=3,
               temperature=600, mesh=[3, 3, 3], cutoff=300, spin=False),
    "Cu": dict(a=3.615, basis="DZV-GTH-PADE", basis_file="BASIS_SET",
               potential="GTH-PBE-q11", functional="PBE", electrons=11,
               temperature=800, mesh=[2, 2, 2], cutoff=300, spin=False),
    "Ni": dict(a=3.52, basis="DZV-GTH-PADE-q10", basis_file="BASIS_SET",
               potential="GTH-PADE-q10", functional="PADE", electrons=10,
               temperature=1000, mesh=[3, 2, 1], cutoff=300, spin=True),
}


def input_text(case):
    element = case["element"]
    a = case["a"]
    lattice = case.get("cell", [[0, a / 2, a / 2], [a / 2, 0, a / 2], [a / 2, a / 2, 0]])
    coordinates = case.get("coordinates", [[0, 0, 0]])
    cell_text = "\n".join(f"      {label} " + " ".join(f"{x:.12f}" for x in row)
                          for label, row in zip("ABC", lattice))
    coord_text = "\n".join(f"      {element} " + " ".join(f"{x:.12f}" for x in row)
                           for row in coordinates)
    sampling = ""
    if not case.get("gamma", False):
        sampling = f"""    &KPOINTS
      SCHEME MONKHORST-PACK {' '.join(map(str, case['mesh']))}
      FULL_GRID {'ON' if case.get('full_grid', False) else 'OFF'}
      SYMMETRY ON
      WAVEFUNCTIONS COMPLEX
      PARALLEL_GROUP_SIZE 0
    &END KPOINTS
"""
    if case["method"] == "DIAG":
        solver = """      &DIAGONALIZATION
        ALGORITHM STANDARD
      &END DIAGONALIZATION
      &MIXING
        METHOD BROYDEN_MIXING
        ALPHA 0.1
        NBROYDEN 8
      &END MIXING"""
    else:
        solver = f"""      &OT
        ALGORITHM {case.get('algorithm', 'STRICT')}
        MINIMIZER {case['method']}
        PRECONDITIONER {case.get('preconditioner', 'FULL_SINGLE_INVERSE')}
        LINESEARCH 2PNT
        ROTATION
        ENERGIES
        OCCUPATION_PRECONDITIONER {'.TRUE.' if case.get('occupation_preconditioner', True) else '.FALSE.'}
      &END OT"""
    motion = case.get("motion", "")
    velocity = case.get("velocity", "")
    spin = f"    UKS TRUE\n    MULTIPLICITY {case.get('multiplicity', 3)}\n" if case["spin"] else ""
    if case.get("roks"):
        spin = "    ROKS TRUE\n    MULTIPLICITY 2\n"
    restart_file = case.get("restart_file")
    restart = f"    WFN_RESTART_FILE_NAME {restart_file}\n" if restart_file else ""
    guess = "RESTART" if restart_file else "ATOMIC"
    return f"""&GLOBAL
  PROJECT calculation
  RUN_TYPE {case.get('run_type', 'ENERGY_FORCE')}
  PRINT_LEVEL MEDIUM
  &TIMINGS
    THRESHOLD 0.0
  &END TIMINGS
&END GLOBAL
{motion}
&FORCE_EVAL
  METHOD QUICKSTEP
  STRESS_TENSOR ANALYTICAL
  &DFT
    BASIS_SET_FILE_NAME {case['basis_file']}
    POTENTIAL_FILE_NAME POTENTIAL
{spin}{restart}{sampling}    &MGRID
      CUTOFF {case['cutoff']}
      REL_CUTOFF 40
      COMMENSURATE
    &END MGRID
    &QS
      EPS_DEFAULT 1.0E-11
      EXTRAPOLATION ASPC
    &END QS
    &SCF
      ADDED_MOS {case.get('added_mos', -1)}
      EPS_SCF {case.get('eps_scf', 1e-6):.2E}
      MAX_SCF {case.get('max_scf', 400)}
      SCF_GUESS {guess}
{solver}
      &SMEAR
        METHOD {case.get('smearing', 'FERMI_DIRAC')}
        ELECTRONIC_TEMPERATURE {case['temperature']}
        {case.get('smear_extra', '')}
      &END SMEAR
      &PRINT
        &RESTART {'ON' if case.get('write_restart') else 'OFF'}
        &END RESTART
      &END PRINT
    &END SCF
    &XC
      &XC_FUNCTIONAL {case['functional']}
      &END XC_FUNCTIONAL
    &END XC
  &END DFT
  &PRINT
    &FORCES ON
    &END FORCES
    &STRESS_TENSOR ON
    &END STRESS_TENSOR
  &END PRINT
  &SUBSYS
    &CELL
{cell_text}
    &END CELL
    &COORD
{coord_text}
    &END COORD
{velocity}    &KIND {element}
      BASIS_SET {case['basis']}
      POTENTIAL {case['potential']}
    &END KIND
  &END SUBSYS
&END FORCE_EVAL
"""


def generate(source, phase):
    source = Path(source).resolve()
    cases = []
    for element, settings in SYSTEMS.items():
        for method in ("CG", "LBFGS", "DIAG"):
            case = dict(settings, element=element, method=method,
                        name=f"{element.lower()}-base-{method.lower()}", group="pilot")
            cases.append(case)
    if phase == "complete":
        originals = copy.deepcopy(cases)
        for case in originals:
            hot = dict(case, temperature=3000 if case["element"] == "Al" else 2000,
                       name=case["name"].replace("base", "hot"), group="temperature")
            cases.append(hot)
            dense = dict(case, mesh=[4, 4, 4] if case["element"] != "Ni" else [4, 3, 2],
                         name=case["name"].replace("base", "dense"), group="mesh")
            cases.append(dense)
        al = dict(SYSTEMS["Al"], element="Al", method="CG")
        for algorithm in ("STRICT", "IRAC"):
            for method in ("CG", "DIIS", "BROYDEN", "LBFGS"):
                cases.append(dict(al, name=f"al-{algorithm.lower()}-{method.lower()}",
                                  group="options", algorithm=algorithm, method=method))
        for preconditioner in ("FULL_KINETIC", "FULL_S_INVERSE", "FULL_ALL",
                               "FERMI_LOW_RANK", "FULL_ALL_COVARIANT"):
            cases.append(dict(al, name=f"al-preconditioner-{preconditioner.lower()}",
                              group="preconditioners", preconditioner=preconditioner))
        cases += [dict(al, name="al-full-mesh", group="symmetry", full_grid=True),
                  dict(al, name="al-gamma", group="gamma", gamma=True),
                  dict(al, name="al-explicit-gamma", group="gamma", mesh=[1, 1, 1]),
                  dict(al, name="al-auto", group="adaptive", added_mos="AUTO"),
                  dict(al, name="al-no-occupation-preconditioner", group="ablation",
                       occupation_preconditioner=False)]
    data_dir = ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    hashes = {}
    for name in ("BASIS_SET", "BASIS_MOLOPT", "POTENTIAL"):
        shutil.copy2(source / "data" / name, data_dir / name)
        hashes[name] = hashlib.sha256((data_dir / name).read_bytes()).hexdigest()
    revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    for case in cases:
        target = ROOT / "inputs" / case["name"]
        target.mkdir(parents=True, exist_ok=True)
        (target / "input.inp").write_text(input_text(case))
        case["input_sha256"] = hashlib.sha256((target / "input.inp").read_bytes()).hexdigest()
    manifest = dict(source_revision=revision, source_url="https://github.com/cp2k/cp2k",
                    phase=phase, units=dict(energy="hartree", length="angstrom", temperature="K"),
                    data_sha256=hashes, cases=cases)
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Prepared {len(cases)} cases at {revision}.")


def last_number(pattern, text):
    values = re.findall(pattern + r"\s*(" + NUMBER + ")", text, re.M)
    return float(values[-1].replace("D", "E")) if values else None


def summarize(path, metadata):
    text = (path / "output.out").read_text(errors="replace") if (path / "output.out").exists() else ""
    convergences = [int(x) for x in re.findall(r"SCF run converged in\s+(\d+)\s+steps", text)]
    warning_text = " ".join(re.sub(r"\*+", " ", text).split())
    iterations = re.findall(r"^\s+(\d+)\s+(?:OT\s+|Diag\.|Broy\.|Pulay\.|Mixing)", text, re.M)
    result = dict(metadata, normal_end="PROGRAM ENDED AT" in text,
                  scf_converged=bool(convergences) and "SCF run NOT converged" not in text,
                  converged_steps=convergences, printed_iterations=len(iterations),
                  free_energy_Ha=last_number(r"ENERGY\| Total FORCE_EVAL\s+\( QS \) energy \[hartree\]", text),
                  minus_TS_Ha=last_number(r"Electronic entropic energy:", text),
                  fermi_energy_Ha=last_number(r"Fermi energy:", text),
                  integrated_spin=last_number(r"Integrated spin density:", text),
                  total_charge_error=last_number(r"Total charge density on r-space grids:", text),
                  band_boundary_warnings=len(re.findall(r"K-point smearing includes the (?:first|last) band", warning_text, re.I)),
                  cp2k_time_s=None)
    actual_ranks = re.findall(r"GLOBAL\| Total number of message passing processes\s+(\d+)", text)
    result["actual_mpi_ranks"] = int(actual_ranks[-1]) if actual_ranks else None
    result["launcher_valid"] = bool(actual_ranks and result["actual_mpi_ranks"] == metadata.get("ranks"))
    timing = re.findall(r"^\s+CP2K\s+1\s+.*$", text, re.M)
    if timing:
        try:
            result["cp2k_time_s"] = float(timing[-1].split()[-1])
        except ValueError:
            pass
    scf_rows = re.findall(r"^\s+\d+\s+(?:OT\s+\S+|Diag\.|Broy\.|Pulay\.|Mixing).*?$", text, re.M)
    if scf_rows:
        result["last_scf_row"] = scf_rows[-1].strip()
        fields = scf_rows[-1].split()
        result["last_scf_iteration"] = int(fields[0])
        result["last_scf_residual"] = float(fields[5] if fields[1] == "OT" else fields[4])
    result["iteration_limit_reached"] = "SCF run NOT converged" in text
    electron_rows = re.findall(r"Electronic density on regular grids:\s*(" + NUMBER + r")\s+(" + NUMBER + r")", text)
    if electron_rows:
        result["electron_count_grid"] = -float(electron_rows[-1][0])
        result["electron_count_grid_error"] = float(electron_rows[-1][1])
    forces = re.findall(r"^\s+\d+\s+\d+\s+[A-Za-z]+\s+(" + NUMBER + r")\s+(" + NUMBER + r")\s+(" + NUMBER + r")\s*$", text, re.M)
    modern_forces = re.findall(r"^\s*FORCES\|\s+\d+\s+(" + NUMBER + r")\s+(" + NUMBER + r")\s+(" + NUMBER + r")", text, re.M)
    if modern_forces:
        forces = modern_forces
    result["force_rows_Ha_per_bohr"] = [[float(x) for x in row] for row in forces]
    stress_blocks = re.findall(r"STRESS\| Analytical stress tensor \[bar\]\n(.*?)(?=\n\s*\n)", text, re.S)
    stresses = re.findall(r"^\s*STRESS\|\s+[xyz]\s+(" + NUMBER + r")\s+(" + NUMBER + r")\s+(" + NUMBER + r")", stress_blocks[-1] if stress_blocks else "", re.M)
    result["stress_bar"] = [[float(x) for x in row] for row in stresses[-3:]]
    result["finite_entropy"] = result["minus_TS_Ha"] is not None and abs(result["minus_TS_Ha"]) > 1e-8
    result["generalized_correction_Ha"] = last_number(r"Smearing free energy correction:", text)
    result["objective_correction_Ha"] = (result["minus_TS_Ha"] if result["minus_TS_Ha"] is not None
                                           else result["generalized_correction_Ha"])
    result["geometry_converged"] = "GEOMETRY OPTIMIZATION COMPLETED" in text
    result["nuclear_step_limit_reached"] = "MAXIMUM NUMBER OF OPTIMIZATION STEPS REACHED" in text
    result["last_nuclear_step"] = last_number(r"OPT\| Step number", text)
    result["kpoint_count"] = last_number(r"BRILLOUIN\| List of Kpoints \[2 Pi/Bohr\]", text)
    printed_kpoints = re.findall(r"^\s*BRILLOUIN\|\s+(\d+)\s+(" + NUMBER + r")\s+(" + NUMBER
                                + r")\s+(" + NUMBER + r")\s+(" + NUMBER + r")\s*$", text, re.M)
    result["printed_kpoints"] = [[int(row[0])] + [float(x) for x in row[1:]] for row in printed_kpoints]
    result["ao_count"] = last_number(r"Number of spherical basis functions:", text)
    result["printed_mo_counts"] = [int(x) for x in re.findall(r"Number of molecular orbitals:\s+(\d+)", text)]
    result["last_mo_count"] = result["printed_mo_counts"][-1] if result["printed_mo_counts"] else None
    result["full_ks_subspace_rebuilds"] = text.count(
        "K-point OT: rebuilding physical virtual subspace by full KS diagonalization.")
    energy_file = next(path.glob("*.ener"), None)
    if energy_file:
        trajectory = [[float(x) for x in line.split()] for line in energy_file.read_text().splitlines()
                      if line.strip() and not line.lstrip().startswith("#")]
        result["md_energy_rows"] = trajectory
    return result


def run(binary, repetitions, groups, ranks, timeout, workers, names=None, converged_only=False,
        first_repetition=1):
    binary_hash = hashlib.sha256(Path(binary).read_bytes()).hexdigest()
    manifest = json.loads((ROOT / "manifest.json").read_text())
    selected = [c for c in manifest["cases"]
                if (not groups or c["group"] in groups) and (not names or c["name"] in names)]
    if names and set(names) != {c["name"] for c in selected}:
        raise ValueError("Requested cases are missing from the selected manifest")
    if converged_only:
        successful = []
        for case in selected:
            record = ROOT / "runs" / case["name"] / "repeat-1" / "result.json"
            if record.exists():
                first = json.loads(record.read_text())
                if first["normal_end"] and first["scf_converged"] and first.get("launcher_valid"):
                    successful.append(case)
        selected = successful
    schedule = [(case, repeat) for repeat in range(first_repetition, repetitions + 1) for case in selected]
    random.Random(20261018).shuffle(schedule)
    schedule.sort(key=lambda item: bool(item[0].get("depends_on")))
    environment = dict(os.environ, CP2K_DATA_DIR=str(ROOT / "data"),
                       OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
                       OMP_STACKSIZE="256M")
    def execute(item):
        case, repeat = item
        destination = ROOT / "runs" / case["name"] / f"repeat-{repeat}"
        destination.mkdir(parents=True, exist_ok=True)
        if (destination / "result.json").exists():
            return
        shutil.copy2(ROOT / "inputs" / case["name"] / "input.inp", destination / "input.inp")
        if case.get("depends_on"):
            parent = ROOT / "runs" / case["depends_on"] / f"repeat-{repeat}"
            shutil.copy2(parent / "calculation-RESTART.kp", destination / "initial.kp")
        command = ["srun", "--mpi=pmix", "--exclusive", "--exact", "--mem=2G", "--cpu-bind=cores", "--nodes=1",
                   f"--ntasks={ranks}", "--cpus-per-task=1", str(Path(binary).resolve()),
                   "-i", "input.inp", "-o", "output.out"]
        start = time.monotonic()
        with (destination / "launcher.log").open("w") as log:
            try:
                code = subprocess.run(command, cwd=destination, env=environment,
                                      stdout=log, stderr=subprocess.STDOUT, timeout=timeout).returncode
            except subprocess.TimeoutExpired:
                code = 124
        metadata = dict(case=case["name"], group=case["group"], repetition=repeat,
                        ranks=ranks, threads_per_rank=1, returncode=code,
                        time_limit_s=timeout,
                        binary_sha256=binary_hash,
                        elapsed_including_launcher_s=time.monotonic() - start,
                        hostname=os.environ.get("SLURMD_NODENAME"), command=command)
        result = summarize(destination, metadata)
        write_json(destination / "result.json", result)
        print(json.dumps(result), flush=True)
    if workers == 1:
        for item in schedule:
            execute(item)
    else:
        assert not any(case.get("depends_on") for case in selected), "Run restart chains serially"
        with ThreadPoolExecutor(max_workers=workers) as executor:
            list(executor.map(execute, schedule))
    collect()


def collect():
    results = []
    for path in sorted((ROOT / "runs").glob("*/*/result.json")):
        result = summarize(path.parent, json.loads(path.read_text()))
        results.append(result)
    # Different batch jobs may collect simultaneously; raw per-run records stay immutable.
    (ROOT / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(f"Collected {len(results)} completed or failed attempts.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    generator = subparsers.add_parser("generate")
    generator.add_argument("--source", required=True)
    generator.add_argument("--phase", choices=("pilot", "complete"), default="pilot")
    runner = subparsers.add_parser("run")
    runner.add_argument("--binary", required=True)
    runner.add_argument("--repetitions", type=int, default=1)
    runner.add_argument("--first-repetition", type=int, default=1)
    runner.add_argument("--groups", nargs="*")
    runner.add_argument("--cases", nargs="*")
    runner.add_argument("--repeat-converged-only", action="store_true")
    runner.add_argument("--ranks", type=int, default=2)
    runner.add_argument("--timeout", type=int, default=900)
    runner.add_argument("--workers", type=int, default=1)
    subparsers.add_parser("collect")
    arguments = parser.parse_args()
    if arguments.action == "generate":
        generate(arguments.source, arguments.phase)
    elif arguments.action == "run":
        run(arguments.binary, arguments.repetitions, arguments.groups,
            arguments.ranks, arguments.timeout, arguments.workers, arguments.cases,
            arguments.repeat_converged_only, arguments.first_repetition)
    else:
        collect()
