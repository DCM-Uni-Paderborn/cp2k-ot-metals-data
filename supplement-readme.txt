SUPPLEMENTARY MATERIAL: ORBITAL TRANSFORMATION FOR METALS

Working archive: https://github.com/DCM-Uni-Paderborn/cp2k-ot-metals-data
Initially private; reviewer/public access and permanent archival release remain
to be arranged. coverage.json explicitly records the missing CP2K evidence.

S1. Independent verification and figure reproduction
verify_derivatives.py executes deterministic complex finite-matrix experiments
using NumPy and SciPy. requirements.txt lists the dependencies. The random seed
is 271828. This script does not call CP2K and does not measure CP2K performance.

Run:
  python -m venv .venv
  .venv/bin/pip install -r requirements.txt
  .venv/bin/python verify_derivatives.py

Outputs:
  derivative-results.json: parameters, invariants and finite-difference scan.
  derivative-plot.tex: editable figure of derivative errors.
  convergence-plot.tex: editable plot of recorded CP2K iteration counts.
  figures/derivative-checks.pdf and .png: alternative data-plot rendering.
  figures/recorded-convergence.pdf and .png: alternative data-plot rendering.

The checks cover the fixed-number auxiliary-energy gradient, the spectral
occupation-projector derivative with a degenerate eigenvalue, finite complex
rotation gradients, cancellation of pure orbital-basis motion, the constant
energy gauge, total electron conservation and the frozen-Hamiltonian coupled
rotation/energy curvature. Assertions fail when the stated error thresholds
are exceeded. Roundoff-level last digits can differ with library versions.
The independent model does not validate a self-consistent CP2K Hxc kernel.

S2. Recorded electronic-structure comparisons
recorded-results.json contains transcribed numerical comparison records used
in the manuscript. It includes units, available settings and explicit caveats.
These data were collected during different implementation stages. They must
not be interpreted as a common-revision performance campaign. Single elapsed
times have no statistical confidence interval. A one-step motion check does
not establish long-time energy conservation.

This supplementary set is not the complete original CP2K input/output archive.
In particular, the four-atom Al model specification, the full option-audit
manifest, and executable/hardware details require recovery or new controlled
calculations before submission. Do not construct fictitious inputs from
partial records or label regenerated calculations as the original results.

S3. Recommended archive structure for the missing physical benchmarks
For each case, preserve input and all restart dependencies, full output,
basis/potential files or unambiguous library identifiers, compiler and linked
library versions, binary/build provenance, hardware, MPI/OpenMP layout and
analysis instructions. Record stopping criteria, smearing convention, electron
number, spin constraints, final energy/entropy/density residuals and failures.
For timing claims, use repeated runs with matched initialization and settings.
Deposit this completed archive in a persistent repository and insert its
resolvable identifier in the manuscript's data-availability statement.

S4. FFT-based orbital preconditioning
The manuscript appendix "Translation-averaged FFT preconditioning" derives
the direct-operator projection, Fourier-block inverse and optional balanced
local correction. It specifies real-Gamma scope, covariance and distributed
RHS routing. This is distinct from KPOINTS lattice transforms and from the
fixed-number occupation response.

The lattice_fft_application group in recorded-results.json transcribes
five-repeat medians for a 16-cell GFN2 N2 model with 2/4 MPI ranks and 14
OpenMP threads per rank. It compares gathered and distributed FFT application,
not FFT versus a conventional preconditioner or a metallic Mermin calculation.
All runs are reported to have taken 36 steps. The original temporary input
and output paths are no longer present. Per-run samples, numerical energy
endpoints, machine details and full build provenance are not in this archive.
Do not infer confidence intervals or general total-runtime gains from these
medians. Metal-specific acceleration requires a new matched comparison.
