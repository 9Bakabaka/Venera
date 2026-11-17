# SPDX-License-Identifier: MIT
cmake_minimum_required(VERSION 3.24)
project(venera-windows-architecture-tests LANGUAGES CXX)
if(NOT WIN32)
  message(FATAL_ERROR "These tests exercise native Windows contexts and clocks")
endif()
enable_testing()
add_executable(windows-architecture main.cpp)
target_compile_features(windows-architecture PRIVATE cxx_std_20)
target_compile_definitions(windows-architecture PRIVATE _WIN32_WINNT=0x0A00)
add_test(NAME windows-architecture COMMAND windows-architecture)

find_package(Python3 REQUIRED COMPONENTS Interpreter)
add_executable(trace-recorder ../win/venera-trace.cpp)
target_compile_features(trace-recorder PRIVATE cxx_std_20)
target_link_libraries(trace-recorder PRIVATE tdh advapi32)
add_test(NAME etw-clock
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/test_etw.py"
            "$<TARGET_FILE:trace-recorder>")
