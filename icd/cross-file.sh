#!/bin/sh
# SPDX-License-Identifier: MIT
# Write Mesa's Meson cross file for one Windows ABI.
# Usage: cross-file.sh <output> <x64|x86|arm64> <SDK shared headers>
set -eu
out=$1 arch=$2 sdk_shared=$3
mcfg_include= mcfg_lib= bin=
case "$arch" in
    x64)
        triple=x86_64-w64-mingw32 cpu_family=x86_64 cpu=x86_64 cc=gcc cxx=g++
        mcfg_include=${VENERA_MINGW_MCFG_INCLUDE:-} mcfg_lib=${VENERA_MINGW_MCFG_LIB:-}
        ;;
    x86)
        triple=i686-w64-mingw32 cpu_family=x86 cpu=i686 cc=gcc cxx=g++
        mcfg_include=${VENERA_MINGW32_MCFG_INCLUDE:-} mcfg_lib=${VENERA_MINGW32_MCFG_LIB:-}
        ;;
    arm64)
        triple=aarch64-w64-mingw32 cpu_family=aarch64 cpu=aarch64 cc=clang cxx=clang++
        if [ -n "${VENERA_LLVM_MINGW_ROOT:-}" ]; then bin=$VENERA_LLVM_MINGW_ROOT/bin/; fi
        ;;
    *) echo "icd: unsupported target architecture '$arch' (expected x64, x86 or arm64)" >&2; exit 1 ;;
esac
launcher=
if command -v ccache >/dev/null; then launcher="'ccache', "; fi
c_args="'-idirafter', '$sdk_shared'" cpp_args= link_args=
if [ -n "$mcfg_include" ]; then
    c_args="'-isystem', '$mcfg_include', $c_args"
    cpp_args="'-isystem', '$mcfg_include'"
fi
if [ -n "$mcfg_lib" ]; then link_args="'-L$mcfg_lib', "; fi
cat > "$out" <<EOF
[binaries]
c = [${launcher}'$bin$triple-$cc']
cpp = [${launcher}'$bin$triple-$cxx']
ar = '$bin$triple-ar'
strip = '$bin$triple-strip'
windres = '$bin$triple-windres'

[built-in options]
c_args = [$c_args]
cpp_args = [$cpp_args]
c_link_args = [${link_args}'-static', '-static-libgcc']
cpp_link_args = [${link_args}'-static', '-static-libgcc', '-static-libstdc++']

[properties]
needs_exe_wrapper = true

[host_machine]
system = 'windows'
cpu_family = '$cpu_family'
cpu = '$cpu'
endian = 'little'
EOF
