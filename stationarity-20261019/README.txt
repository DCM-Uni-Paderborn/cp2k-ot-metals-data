INDEPENDENT CANONICAL-STATIONARITY AND RECOVERY CONTROLS

This supplement preserves the original 18 October campaign unchanged.
All eleven additional calculations use two actual MPI ranks and one thread
per rank on the same CPU/software configuration as that campaign.
They are compact solver tests, not converged materials predictions.

The top-level runs/ directory contains five diagnostic-only repetitions.
The projected physical Hamiltonian, unchanged current orbitals, global
Fermi constraint groups, and current occupations define a canonical density
residual, a frozen-H free-energy gap, and a commutator norm. The diagnostic
is evaluated before the next trial-orbital update. It does not modify the
minimizer or its stopping criterion. The source patch includes the two
previously archived spin fixes and the diagnostic. Its base revision is
recorded in manifest.json. Apply the patch to that source revision.

larger/ contains a matched eight-atom Al comparison with 104 AO functions,
16 adaptively selected orbitals, and the diagnostic-only executable.
The inherited parser's ao_count field counts functions of a printed atomic
kind, not necessarily the whole simulation cell. analysis.json instead
records total_ao_count from the explicit total orbital-function line.

recovery/ contains four matched controls with the physical Fermi-Dirac
recovery policy made independent of the occupation-preconditioner switch.
Its residual windows, four-rebuild limit, gradients, and damping constants
are unchanged. This executable adds a tested pure matrix-metrics helper.
The source patch and binary checksum are separate from the first cohort.
The exact canonical-density test error is 2.2204e-17 on MPI-1 and MPI-2.

The baseline Al OFF endpoint reports convergence after 199 steps but has
a canonical gap of 0.002572647841387 Ha. It is not a physical stationary
solution. The modified-policy control reaches the matching endpoint after
27 steps and two full-KS recoveries, with gap 2.563695850662e-10 Ha.
The unchanged Al/Cu ON controls and four-function Al OFF control preserve
their iteration counts and free energies. The Ni audit repeats the valid
adaptive variable-moment endpoint. Neither the diagnostic nor this limited
control establishes a universal convergence certificate or new default.

analysis.json is regenerated with
  python3 stationarity-20261019/analyze.py
The script verifies each retained input checksum and actual MPI count.
Raw output.out, result.json, input.inp, and launcher.log files are retained.
All basis and potential files are provided with checksums. Full binary
executables and private failed-instrumentation prototypes are excluded.
The diagnostic-only build and the recovery build use the spin-correction
CPU CMake configuration archived under validation-20261018. Exact patches
are in provenance/source.patch and recovery/provenance/source.patch.

The run driver reuses validation-20261018/campaign.py. Before reproduction,
set the Slurm account/partition and installation paths for the target system
in the supplied sbatch files. Use PMIx and verify the MPI world size.
The manifests and inputs define the scientific settings independently of
these machine-specific launch paths. Do not overwrite the original raw
attempts when repeating a calculation. Use a new campaign directory.

Source-patch deposition supports numerical reproducibility. It is not the
publication of a CP2K pull request or a claim of upstream integration.
No author approval of the manuscript is implied.
