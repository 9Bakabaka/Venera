# SPDX-License-Identifier: MIT
cmake_minimum_required(VERSION 3.24)
project(venera-host-tests LANGUAGES CXX)

enable_testing()
find_package(Python3 REQUIRED COMPONENTS Interpreter)

add_executable(package-architecture package_architecture.cpp)
target_compile_features(package-architecture PRIVATE cxx_std_20)
add_test(NAME package-architecture COMMAND package-architecture)
add_test(NAME package-validation
    COMMAND "${CMAKE_COMMAND}" -E env "CMAKE=${CMAKE_COMMAND}"
            "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/test_package.py" -v)
