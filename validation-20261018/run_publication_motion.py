"""Propagate only the predefined motion controls, independently of static comparisons."""

import json

from campaign import ROOT, run

cases = json.loads((ROOT / "manifest.json").read_text())["cases"]
selected = [case["name"] for case in cases if case.get("run_type") == "MD"]
run(ROOT / "build/bin/cp2k.psmp", 1, None, 2, 3600, 14, selected)
