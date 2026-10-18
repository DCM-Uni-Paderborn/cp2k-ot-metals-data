#!/usr/bin/env bash
#SBATCH --job-name=ot-metals-nickel
#SBATCH --partition=cpu-turin
#SBATCH --account=casus
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:45:00

set -eo pipefail
source /etc/profile
module purge
module load turin foss/2025b cmake/4.0.3
set -u
cd /home/kuehne88/ot-metals-validation-20261018
python3 campaign.py run --binary build/bin/cp2k.psmp --workers 2 --timeout 2400 \
  --repetitions 2 --first-repetition 2 --cases ni-reduced-cg ni-reduced-lbfgs
