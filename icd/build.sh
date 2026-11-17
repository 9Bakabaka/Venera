#!/bin/sh
# SPDX-License-Identifier: MIT
# Builds yttrium's Mesa drivers for the guest from the pinned Mesa fork (third_party/virtio-win-mesa) with
# icd/patches/*.patch applied, cross-compiled with MinGW GCC (x64/x86) or LLVM-MinGW (ARM64): the Venus Vulkan driver
# (venera_vulkan_virtio.dll) and the OpenGL driver (viogpu_wgl.dll: WGL on zink, so OpenGL runs on Venus too), each
# for x86_64 and, for 32-bit processes, for i686 (venera_vulkan_virtio_32.dll, viogpu_wgl_32.dll).
#
#   icd/build.sh [build-dir] [x64|arm64]      (default build/icd, x64; run inside nix develop)
#
# The submodule stays pristine: the build compiles an exported copy with the patches applied.
set -eu

root=$(cd "$(dirname "$0")/.." && pwd)
out=${1:-$root/build/icd}
arch=${2:-x64}
case "$arch" in
    x64|arm64) ;;
    *) echo "icd: unsupported target architecture '$arch' (expected x64 or arm64)" >&2; exit 1 ;;
esac
mkdir -p "$out"
out=$(cd "$out" && pwd)
# Meson caches the target compiler. A build directory belongs to one native ABI.
if [ -f "$out/.target-arch" ] && [ "$(cat "$out/.target-arch")" != "$arch" ]; then
    echo "icd: $out belongs to $(cat "$out/.target-arch"); use a separate directory for $arch" >&2
    exit 1
fi
if [ ! -f "$out/.target-arch" ] && { [ -f "$out/meson/build.ninja" ] || [ -f "$out/meson32/build.ninja" ]; }; then
    echo "icd: $out contains an existing build without target ABI metadata; use a separate build directory" >&2
    exit 1
fi
printf '%s\n' "$arch" > "$out/.target-arch"
mesa=$root/third_party/virtio-win-mesa
src=$out/src

# The meson options; changing them rebuilds from scratch. SPIRV-Tools only prints SPIR-V for debugging, and the
# dev shell's is a Linux library.
options="--buildtype=release -Db_ndebug=true -Dc_std=c11 \
    -Dplatforms=windows -Dvulkan-drivers=virtio -Dgallium-drivers=zink -Dgallium-yttrium=true \
    -Dopengl=true -Dgallium-wgl-dll-name=viogpu_wgl \
    -Dgles1=disabled -Dgles2=disabled -Degl=disabled -Dglx=disabled -Dgbm=disabled \
    -Dllvm=disabled -Dzlib=disabled -Dzstd=disabled -Dexpat=disabled -Dvalgrind=disabled \
    -Dlibunwind=disabled -Dbuild-tests=false -Dvideo-codecs= -Dmicrosoft-clc=disabled \
    -Dspirv-tools=disabled"

stamp="$(git -C "$mesa" rev-parse HEAD) $options"
for p in "$root"/icd/patches/*.patch; do
    stamp="$stamp $(sha256sum "$p" | cut -d' ' -f1)"
done
if [ ! -f "$src/.stamp" ] || [ "$(cat "$src/.stamp")" != "$stamp" ]; then
    rm -rf "$src" "$out/meson" "$out/meson32"
    mkdir -p "$src"
    git -C "$mesa" archive HEAD | tar -x -C "$src"
    for p in "$root"/icd/patches/*.patch; do
        echo "icd: applying $(basename "$p")"
        (cd "$src" && patch -p1 --forward --quiet < "$p")
    done
    echo "$stamp" > "$src/.stamp"
fi

# d3dkmthk.h and friends, which MinGW lacks, from the SDK after MinGW's own headers (as for the UMD).
sdk_shared=$root/refs/winkits/sdk/c/Include/10.0.26100.0/shared
# Builds the two drivers for one architecture into $out/<build> and copies them to $out with a suffix:
#   build_arch <build> <arch> <suffix>
# GCC from nixpkgs uses the mcfgthread model; link it and the GCC runtime statically, as the UMD does.
build_arch() {
    build=$out/$1 target=$2 suffix=$3
    sh "$root/icd/cross-file.sh" "$out/cross$suffix.ini" "$target" "$sdk_shared"

    if [ ! -f "$build/build.ninja" ]; then
        # shellcheck disable=SC2086 # word splitting intended: the options list
        meson setup "$build" "$src" --cross-file "$out/cross$suffix.ini" $options
    fi
    ninja -C "$build" src/virtio/vulkan/libvulkan_virtio.dll src/gallium/targets/wgl/viogpu_wgl.dll
    # Installed next to venera_d3d12$suffix.dll under the name the UMD looks for.
    cp "$build/src/virtio/vulkan/libvulkan_virtio.dll" "$out/venera_vulkan_virtio$suffix.dll"
    cp "$build/src/gallium/targets/wgl/viogpu_wgl.dll" "$out/viogpu_wgl$suffix.dll"
    echo "icd: $out/venera_vulkan_virtio$suffix.dll $out/viogpu_wgl$suffix.dll"
}

build_arch meson "$arch" ""
build_arch meson32 x86 _32
