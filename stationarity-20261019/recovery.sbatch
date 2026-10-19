#!/usr/bin/env bash
#SBATCH --job-name=ot-canonical-recovery
#SBATCH --partition=cpu-turin
#SBATCH --account=casus
#SBATCH --nodes=1
#SBATCH --ntasks=8
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G
#SBATCH --time=00:35:00

set -eo pipefail
source /etc/profile
module purge
module load turin foss/2025b cmake/4.0.3
set -u
root=/home/kuehne88/ot-metals-validation-20261018
cd "$root"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export LD_LIBRARY_PATH=/home/kuehne88/cp2k-native-skala/install/dbcsr-cpu/lib:/home/kuehne88/cp2k-native-skala/install/spglib/lib:${LD_LIBRARY_PATH:-}
mkdir -p stationarity-20261019/recovery/provenance
if ! test -e stationarity-20261019/provenance/cp2k-endpoint-audit.psmp; then
  cp build-spin-fix/bin/cp2k.psmp stationarity-20261019/provenance/cp2k-endpoint-audit.psmp
fi
cmake --build build-spin-fix --target cp2k-bin qs_ot_complex_ref_unittest --parallel 8
sha256sum build-spin-fix/bin/cp2k.psmp > stationarity-20261019/recovery/provenance/binary-sha256.txt
git -C source-spin-fix diff > stationarity-20261019/recovery/provenance/source.patch
for ranks in 1 2; do
  srun --mpi=pmix --exclusive --exact --cpu-bind=cores --ntasks="$ranks" --cpus-per-task=1 \
    build-spin-fix/bin/qs_ot_complex_ref_unittest.psmp > "stationarity-20261019/recovery/provenance/unit-np${ranks}.out"
done
python3 stationarity-20261019/run_audit.py "$root/build-spin-fix/bin/cp2k.psmp" "$root/stationarity-20261019/recovery"
