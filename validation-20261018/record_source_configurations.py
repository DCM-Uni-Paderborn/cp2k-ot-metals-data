"""Bind each model group to the actual executable and source provenance."""

import hashlib
import json
import argparse

from campaign import ROOT

path = ROOT / "manifest.json"
manifest = json.loads(path.read_text())
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source-revision")
arguments = parser.parse_args()
if arguments.source_revision:
    manifest["source_revision"] = arguments.source_revision
configurations = {}
for name, directory in (("cpu", "provenance"), ("tblite", "provenance-tblite"),
                        ("spin-corrected", "provenance-spin-constraints")):
    provenance = ROOT / directory
    record = dict(base_source_revision=manifest["source_revision"], provenance_directory=directory)
    checksum_file = provenance / "binary-sha256.txt"
    if checksum_file.exists():
        record["binary_sha256"] = checksum_file.read_text().split()[0]
    if name == "spin-corrected":
        record["source_patch"] = "production-spin-corrections.patch"
        record["source_patch_sha256"] = hashlib.sha256((ROOT / record["source_patch"]).read_bytes()).hexdigest()
    configurations[name] = record
for case in manifest["cases"]:
    case["executable_configuration"] = ("tblite" if case["group"] == "tblite" else
                                        "spin-corrected" if case["group"] == "spin-probes" else "cpu")
manifest["executable_configurations"] = configurations
path.write_text(json.dumps(manifest, indent=2) + "\n")
