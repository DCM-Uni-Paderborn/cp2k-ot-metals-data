#!/usr/bin/env bash
#SBATCH --job-name=ot-metals-eight-atom
#SBATCH --partition=cpu-turin
#SBATCH --account=casus
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:35:00

set -eo pipefail
source /etc/profile
module purge
module load turin foss/2025b cmake/4.0.3
set -u
root=/home/kuehne88/ot-metals-validation-20261018
cd "$root"
export LD_LIBRARY_PATH=/home/kuehne88/cp2k-native-skala/install/dbcsr-cpu/lib:/home/kuehne88/cp2k-native-skala/install/spglib/lib:${LD_LIBRARY_PATH:-}
python3 stationarity-20261019/run_audit.py "$root/build-spin-fix/bin/cp2k.psmp" "$root/stationarity-20261019/larger"
