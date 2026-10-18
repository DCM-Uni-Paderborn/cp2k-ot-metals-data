CONTROLLED METALLIC-OT VALIDATION

This directory contains new CP2K calculations, not reconstructed historical
measurements. The exact public source revision is pinned in manifest.json.
The principal DFT executable, the same-source tblite executable, and the
separately corrected spin-constraint executable have distinct provenance.
No timings from different executable configurations are pooled.

CONTENTS
inputs/ contains every complete input. data/ contains the exact basis and
pseudopotential files. runs/ retains inputs, raw program output, launcher
diagnostics, per-run summaries, and motion/restart data. manifest.json
describes each physical model and records input/dependency checksums.
provenance*/ identifies compilers, linked libraries, source changes, and
executables. analysis.json is derived from the raw output by analyze.py.
publication/ contains generated tables, an editable plot, and a compact
machine-readable summary. The raw output remains the authority.

BUILD AND RUN
build_cpu.sbatch and build_tblite.sbatch describe the ROSI CPU configuration.
refresh_builds.sbatch records the final common-source rebuild. Adjust project/module/dependency paths and
Slurm account/partition for another installation. Reproduce the scientific
inputs rather than relying on host-specific absolute paths.
The production-spin-corrections.patch applies the two tested spin fixes to
the pinned source.
The DBCSR source version, GPU-only configuration change, CPU build cache,
and installed-library hashes are recorded under provenance/dependencies/.

The generated manifest can be reconstructed in this order:
  python3 campaign.py generate --source /path/to/pinned/cp2k --phase complete
  python3 extend_campaign.py
  python3 add_spin_controls.py
  python3 add_thermal_controls.py
  python3 add_symmetry_controls.py
  python3 add_tblite_controls.py
  python3 add_spin_probes.py
  python3 add_adaptive_dynamics.py
  python3 add_motion_minimizers.py
  python3 add_default_motion.py
  python3 add_motion_tolerance.py
  python3 add_subspace_controls.py
  python3 record_source_configurations.py --source-revision SOURCE_REVISION

run_publication.sbatch uses one static comparison per Slurm array task.
run_publication.py --count gives the array size. Submit indices from zero
to one less than that count, with a suitable concurrency limit. Each case
selects its DFT, tblite, or corrected-spin executable explicitly.
finish_publication.sbatch runs the repeated primary timings and restart
chains after the static array finishes. run_publication_motion.sbatch runs
the predefined MD controls independently. campaign.py run --help lists
case/group selection. Neither driver overwrites an existing attempt.
run_nickel_companion.sbatch extends the two adaptive Ni minimizations in
separate second attempts with a 2400 s budget. Their original 900 s attempts
remain unchanged. This is not a change of Hamiltonian, state space,
temperature, or convergence target.
Set CP2K_DATA_DIR to data/, OMP_NUM_THREADS=1 and OPENBLAS_NUM_THREADS=1.
The driver uses Slurm steps with --mpi=pmix, exact per-step resources and
CPU binding. Each accepted output must report the requested MPI process
count. Preliminary singleton-world launches were preserved separately and
excluded from this archive's scientific results and timing comparisons.
launcher-validation.json documents the acceptance condition.
Do not launch the same case/repetition in two allocations simultaneously.
Existing result.json files are skipped rather than overwritten by a rerun.
Use a separate directory or repetition for an intentionally changed input.

ANALYSIS
From the repository root, install requirements.txt in an isolated Python
environment, then run:
  .venv/bin/python validation-20261018/analyze.py
  .venv/bin/python validation-20261018/write_tables.py

The second command writes publication/ by default. --output selects another
directory for integration with a manuscript clone. Unit conversions use
the constants of the evaluated CP2K source. MD conserved energy is read
from the conserved-quantity column, not from the wall-time column.
Repeated trajectory times are rejected because these calculations do not
restart an MD trajectory. They are not silently sorted or deduplicated.

INTERPRETATION
Normal termination, electronic convergence, requested spin constraints,
finite entropy, and final energy are separate checks. A numerical SCF
success with the wrong requested moment is not a physical success.
The old one-value UKS full-space requests and incorrect fixed-moment
controls remain identifiable. They are not relabelled as valid results.
Time-limited controls retain their actual status. Preliminary launcher
attempts are excluded and are not counted as algorithmic failures.

The completed campaign contains 136 distinct first attempts and 152 total
attempts including repetitions and restart chains. Of these, 138 terminate
normally with reported electronic convergence. That count is not a claim
of 138 matching physical endpoints or converged nuclear optimizations.
The occupation-preconditioner-OFF Al control reaches an inequivalent
free-energy/entropy endpoint. The old fixed-moment Ni control violates its
requested population constraint. Both remain visible as negative controls.
Eight 10 fs trajectories complete. Six tighter motion controls reach an
SCF or elapsed-time limit and have no fitted conservation drift assigned.

Short trajectories are not long-time energy-conservation evidence. The
compact bases, meshes, and cells are not converged materials predictions.
Solver-specific SCF residuals are not numerically identical norms.
Full-AO and tail-controlled trajectories are distinguished. A timing
improvement from a smaller orbital space is not an isolated minimizer gain.
