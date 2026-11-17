// SPDX-License-Identifier: MIT
#pragma once
#include <windows.h>

namespace venera::umd {

#if defined(_WIN64)
namespace detail {
inline bool unwind_leaf(CONTEXT& ctx)
{
#if defined(_M_ARM64) || defined(__aarch64__)
    if (ctx.Pc == ctx.Lr)
        return false;
    ctx.Pc = ctx.Lr;
    // The new PC is a return address, rather than a suspended instruction.
    // ARM64's unwinder needs this distinction at tail-call boundaries.
    ctx.ContextFlags |= CONTEXT_UNWOUND_TO_CALL;
#else
    SIZE_T got = 0;
    DWORD64 caller = 0;
    if (!ReadProcessMemory(GetCurrentProcess(), reinterpret_cast<LPCVOID>(ctx.Rsp), &caller, sizeof(caller), &got) ||
        got != sizeof(caller))
        return false;
    ctx.Rip = caller;
    ctx.Rsp += sizeof(caller);
#endif
    return true;
}
} // namespace detail
#endif

// Allocation-free: callers may be walking a thread which holds the heap lock.
inline unsigned walk_stack(CONTEXT ctx, DWORD64* frames, unsigned capacity)
{
    unsigned n = 0;
#if defined(_WIN64)
#if defined(_M_ARM64) || defined(__aarch64__)
    auto& pc = ctx.Pc;
    auto& sp = ctx.Sp;
#else
    auto& pc = ctx.Rip;
    auto& sp = ctx.Rsp;
#endif
    // A call through a null function pointer still has a valid caller.
    if (!capacity || (!pc && !detail::unwind_leaf(ctx)))
        return 0;
    while (n < capacity && pc) {
        frames[n++] = pc;
        const DWORD64 previous_pc = pc, previous_sp = sp;
        DWORD64 base = 0;
        if (PRUNTIME_FUNCTION fn = RtlLookupFunctionEntry(pc, &base, nullptr)) {
            void* handler_data = nullptr;
            DWORD64 establisher = 0;
            RtlVirtualUnwind(UNW_FLAG_NHANDLER, base, pc, fn, &ctx, &handler_data, &establisher, nullptr);
        } else if (n == 1) {
            if (!detail::unwind_leaf(ctx))
                break;
        } else {
            break;
        }
        if (pc == previous_pc && sp == previous_sp)
            break;
    }
#else
    if (!ctx.Eip || !capacity)
        return 0;
    frames[n++] = ctx.Eip;
    DWORD ebp = ctx.Ebp;
    while (n < capacity && ebp >= ctx.Esp && !(ebp & 3)) {
        DWORD frame[2];
        SIZE_T got = 0;
        if (!ReadProcessMemory(GetCurrentProcess(), reinterpret_cast<LPCVOID>(ebp), frame, sizeof(frame), &got) ||
            got != sizeof(frame) || !frame[1])
            break;
        frames[n++] = frame[1];
        if (frame[0] <= ebp)
            break;
        ebp = frame[0];
    }
#endif
    return n;
}

} // namespace venera::umd
