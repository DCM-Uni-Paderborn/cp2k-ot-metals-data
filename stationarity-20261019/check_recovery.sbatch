#!/usr/bin/env bash
#SBATCH --job-name=ot-recovery-regression
#SBATCH --partition=cpu-turin
#SBATCH --account=casus
#SBATCH --nodes=1
#SBATCH --ntasks=2
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G
#SBATCH --time=00:20:00

set -eo pipefail
source /etc/profile
module purge
module load turin foss/2025b cmake/4.0.3
set -u
root=/home/kuehne88/ot-metals-validation-20261018
cd "$root"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export LD_LIBRARY_PATH=/home/kuehne88/cp2k-native-skala/install/dbcsr-cpu/lib:/home/kuehne88/cp2k-native-skala/install/spglib/lib:${LD_LIBRARY_PATH:-}
python3 source-spin-fix/tests/do_regtest.py build-spin-fix/bin psmp \
  --mpiranks 2 --ompthreads 1 --maxtasks 1 --skip_unittests --timeout 600 \
  --mpiexec 'srun --mpi=pmix --exclusive --exact --mem=2G --cpu-bind=cores --ntasks={N} --cpus-per-task=1' \
  --restrictdir '^QS/regtest-ot-3-[1-5]$' \
  --workbasedir "$root/stationarity-20261019/recovery/regtests" \
  > stationarity-20261019/recovery/regtests.log 2>&1
