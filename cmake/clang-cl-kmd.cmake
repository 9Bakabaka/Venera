# Cross toolchain for the kernel driver: clang-cl and lld-link from the dev shell, WDK kernel headers and
# libraries from refs/winkits. A kernel driver links no user-mode C runtime, so no MSVC installation is involved.
set(CMAKE_SYSTEM_NAME Windows)
set(VENERA_TARGET_ARCH "x64" CACHE STRING "Windows guest architecture (x64 or arm64)")
set_property(CACHE VENERA_TARGET_ARCH PROPERTY STRINGS x64 arm64)
if(VENERA_TARGET_ARCH STREQUAL "x64")
  set(CMAKE_SYSTEM_PROCESSOR AMD64)
  set(kmd_target x86_64-pc-windows-msvc)
elseif(VENERA_TARGET_ARCH STREQUAL "arm64")
  set(CMAKE_SYSTEM_PROCESSOR ARM64)
  set(kmd_target aarch64-pc-windows-msvc)
else()
  message(FATAL_ERROR "Unsupported VENERA_TARGET_ARCH: ${VENERA_TARGET_ARCH}; expected x64 or arm64")
endif()
# CMake reuses the toolchain for compiler checks in a separate project.
list(APPEND CMAKE_TRY_COMPILE_PLATFORM_VARIABLES VENERA_TARGET_ARCH)

set(CMAKE_C_COMPILER "$ENV{VENERA_CLANG_CL}")
set(CMAKE_CXX_COMPILER "$ENV{VENERA_CLANG_CL}")
set(CMAKE_RC_COMPILER "$ENV{VENERA_LLVM_RC}")
set(CMAKE_LINKER "$ENV{VENERA_LLD_LINK}")
set(CMAKE_AR "$ENV{VENERA_LLVM_LIB}")
set(CMAKE_C_COMPILER_TARGET "${kmd_target}")
set(CMAKE_CXX_COMPILER_TARGET "${kmd_target}")

# Compiler checks would link a user-mode program against a CRT we do not have.
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)
