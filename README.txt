ORBITAL TRANSFORMATION FOR METALS: REPRODUCIBILITY MATERIALS

Preparation archive, 18 September 2026. Not a complete publication dataset.
Repository: https://github.com/DCM-Uni-Paderborn/cp2k-ot-metals-data

CONTENTS AND EVIDENCE LEVELS
verify_derivatives.py is an independent, deterministic NumPy/SciPy matrix
experiment. It does not run CP2K. It verifies fixed-electron-number response,
finite complex rotations, gauge cancellation and frozen-Hamiltonian curvature.
derivative-results.json and derivative-plot.tex are its numerical output and
editable plot. The two channels, spectra, weights and seed are in the script.

recorded-results.json transcribes historical CP2K development comparisons.
convergence-plot.tex visualizes those records. They are not raw CP2K outputs,
newly reproduced measurements or a common-build performance campaign.
coverage.json records the completeness of each evidence group. Missing source
inputs, outputs and environment information are not reconstructed from memory.
supplement-readme.txt describes the experiment and the archival requirements.

REPRODUCE THE MATRIX EXPERIMENT
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
  .venv/bin/python verify_derivatives.py

Assertions check the numerical identities and finite-difference errors.
Last-bit differences between numerical library versions are normal.
The run produces derivative-results.json, both editable .tex plots, and
PDF/PNG plots under figures/. It requires no CP2K executable.

CHECK THE DISTRIBUTED MATERIAL BEFORE REGENERATION
  python3 verify_archive.py

SHA256SUMS.json covers the original deposited data, scripts and instructions.
environment.json identifies the numerical libraries used for the verification.
After regeneration, hashes of plots may change due to timestamps or last-bit
floating-point differences; inspect numerical assertions and values instead
of expecting bytewise equality from an independently regenerated result.

RELEASE CONDITIONS
This repository is initially private. A private URL is not reviewer access
and is not an open-data deposit. Before submission, recover or replace the
missing CP2K benchmark archives, supply reviewer/public access, freeze a data
release and arrange persistent archival identification (for example through
Zenodo or Mendeley Data). No DOI or completed data deposit is asserted here.
Author correspondence, local research notes, credentials, manuscript drafts
and private development logs are deliberately not included.
