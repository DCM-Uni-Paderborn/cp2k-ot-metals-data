#!/usr/bin/env bash
#SBATCH --job-name=ot-metals-checks
#SBATCH --partition=cpu-turin
#SBATCH --account=casus
#SBATCH --nodes=1
#SBATCH --ntasks=2
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G
#SBATCH --time=02:00:00

set -eo pipefail
source /etc/profile
module purge
module load turin foss/2025b cmake/4.0.3
set -u
validation_root=/home/kuehne88/ot-metals-validation-20261018
export LD_LIBRARY_PATH=/home/kuehne88/cp2k-native-skala/install/dbcsr-cpu/lib:/home/kuehne88/cp2k-native-skala/install/spglib/lib:${LD_LIBRARY_PATH:-}
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_STACKSIZE=256M
cd "$validation_root"
mkdir -p checks
for ranks in 1 2; do
  for unit in qs_ot_complex_ref kpoint_smearing qs_ot_minimizer low_rank_preconditioner ot_covariant_preconditioner kpoint_lattice_fft; do
    srun --mpi=pmix --exclusive --cpu-bind=cores --ntasks="$ranks" --cpus-per-task=1 \
      "build/bin/${unit}_unittest.psmp" > "checks/${unit}-mpi${ranks}.out" 2>&1
  done
done
python3 source/tests/do_regtest.py build/bin psmp --mpiranks 2 --ompthreads 1 \
  --maxtasks 1 --skip_unittests --timeout 600 \
  --mpiexec 'srun --mpi=pmix --exclusive --cpu-bind=cores --ntasks={N} --cpus-per-task=1' \
  --restrictdir '^QS/regtest-ot-3-[1-5]$' \
  --workbasedir "$validation_root/checks/regtests" > checks/regtests.log 2>&1
touch checks-complete
