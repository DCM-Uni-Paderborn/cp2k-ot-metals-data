"""Run the predefined publication comparisons with verified MPI process counts."""

import argparse
import json
import os

from campaign import ROOT, run

cases = json.loads((ROOT / "manifest.json").read_text())["cases"]
selected = [c for c in cases if c.get("run_type") != "MD" and c["group"] != "restart"
            and not (c.get("element") == "Ni" and c.get("added_mos") != "-1 -1"
                     and c["group"] != "variational-subspace")]
selected.sort(key=lambda c: c["name"])
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--finish", action="store_true")
parser.add_argument("--count", action="store_true")
arguments = parser.parse_args()
if arguments.count:
    print(len(selected))
elif arguments.finish:
    primary = [f"{element}-base-{method}" + ("-full-spin-space" if element == "ni" else "")
               for element in ("al", "cu", "ni") for method in ("cg", "lbfgs", "diag")]
    run(ROOT / "build/bin/cp2k.psmp", 3, None, 2, 900, 4, primary, converged_only=True)
    run(ROOT / "build/bin/cp2k.psmp", 1, ["restart"], 2, 900, 1)
else:
    case = selected[int(os.environ["SLURM_ARRAY_TASK_ID"])]
    build = ("build-spin-fix" if case["group"] == "spin-probes" else
             "build-tblite" if case["group"] == "tblite" else "build")
    timeout = 1800 if case["group"] == "spin-probes" else 900
    run(ROOT / f"{build}/bin/cp2k.psmp", 1, None, 2, timeout, 1, [case["name"]])
