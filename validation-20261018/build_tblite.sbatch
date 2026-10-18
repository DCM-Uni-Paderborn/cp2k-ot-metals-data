#!/usr/bin/env bash
#SBATCH --job-name=ot-metals-tblite-build
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
curl --fail --location --retry 3 \
  https://www.cp2k.org/static/downloads/tblite-0.7.0.tar.xz \
  --output dependencies/tblite-0.7.0.tar.xz
printf '%s  %s\n' \
  3a7cb4602101e828caf41c38ca5e30f82de82d0d26d5db40168acdcad3462b92 \
  dependencies/tblite-0.7.0.tar.xz | sha256sum --check
tar -xJf dependencies/tblite-0.7.0.tar.xz -C dependencies
cmake -S dependencies/tblite-0.7.0 -B dependencies/tblite-build \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$validation_root/dependencies/tblite" \
  -DCMAKE_INSTALL_LIBDIR=lib -DBUILD_TESTING=OFF -DWITH_TESTS=OFF
cmake --build dependencies/tblite-build --parallel 16
cmake --install dependencies/tblite-build

cmake -S source -B build-tblite \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=mpicc -DCMAKE_CXX_COMPILER=mpicxx -DCMAKE_Fortran_COMPILER=mpifort \
  -DCMAKE_PREFIX_PATH="$dependencies/dbcsr-cpu;$dependencies/spglib;$validation_root/dependencies/wignernj;$validation_root/dependencies/tblite" \
  -DDBCSR_DIR="$dependencies/dbcsr-cpu/lib/cmake/dbcsr" \
  -DCP2K_USE_EVERYTHING=OFF -DCP2K_USE_MPI=ON -DCP2K_USE_MPI_F08=ON \
  -DCP2K_USE_DBCSR_CONFIG=ON -DCP2K_USE_SPGLIB=ON -DCP2K_USE_ACCEL=NONE \
  -DCP2K_USE_TBLITE=ON -DCP2K_BLAS_VENDOR=OpenBLAS -DCP2K_SCALAPACK_VENDOR=GENERIC \
  -DCP2K_ENABLE_FFTW3_OPENMP_SUPPORT=ON -DBUILD_SHARED_LIBS=OFF
cmake --build build-tblite --target cp2k-bin --parallel "$SLURM_CPUS_PER_TASK"
mkdir -p provenance-tblite
cp build-tblite/CMakeCache.txt provenance-tblite/CMakeCache.txt
cp build-tblite/src/CMakeFiles/cp2k.dir/flags.make provenance-tblite/flags.make
cp build-tblite/src/CMakeFiles/cp2k-bin.dir/link.txt provenance-tblite/link.txt
build-tblite/bin/cp2k.psmp --version > provenance-tblite/cp2k-version.txt
ldd build-tblite/bin/cp2k.psmp > provenance-tblite/linked-libraries.txt
sha256sum build-tblite/bin/cp2k.psmp > provenance-tblite/binary-sha256.txt
touch build-tblite-complete
