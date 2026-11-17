#!/bin/sh
# SPDX-License-Identifier: MIT
# Fetches the WDK and SDK headers and the target's kernel-mode libraries from Microsoft's NuGet packages,
# Microsoft.Windows.WDK.{x64,ARM64} and Microsoft.Windows.SDK.CPP, into refs/winkits/{wdk,sdk}.
#
#   cmake/fetch-winkits.sh [dir] [x64|arm64]      (default refs/winkits, x64)
set -eu

version=10.0.26100.6584
root=$(cd "$(dirname "$0")/.." && pwd)
out=${1:-$root/refs/winkits}
arch=${2:-x64}
if [ "$#" -gt 2 ]; then
    echo "usage: $0 [dir] [x64|arm64]" >&2
    exit 2
fi
case "$arch" in
    x64) wdk_arch=x64 ;;
    arm64) wdk_arch=ARM64 ;;
    *) echo "winkits: unsupported architecture '$arch'; expected x64 or arm64" >&2; exit 2 ;;
esac

fetch() {  # package, destination, required file, paths to extract
    package=$1 dest=$2 required=$3
    shift 3
    if [ -f "$dest/$required" ]; then
        echo "winkits: $dest exists, skipping $package"
        return
    fi
    tmp=$(mktemp -d)
    echo "winkits: downloading $package $version"
    curl -fsSL -o "$tmp/pkg.zip" "https://api.nuget.org/v3-flatcontainer/$package/$version/$package.$version.nupkg"
    mkdir -p "$dest"
    # The two WDK packages share headers; adding another target replaces those
    # identical pinned headers without an interactive overwrite prompt.
    unzip -oq "$tmp/pkg.zip" "$@" -d "$dest"
    rm "$tmp/pkg.zip"
    rmdir "$tmp"
}

fetch "microsoft.windows.wdk.$arch" "$out/wdk" "c/Lib/10.0.26100.0/km/$wdk_arch/displib.lib" \
    'c/Include/*' "c/Lib/10.0.26100.0/km/$wdk_arch/*"
fetch microsoft.windows.sdk.cpp "$out/sdk" 'c/Include/10.0.26100.0/um/Windows.h' 'c/Include/*'
