#!/usr/bin/env bash
#SBATCH --job-name=ot-metals-refresh
#SBATCH --partition=cpu-turin
#SBATCH --account=casus
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=64G
#SBATCH --time=00:45:00

set -eo pipefail
source /etc/profile
module purge
module load turin foss/2025b cmake/4.0.3
set -u
root=/home/kuehne88/ot-metals-validation-20261018
cd "$root"
revision=f6c7e1d6e4538564667591a51bda8dc52854de82
test "$(git -C source rev-parse HEAD)" = "$revision"
test "$(git -C source-spin-fix rev-parse HEAD)" = "$revision"
mkdir -p mpi-launch-check
if test -d runs/al-base-cg/repeat-1; then
  mv runs/al-base-cg/repeat-1 mpi-launch-check/al-before-source-refresh
fi
for configuration in cpu tblite spin-constraints; do
  case "$configuration" in
    cpu) build=build; source=source; provenance=provenance ;;
    tblite) build=build-tblite; source=source; provenance=provenance-tblite ;;
    spin-constraints) build=build-spin-fix; source=source-spin-fix; provenance=provenance-spin-constraints ;;
  esac
  cmake --build "$build" --target cp2k-bin --parallel "$SLURM_CPUS_PER_TASK"
  if test "$configuration" != tblite; then
    cmake --build "$build" --target qs_ot_complex_ref_unittest kpoint_smearing_unittest \
      qs_ot_minimizer_unittest low_rank_preconditioner_unittest \
      ot_covariant_preconditioner_unittest kpoint_lattice_fft_unittest \
      --parallel "$SLURM_CPUS_PER_TASK"
  fi
  mkdir -p "$provenance"
  git -C "$source" rev-parse HEAD > "$provenance/source-revision.txt"
  git -C "$source" status --porcelain > "$provenance/source-status.txt"
  sha256sum "$build/bin/cp2k.psmp" > "$provenance/binary-sha256.txt"
  "$build/bin/cp2k.psmp" --version > "$provenance/cp2k-version.txt"
  cp "$build/CMakeCache.txt" "$provenance/CMakeCache.txt"
  cp "$build/src/CMakeFiles/cp2k.dir/flags.make" "$provenance/flags.make"
  cp "$build/src/CMakeFiles/cp2k-bin.dir/link.txt" "$provenance/link.txt"
  ldd "$build/bin/cp2k.psmp" > "$provenance/linked-libraries.txt"
done
cp production-spin-corrections.patch provenance-spin-constraints/source.patch
