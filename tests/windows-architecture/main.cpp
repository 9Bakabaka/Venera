// SPDX-License-Identifier: MIT
#include "../../umd/common/stack_walk.h"
#include "../../pkg/architecture.h"
#include "../win/trace_clock.h"
#include <cstdio>
#include <cstring>

#define CHECK(condition) do { if (!(condition)) { std::fprintf(stderr, "line %d: %s\n", __LINE__, #condition); return 1; } } while (0)

int main()
{
    using namespace venera;
    USHORT process_machine = 0, native_machine = 0;
    CHECK(IsWow64Process2(GetCurrentProcess(), &process_machine, &native_machine));
    CHECK(packageMatchesNative(targetArchitecture(), static_cast<Architecture>(native_machine)));
    CONTEXT context{};
    context.ContextFlags = CONTEXT_FULL;
    RtlCaptureContext(&context);
    DWORD64 frames[32]{};
    CHECK(umd::walk_stack(context, frames, 0) == 0);
    CHECK(umd::walk_stack(context, frames, 1) == 1);
    const unsigned n = umd::walk_stack(context, frames, 32);
    CHECK(n >= 2 && n <= 32);
    CHECK(frames[0] && frames[1] && frames[0] != frames[1]);
#if defined(_M_ARM64) || defined(__aarch64__)
    CHECK(trace_clock::client_context == 1);
    CHECK(std::strcmp(trace_clock::name, "qpc") == 0);
    CHECK(frames[0] == context.Pc);
    // An address with no unwind entry models a leaf: ARM64 must return via LR,
    // with no stack read. A repeated PC must terminate instead of looping.
    CONTEXT leaf{};
    leaf.Pc = 1;
    leaf.Lr = 2;
    CHECK(umd::walk_stack(leaf, frames, 32) == 2);
    CHECK(frames[0] == 1 && frames[1] == 2);
    leaf.Lr = 1;
    CHECK(umd::walk_stack(leaf, frames, 32) == 1);
    leaf.Pc = 0;
    leaf.Lr = 2;
    CHECK(umd::walk_stack(leaf, frames, 32) == 1 && frames[0] == 2);
    leaf = context;
    leaf.Lr = context.Pc;
    leaf.Pc = 1;
    CHECK(umd::walk_stack(leaf, frames, 32) >= 3);
    // A return address needs the unwind-to-call state for a subsequent metadata
    // unwind, while the stack pointer and existing context flags stay intact.
    leaf.ContextFlags = CONTEXT_FULL;
    leaf.Pc = 1;
    leaf.Lr = 2;
    leaf.Sp = 0x10;
    CHECK(umd::detail::unwind_leaf(leaf));
    CHECK(leaf.Pc == 2 && leaf.Sp == 0x10);
    CHECK((leaf.ContextFlags & CONTEXT_UNWOUND_TO_CALL) != 0);
    CHECK((leaf.ContextFlags & CONTEXT_FULL) == CONTEXT_FULL);
    leaf.Pc = leaf.Lr;
    CHECK(!umd::detail::unwind_leaf(leaf));
    LARGE_INTEGER frequency;
    QueryPerformanceFrequency(&frequency);
    CHECK(trace_clock::frequency() == static_cast<double>(frequency.QuadPart));
#else
    CHECK(trace_clock::client_context == 3);
    CHECK(std::strcmp(trace_clock::name, "tsc") == 0);
    CHECK(frames[0] == context.Rip);
    CONTEXT leaf{};
    DWORD64 return_address = 2;
    leaf.Rsp = reinterpret_cast<DWORD64>(&return_address);
    CHECK(umd::walk_stack(leaf, frames, 32) == 1 && frames[0] == 2);
    leaf.Rsp = 1; // A corrupted stack must not crash the exception reporter.
    CHECK(umd::walk_stack(leaf, frames, 32) == 0);
#endif
    LARGE_INTEGER q0, q1, qf;
    QueryPerformanceFrequency(&qf);
    const double hz = trace_clock::frequency();
    QueryPerformanceCounter(&q0);
    const auto t0 = trace_clock::now();
    Sleep(100);
    const auto t1 = trace_clock::now();
    QueryPerformanceCounter(&q1);
    CHECK(t1 > t0 && hz > 0);
    const double elapsed = static_cast<double>(t1 - t0) / hz;
    const double reference = static_cast<double>(q1.QuadPart - q0.QuadPart) / qf.QuadPart;
    CHECK(elapsed > reference * 0.9 && elapsed < reference * 1.1);
    return 0;
}
