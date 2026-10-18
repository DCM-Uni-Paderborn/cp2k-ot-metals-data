"""Record the exact installed CPU dependencies without changing their shared builds."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
shared = Path("/home/kuehne88/cp2k-native-skala")
target = ROOT / "provenance" / "dependencies"
target.mkdir(parents=True, exist_ok=True)
records = {}
for name, source, build, install in (
    ("dbcsr", "dbcsr-src", "dbcsr-cpu", "dbcsr-cpu"),
    ("spglib", "spglib-src", "spglib", "spglib"),
):
    source = shared / "build" / source
    record = dict(source_revision=subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip(),
        source_status=subprocess.check_output(
        ["git", "-C", str(source), "status", "--short"], text=True).splitlines())
    patch = subprocess.check_output(["git", "-C", str(source), "diff", "--binary"])
    (target / f"{name}-source.patch").write_bytes(patch)
    cache = shared / "build" / build / "CMakeCache.txt"
    if cache.exists():
        shutil.copy2(cache, target / f"{name}-CMakeCache.txt")
    record["installed_libraries"] = {}
    for library in (shared / "install" / install / "lib").glob("*.so*"):
        if not library.is_symlink():
            record["installed_libraries"][library.name] = hashlib.sha256(library.read_bytes()).hexdigest()
    records[name] = record
records["dbcsr"]["cpu_scope"] = (
    "USE_ACCEL=none. The tracked CMake change only registers the B200 CUDA architecture. "
    "The untracked B200 tuning parameters are not used by this CPU build.")
(target / "dependencies.json").write_text(json.dumps(records, indent=2) + "\n")
