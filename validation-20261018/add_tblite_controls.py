"""Prepare matched direct GFN1 and nested GFN2 OT/diagonalization pairs."""

import hashlib
import json
from campaign import ROOT


def make_input(model, ot):
    if model == "GFN1" and ot:
        solver = """      &OT
        ALGORITHM STRICT
        MINIMIZER DIIS
        PRECONDITIONER FULL_SINGLE_INVERSE
        ROTATION
        ENERGIES
        OCCUPATION_PRECONDITIONER
      &END OT"""
    elif model == "GFN2" and ot:
        solver = """      &DIAGONALIZATION
        ALGORITHM OT
        EPS_ITER 1.0E-8
        MAX_ITER 120
        &OT
          ALGORITHM STRICT
          MINIMIZER LBFGS
          PRECONDITIONER FULL_SINGLE_INVERSE
          ROTATION
        &END OT
      &END DIAGONALIZATION"""
    else:
        solver = """      &DIAGONALIZATION
        ALGORITHM STANDARD
      &END DIAGONALIZATION"""
    mixer = "NONE" if model == "GFN1" and ot else "TBLITE"
    return f"""&GLOBAL
  PROJECT calculation
  RUN_TYPE ENERGY
  PRINT_LEVEL MEDIUM
&END GLOBAL
&FORCE_EVAL
  &DFT
    &KPOINTS
      FULL_GRID OFF
      SCHEME MONKHORST-PACK 3 1 1
      SYMMETRY ON
      WAVEFUNCTIONS COMPLEX
      PARALLEL_GROUP_SIZE 0
    &END KPOINTS
    &QS
      METHOD xTB
      &XTB
        GFN_TYPE TBLITE
        SCC_MIXER {mixer}
        &TBLITE
          METHOD {model}
        &END TBLITE
      &END XTB
    &END QS
    &SCF
      ADDED_MOS -1
      EPS_SCF 1.0E-7
      MAX_SCF 300
      SCF_GUESS MOPAC
{solver}
      &SMEAR
        METHOD FERMI_DIRAC
        ELECTRONIC_TEMPERATURE 500
      &END SMEAR
      &PRINT
        &RESTART OFF
        &END RESTART
      &END PRINT
    &END SCF
  &END DFT
  &SUBSYS
    &CELL
      ABC 2.8637824638 2.8637824638 2.8637824638
      ALPHA_BETA_GAMMA 60 60 60
    &END CELL
    &COORD
      Al 0 0 0
    &END COORD
  &END SUBSYS
&END FORCE_EVAL
"""


manifest = json.loads((ROOT / "manifest.json").read_text())
known = {c["name"] for c in manifest["cases"]}
for model in ("GFN1", "GFN2"):
    for ot in (False, True):
        name = f"al-{model.lower()}-{'ot' if ot else 'diag'}"
        if name in known:
            continue
        path = ROOT / "inputs" / name / "input.inp"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(make_input(model, ot))
        manifest["cases"].append(dict(name=name, group="tblite", model=model,
                                     method="OT" if ot else "DIAG", temperature=500,
                                     mesh=[3, 1, 1], input_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
(ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
