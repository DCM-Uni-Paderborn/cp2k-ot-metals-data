"""Retain one-value UKS failures and add explicit two-spin orbital-space controls."""

import copy
import hashlib
import json

from campaign import ROOT, input_text

path = ROOT / "manifest.json"
manifest = json.loads(path.read_text())
names = {case["name"] for case in manifest["cases"]}
additions = []
for case in manifest["cases"]:
    if case["element"] != "Ni" or case.get("added_mos") == "-1 -1":
        continue
    controlled = copy.deepcopy(case)
    controlled["name"] += "-full-spin-space"
    if controlled["name"] in names:
        continue
    controlled["added_mos"] = "-1 -1"
    controlled["group"] = "spin-controls"
    controlled["paired_one_value_input"] = case["name"]
    directory = ROOT / "inputs" / controlled["name"]
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "input.inp").write_text(input_text(controlled))
    controlled["input_sha256"] = hashlib.sha256((directory / "input.inp").read_bytes()).hexdigest()
    additions.append(controlled)
manifest["cases"].extend(additions)
path.write_text(json.dumps(manifest, indent=2) + "\n")
print(f"Added {len(additions)} explicit-spin controls.")
