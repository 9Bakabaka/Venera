// SPDX-License-Identifier: MIT
#include "../../pkg/architecture.h"
#include "../../panel/update_asset.h"

#include <cstdio>
#include <string>

#define CHECK(condition) do { if (!(condition)) { \
    std::fprintf(stderr, "line %d: %s\n", __LINE__, #condition); return 1; \
} } while (false)

int main()
{
    using venera::Architecture;
    constexpr Architecture arches[] = {Architecture::unknown, Architecture::x86, Architecture::x64,
                                       Architecture::arm64, static_cast<Architecture>(0xffff)};
    for (auto package : arches)
        for (auto native : arches)
            CHECK(venera::packageMatchesNative(package, native) ==
                  ((package == Architecture::x64 || package == Architecture::arm64) && package == native));

    CHECK(std::wstring(venera::architectureName(Architecture::arm64)) == L"arm64");
    CHECK(std::wstring(venera::architectureName(Architecture::x64)) == L"x64");
    CHECK(std::wstring(venera::architectureName(Architecture::unknown)) == L"unknown");

    const std::wstring version = L"0.2.4.123.abcdef0";
    for (auto arch : {Architecture::x64, Architecture::arm64}) {
        const std::wstring stem = L"venera-setup-" + version + L"-" + venera::architectureName(arch);
        CHECK(panel::installerAssetVersion(stem, arch, L"") == version);
        CHECK(panel::installerAssetVersion(stem + L".exe", arch, L".exe") == version);
        auto other = arch == Architecture::x64 ? Architecture::arm64 : Architecture::x64;
        CHECK(panel::installerAssetVersion(stem, other, L"").empty());
        CHECK(panel::installerAssetVersion(stem + L".exe", other, L".exe").empty());
        CHECK(panel::installerAssetVersion(stem + L".iso", arch, L".exe").empty());
        CHECK(panel::installerAssetVersion(stem + L".exe.bak", arch, L".exe").empty());
    }
    CHECK(panel::installerAssetVersion(L"venera-setup-" + version, Architecture::x64, L"") == version);
    CHECK(panel::installerAssetVersion(L"venera-setup-" + version + L".exe", Architecture::x64, L".exe") == version);
    CHECK(panel::installerAssetVersion(L"venera-setup-" + version, Architecture::arm64, L"").empty());
    for (const wchar_t* bad : {L"venera-setup--arm64.exe", L"venera-setup-../evil-arm64.exe",
                               L"venera-setup-0.2.4-arm64.zip", L"other-setup-0.2.4-arm64.exe",
                               L"venera-setup-0.2.4-x86.exe", L"venera-setup-0.2.4-arm64x.exe"})
        CHECK(panel::installerAssetVersion(bad, Architecture::arm64, L".exe").empty());
    return 0;
}
