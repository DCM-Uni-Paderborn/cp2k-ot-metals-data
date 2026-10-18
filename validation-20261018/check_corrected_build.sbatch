#!/usr/bin/env bash
#SBATCH --job-name=ot-corrected-checks
#SBATCH --partition=cpu-turin
#SBATCH --account=casus
#SBATCH --nodes=1
#SBATCH --ntasks=2
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G
#SBATCH --time=01:00:00

set -eo pipefail
source /etc/profile
module purge
module load turin foss/2025b cmake/4.0.3
set -u
root=/home/kuehne88/ot-metals-validation-20261018
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
cd "$root"
mkdir -p corrected-checks
for unit in qs_ot_complex_ref kpoint_smearing qs_ot_minimizer low_rank_preconditioner ot_covariant_preconditioner kpoint_lattice_fft; do
  cmake --build build-spin-fix --target "${unit}_unittest" --parallel 2
  for ranks in 1 2; do
    srun --mpi=pmix --exact --exclusive --mem=2G -n "$ranks" "build-spin-fix/bin/${unit}_unittest.psmp" \
      > "corrected-checks/${unit}-mpi$ranks.out" 2>&1
  done
done
python3 source-spin-fix/tests/do_regtest.py build-spin-fix/bin psmp \
  --mpiranks 2 --ompthreads 1 --maxtasks 1 --skip_unittests --timeout 600 \
  --mpiexec 'srun --mpi=pmix --exclusive --exact --mem=2G --cpu-bind=cores --ntasks={N} --cpus-per-task=1' \
  --restrictdir '^QS/regtest-ot-3-[1-5]$' --workbasedir "$root/corrected-checks/regtests" \
  > corrected-checks/regtests.log 2>&1
