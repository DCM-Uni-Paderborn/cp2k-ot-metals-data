#!/usr/bin/env bash
#SBATCH --job-name=ot-metals-repeats
#SBATCH --partition=cpu-turin
#SBATCH --account=casus
#SBATCH --nodes=1
#SBATCH --ntasks=8
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G
#SBATCH --time=00:30:00

set -eo pipefail
source /etc/profile
module purge
module load turin foss/2025b cmake/4.0.3
set -u
cd /home/kuehne88/ot-metals-validation-20261018
python3 run_publication.py --finish
