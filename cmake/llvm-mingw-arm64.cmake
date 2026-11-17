# SPDX-License-Identifier: MIT
# Native Windows on Arm user-mode binaries. LLVM-MinGW supplies a consistent
# compiler, CRT and C++ runtime for our code and all of its static dependencies.
set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_SYSTEM_PROCESSOR aarch64)
set(VENERA_MINGW_TRIPLE aarch64-w64-mingw32)

set(VENERA_LLVM_MINGW_ROOT "$ENV{VENERA_LLVM_MINGW_ROOT}" CACHE PATH "LLVM-MinGW toolchain root")
set(_venera_bin "")
if(VENERA_LLVM_MINGW_ROOT)
  set(_venera_bin "${VENERA_LLVM_MINGW_ROOT}/bin/")
endif()
set(CMAKE_C_COMPILER "${_venera_bin}${VENERA_MINGW_TRIPLE}-clang")
set(CMAKE_CXX_COMPILER "${_venera_bin}${VENERA_MINGW_TRIPLE}-clang++")
set(CMAKE_AR "${_venera_bin}${VENERA_MINGW_TRIPLE}-ar")
set(CMAKE_RANLIB "${_venera_bin}${VENERA_MINGW_TRIPLE}-ranlib")
set(CMAKE_STRIP "${_venera_bin}${VENERA_MINGW_TRIPLE}-strip")
set(CMAKE_RC_COMPILER "${_venera_bin}${VENERA_MINGW_TRIPLE}-windres")
set(VENERA_MINGW_WIDL "${_venera_bin}${VENERA_MINGW_TRIPLE}-widl")
unset(_venera_bin)

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
list(APPEND CMAKE_TRY_COMPILE_PLATFORM_VARIABLES VENERA_LLVM_MINGW_ROOT)
