#!/usr/bin/env bash
#SBATCH --job-name=ot-metals-build
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
mkdir -p provenance dependencies
git -C source rev-parse HEAD > provenance/source-revision.txt
test "$(cat provenance/source-revision.txt)" = f6c7e1d6e4538564667591a51bda8dc52854de82
git -C source status --porcelain > provenance/source-status.txt
test ! -s provenance/source-status.txt
module -t list 2> provenance/modules.txt
lscpu > provenance/cpu.txt
mpifort --version > provenance/compiler.txt
mpirun --version > provenance/mpi.txt
cmake --version > provenance/cmake.txt

curl --fail --location --retry 3 \
  https://www.cp2k.org/static/downloads/libwignernj-0.8.0.tar.gz \
  --output dependencies/libwignernj-0.8.0.tar.gz
printf '%s  %s\n' \
  7220cea92652040d6456aba92ff151124d9c69ce8695840490c18dd25a0da80c \
  dependencies/libwignernj-0.8.0.tar.gz | sha256sum --check
tar -xzf dependencies/libwignernj-0.8.0.tar.gz -C dependencies
cmake -S dependencies/libwignernj-0.8.0 -B dependencies/wignernj-build \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$validation_root/dependencies/wignernj" \
  -DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
  -DBUILD_SHARED_LIBS=OFF -DWIGNERNJ_BUILD_FORTRAN=OFF \
  -DWIGNERNJ_BUILD_TESTS=OFF -DWIGNERNJ_BUILD_CXX_TESTS=OFF \
  -DWIGNERNJ_BUILD_EXAMPLES=OFF
cmake --build dependencies/wignernj-build --parallel 8
cmake --install dependencies/wignernj-build

cmake -S source -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=mpicc -DCMAKE_CXX_COMPILER=mpicxx -DCMAKE_Fortran_COMPILER=mpifort \
  -DCMAKE_PREFIX_PATH="$dependencies/dbcsr-cpu;$dependencies/spglib;$validation_root/dependencies/wignernj" \
  -DDBCSR_DIR="$dependencies/dbcsr-cpu/lib/cmake/dbcsr" \
  -DCP2K_USE_EVERYTHING=OFF -DCP2K_USE_MPI=ON -DCP2K_USE_MPI_F08=ON \
  -DCP2K_USE_DBCSR_CONFIG=ON -DCP2K_USE_SPGLIB=ON -DCP2K_USE_ACCEL=NONE \
  -DCP2K_BLAS_VENDOR=OpenBLAS -DCP2K_SCALAPACK_VENDOR=GENERIC \
  -DCP2K_ENABLE_FFTW3_OPENMP_SUPPORT=ON -DBUILD_SHARED_LIBS=OFF
cmake --build build --target cp2k-bin qs_ot_complex_ref_unittest \
  kpoint_smearing_unittest qs_ot_minimizer_unittest \
  low_rank_preconditioner_unittest ot_covariant_preconditioner_unittest \
  kpoint_lattice_fft_unittest --parallel "$SLURM_CPUS_PER_TASK"
cp build/CMakeCache.txt provenance/CMakeCache.txt
cp build/compile_commands.json provenance/compile_commands.json 2>/dev/null || true
ldd build/bin/cp2k.psmp > provenance/linked-libraries.txt
sha256sum build/bin/cp2k.psmp > provenance/binary-sha256.txt
build/bin/cp2k.psmp --version > provenance/cp2k-version.txt
touch build-complete
