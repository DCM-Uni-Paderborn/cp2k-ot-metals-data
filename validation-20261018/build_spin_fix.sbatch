#!/usr/bin/env bash
#SBATCH --job-name=ot-spin-constraints-build
#SBATCH --partition=cpu-turin
#SBATCH --account=casus
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=64G
#SBATCH --time=02:00:00

set -eo pipefail
source /etc/profile
module purge
module load turin foss/2025b cmake/4.0.3
set -u
validation_root=/home/kuehne88/ot-metals-validation-20261018
dependencies=/home/kuehne88/cp2k-native-skala/install
cd "$validation_root"
git -C source worktree add --detach ../source-spin-fix f6c7e1d6e4538564667591a51bda8dc52854de82
git -C source-spin-fix apply ../production-spin-corrections.patch
cmake -S source-spin-fix -B build-spin-fix \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=mpicc -DCMAKE_CXX_COMPILER=mpicxx -DCMAKE_Fortran_COMPILER=mpifort \
  -DCMAKE_PREFIX_PATH="$dependencies/dbcsr-cpu;$dependencies/spglib;$validation_root/dependencies/wignernj" \
  -DDBCSR_DIR="$dependencies/dbcsr-cpu/lib/cmake/dbcsr" \
  -DCP2K_USE_EVERYTHING=OFF -DCP2K_USE_MPI=ON -DCP2K_USE_MPI_F08=ON \
  -DCP2K_USE_DBCSR_CONFIG=ON -DCP2K_USE_SPGLIB=ON -DCP2K_USE_ACCEL=NONE \
  -DCP2K_BLAS_VENDOR=OpenBLAS -DCP2K_SCALAPACK_VENDOR=GENERIC \
  -DCP2K_ENABLE_FFTW3_OPENMP_SUPPORT=ON -DBUILD_SHARED_LIBS=OFF
cmake --build build-spin-fix --target cp2k-bin --parallel "$SLURM_CPUS_PER_TASK"
mkdir -p provenance-spin-constraints
cp build-spin-fix/CMakeCache.txt provenance-spin-constraints/CMakeCache.txt
cp production-spin-corrections.patch provenance-spin-constraints/source.patch
git -C source-spin-fix rev-parse HEAD > provenance-spin-constraints/source-revision.txt
sha256sum build-spin-fix/bin/cp2k.psmp > provenance-spin-constraints/binary-sha256.txt
touch build-spin-fix-complete
