ORBITAL TRANSFORMATION FOR METALS: REPRODUCIBILITY MATERIALS

This repository separates independent matrix verification, new archived
CP2K calculations, and historical transcriptions. It accompanies the
metallic-OT manuscript and its supporting-information document.

verify_derivatives.py reproduces the fixed-number, complex-rotation,
projector, and frozen-Hamiltonian curvature checks. It does not call CP2K.
requirements.txt pins the numerical environment. Run in an isolated venv:
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
  .venv/bin/python verify_derivatives.py

validation-20261018/ contains complete physical inputs, raw outputs,
model definitions, source/build provenance, and the analysis code for the
new common-source campaign. Its README.txt explains model generation,
separate executable configurations, failures, and reproduction. Run:
  .venv/bin/python validation-20261018/analyze.py
  .venv/bin/python validation-20261018/write_tables.py

recorded-results.json retains earlier numerical transcriptions for
historical traceability. They are not newly reproduced measurements and
are not the source of the replacement publication tables. The old
convergence-plot.tex represents those historical records only.

coverage.json distinguishes the evidence and remaining release conditions.
SHA256SUMS.json checks deposited-file integrity. After inspecting a data
update, regenerate the checksums with prepare_archive.py and verify them
with verify_archive.py. Regeneration does not approve the scientific
interpretation or author declarations.

The versioned public dataset is validation-2026-10-18:
https://github.com/DCM-Uni-Paderborn/cp2k-ot-metals-data/releases/tag/validation-2026-10-18
Its checksummed archive contains numerical evidence and reproduction
materials, not an author-approved manuscript. No DOI is claimed.
Credentials, correspondence, local author notes, and unrelated development
files are excluded. Publication of the dataset does not imply approval of
an article or its author declarations.

stationarity-20261019/ supplements the frozen campaign with independent
canonical-density checks, a matched eight-atom Al calculation, and a
metric-independent recovery-policy control. The baseline negative result
is retained. Its README.txt distinguishes the two executable patches and
the limited scope of the additional measurements. The cumulative follow-up
release is validation-2026-10-19; the earlier release remains immutable.

CP2K-derived inputs, numerical data definitions, and source patches retain
their upstream licensing. The CP2K license text is included as
LICENSE.cp2k. The exact upstream source and dependency pins are recorded
in validation-20261018/manifest.json and provenance/dependencies/.
