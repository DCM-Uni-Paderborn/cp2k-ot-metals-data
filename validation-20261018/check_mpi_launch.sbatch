#!/usr/bin/env bash
#SBATCH --job-name=ot-metals-mpi-check
#SBATCH --partition=cpu-turin
#SBATCH --account=casus
#SBATCH --nodes=1
#SBATCH --ntasks=2
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:15:00

set -eo pipefail
source /etc/profile
module purge
module load turin foss/2025b cmake/4.0.3
set -u
root=/home/kuehne88/ot-metals-validation-20261018
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_STACKSIZE=256M
cd "$root"
mkdir -p mpi-launch-check
srun --mpi=pmix --exact --exclusive --mem=2G -n 2 \
  build-spin-fix/bin/kpoint_smearing_unittest.psmp > mpi-launch-check/smearing.out 2>&1
python3 campaign.py run --binary build/bin/cp2k.psmp --cases al-base-cg --workers 1
python3 -c 'import json; from pathlib import Path; r=json.loads(Path("runs/al-base-cg/repeat-1/result.json").read_text()); assert r["launcher_valid"] and r["actual_mpi_ranks"] == 2 and r["normal_end"] and r["scf_converged"], r'
