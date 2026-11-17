// SPDX-License-Identifier: MIT
#pragma once
#include <windows.h>
#include <cstdint>
#if !defined(_M_ARM64) && !defined(__aarch64__)
#include <intrin.h>
#endif

namespace venera::trace_clock {
#if defined(_M_ARM64) || defined(__aarch64__)
inline constexpr ULONG client_context = 1; // ETW's performance counter clock.
inline constexpr const char* name = "qpc";
inline uint64_t now()
{
    LARGE_INTEGER counter;
    QueryPerformanceCounter(&counter);
    return counter.QuadPart;
}
inline double frequency()
{
    LARGE_INTEGER frequency;
    QueryPerformanceFrequency(&frequency);
    return static_cast<double>(frequency.QuadPart);
}
#else
inline constexpr ULONG client_context = 3; // ETW's CPU cycle counter clock.
inline constexpr const char* name = "tsc";
inline uint64_t now() { return __rdtsc(); }
inline double frequency()
{
    LARGE_INTEGER f, q0, q1;
    QueryPerformanceFrequency(&f);
    QueryPerformanceCounter(&q0);
    const uint64_t t0 = now();
    Sleep(200);
    QueryPerformanceCounter(&q1);
    const uint64_t t1 = now();
    return static_cast<double>(t1 - t0) * f.QuadPart / (q1.QuadPart - q0.QuadPart);
}
#endif
} // namespace venera::trace_clock
