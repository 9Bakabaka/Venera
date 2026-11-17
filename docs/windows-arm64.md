# Windows on Arm

The Arm64 build targets Windows 11 Arm64 guests and keeps Venera's normal driver
model: a native WDDM kernel driver, native Venus/zink and D3D10/11/12 user-mode
drivers, resolution services, control panel and installer. The package also
contains x86 user-mode drivers for 32-bit applications. No system DLL replacement
or runtime architecture substitution is involved.

Native Arm64 and x86 applications use their respective drivers. Emulated x64
applications are outside this package's graphics support: an Arm64 DLL cannot be
loaded into an x64 process. They require a separate compatible user-mode driver
ABI, such as Arm64EC/Arm64X, throughout the graphics stack. This build does not
register the native DLLs as x64-compatible drivers. See Microsoft's
[emulation architecture](https://learn.microsoft.com/en-us/windows/arm/apps-on-arm-x86-emulation)
and [Arm64EC ABI](https://learn.microsoft.com/en-us/windows/arm/arm64ec).

## Build

Use the repository's pinned submodules and the x86_64 Linux Nix development
shell. It provides LLVM-MinGW 20251104, including its matching Arm64 CRT and C++
runtime, alongside the existing x86/x64 GCC toolchains. The LLVM-MinGW archive is
versioned and SHA256-verified by Nix. The kernel uses clang-cl's MSVC Arm64 ABI and
Microsoft's official Arm64 WDK libraries, including its kernel CRT security
helpers.

Run inside `nix develop`:

```sh
git submodule update --init --recursive
cmake/fetch-winkits.sh refs/winkits arm64
icd/build.sh build/arm64/icd arm64
cmake -S kmd -B build/arm64/kmd -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE="$PWD/cmake/clang-cl-kmd.cmake" \
  -DVENERA_TARGET_ARCH=arm64 \
  -DVENERA_KMD_SIGN_PFX=/absolute/path/to/test-signing.pfx
cmake --build build/arm64/kmd
cmake -S . -B build/arm64/win -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE=cmake/llvm-mingw-arm64.cmake \
  -DVENERA_ICD_DIR="$PWD/build/arm64/icd" \
  -DVENERA_KMD_SYS="$PWD/build/arm64/kmd/signed/viogpu3d.sys"
cmake --build build/arm64/win
```

The installer is `build/arm64/win/setup/venera-setup.exe`. The x86 drivers are
built automatically in `build/arm64/win/umd32`. Keep different native targets in
separate build directories; packaging verifies each binary's PE machine type
before producing the WIM. The WDK download cache can contain both architectures.

For a standalone LLVM-MinGW installation outside Nix, set
`VENERA_LLVM_MINGW_ROOT` to its root directory; the Arm64 CMake toolchain and Mesa
cross-file generator use the same compiler and runtime. The other tools and the
x86 MinGW GCC compiler from the development shell are still required.

## Actions

The build workflow runs independent `x64` and `arm64` jobs on Linux, builds both
complete installers, test-signs each native kernel driver, and uploads:

- `venera-setup-<version>-x64.exe` and `.iso`
- `venera-setup-<version>-arm64.exe` and `.iso`

Compiler and WDK caches are separated by guest architecture. A tagged release
publishes both sets together after the builds and tests pass. The control panel
selects updates for its own native architecture, including the executable inside
an Actions artifact ZIP.

## Tests and validation

Host checks exercise target selection, generated Meson cross files, WDK package
selection and caching, PE validation, INF generation, installer architecture
matching, update asset selection and QPC/TSC trace decoding:

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
cmake -S tests/host -B build/host -G Ninja
cmake --build build/host
ctest --test-dir build/host --output-on-failure
```

The standalone `tests/windows-architecture` project exercises native Windows
stack unwinding, Arm64 leaf/null-call handling and performance counters. Its ETW
test records and decodes real events, requires elevation, and needs no Venera
driver. Actions runs it on both native x64 and Arm64 Windows runners.

Compilation and these driver-independent tests do not validate display output,
GPU submissions, test-signature acceptance or driver loading. Validate those in
an Arm64 Windows guest with the PCI virtio GPU and Venus-enabled host described
in the main README. Use the control panel's D3D9/11/12 and Vulkan tests to check
the native driver paths, and the generated `umd32/tests/win/d3d9caps_32.exe` to
check the x86 path. Native Arm64 guest rendering has not been verified in the
development environment used for this port.

Arm64 diagnostic traces use Windows QPC, with the frequency stored in trace
metadata. `vtrace.py capture --no-host` supports these guest traces; the existing
host/guest correlation tool uses x86 KVM TSC offsets and cannot correlate QPC as
if it were a host TSC. Existing x86 TSC traces remain readable.
