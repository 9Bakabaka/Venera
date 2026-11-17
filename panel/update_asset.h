// SPDX-License-Identifier: MIT
#pragma once

#include "../pkg/architecture.h"

#include <string>
#include <string_view>

namespace panel {

// Artifact names have no extension; release assets end in .exe. Architectureless
// names are the x64 format published before architecture-specific builds existed.
inline std::wstring installerAssetVersion(std::wstring_view name, venera::Architecture arch,
                                         std::wstring_view extension)
{
    constexpr std::wstring_view prefix = L"venera-setup-";
    if (!name.starts_with(prefix) || !name.ends_with(extension))
        return {};
    name.remove_prefix(prefix.size());
    name.remove_suffix(extension.size());
    if (name.ends_with(L"-x64")) {
        if (arch != venera::Architecture::x64)
            return {};
        name.remove_suffix(4);
    } else if (name.ends_with(L"-arm64")) {
        if (arch != venera::Architecture::arm64)
            return {};
        name.remove_suffix(6);
    } else if (arch != venera::Architecture::x64) {
        return {};
    }
    if (name.empty() || name.find_first_not_of(L"0123456789abcdef.") != std::wstring_view::npos)
        return {};
    return std::wstring(name);
}

}  // namespace panel
