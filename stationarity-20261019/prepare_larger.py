"""Generate a matched eight-atom Al comparison with a proper orbital complement."""

import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
original = next(path for path in (
    ROOT.parent / "validation-20261018",
    ROOT.parent / "cp2k-ot-metals-data/validation-20261018",
) if path.exists())
spec = importlib.util.spec_from_file_location("metal_campaign", original / "campaign.py")
campaign = importlib.util.module_from_spec(spec)
spec.loader.exec_module(campaign)
primitive = [[0, 2.025, 2.025], [2.025, 0, 2.025], [2.025, 2.025, 0]]
coordinates = [[sum(index[j]*primitive[j][i] for j in range(3)) for i in range(3)]
               for index in itertools.product(range(2), repeat=3)]
target = ROOT / "larger"
cases = []
for method in ("CG", "DIAG"):
    case = dict(campaign.SYSTEMS["Al"], element="Al", method=method,
                name=f"al-eight-{method.lower()}", group="larger",
                cell=[[2*x for x in row] for row in primitive],
                coordinates=coordinates, mesh=[2, 2, 2], added_mos="AUTO")
    path = target / "inputs" / case["name"] / "input.inp"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(campaign.input_text(case))
    case["input_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    cases.append(case)
manifest = json.loads((original / "manifest.json").read_text())
(target / "data").mkdir(exist_ok=True)
for name in manifest["data_sha256"]:
    shutil.copy2(original / "data" / name, target / "data" / name)
(target / "manifest.json").write_text(json.dumps(dict(
    source_revision=manifest["source_revision"], cases=cases,
    data_sha256=manifest["data_sha256"]), indent=2) + "\n")
