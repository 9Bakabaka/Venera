// SPDX-License-Identifier: MIT
// PE machine identifiers, shared by setup and the updater. A package always targets
// the native Windows architecture, even when its installer can run under emulation.
#pragma once

namespace venera {

enum class Architecture : unsigned short { unknown = 0, x86 = 0x014c, x64 = 0x8664, arm64 = 0xaa64 };

constexpr Architecture targetArchitecture()
{
#if defined(_M_ARM64) || defined(__aarch64__)
    return Architecture::arm64;
#elif defined(_M_X64) || defined(__x86_64__)
    return Architecture::x64;
#else
#error Venera setup and panel require an x64 or ARM64 target
#endif
}

constexpr const wchar_t* architectureName(Architecture arch)
{
    switch (arch) {
    case Architecture::x86: return L"x86";
    case Architecture::x64: return L"x64";
    case Architecture::arm64: return L"arm64";
    default: return L"unknown";
    }
}

constexpr bool packageMatchesNative(Architecture package, Architecture native)
{
    return (package == Architecture::x64 || package == Architecture::arm64) && package == native;
}

}  // namespace venera
