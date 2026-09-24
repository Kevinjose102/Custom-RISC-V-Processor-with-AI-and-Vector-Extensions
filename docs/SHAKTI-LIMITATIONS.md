# Shakti C-Class: Key Limitations (Quick Reference)

Last updated: August 16, 2026
Companion to `SHAKTI-ARCHITECTURE-AND-RATIONALE.md` (Section 3 has the full
limitations list, including the missing vector/SIMD extension — the
single biggest one, and the reason our packed byte-wise absolute-difference
instruction exists). This file captures three more limitations discussed
in detail during presentation prep, with the extra reasoning/numbers
behind each — useful for answering follow-up questions directly.

---

## 1. Single-issue, in-order pipeline

Only one instruction executes per cycle, in program order — no
speculative execution, no out-of-order issue, no superscalar
parallelism. This caps overall throughput regardless of what custom
instructions get added: adding a fast instruction helps the *specific
operation* it targets, but the core still can't issue more than one
instruction per cycle overall. Shakti's own listed performance
(~1.68 DMIPS/MHz) is representative of a controller-class core, not an
inference accelerator.

## 2. Memory bottleneck (likely the dominant real-world cost)

16KB I-Cache / 16KB D-Cache, both 4-way set-associative, **no L2 cache at
all** in our build (confirmed — `core64.yaml` has no L2 section).

This matters more than it sounds like at first, because **compute
throughput is not actually the constraint** — we did the math:

- A 640×480 frame needs 38,400 packed abs-diff instructions (8 pixels/
  instruction). At even a conservative 50 MHz FPGA clock, that's well
  under 1% of available cycles per second, and processing 10 seconds of
  such video would take ~230ms of compute time alone — roughly 43× faster
  than real-time.
- So the abs-diff instruction itself is nowhere close to being the
  bottleneck. What *is* likely to dominate real runtime: getting pixel
  data into registers in the first place. Every 8-pixel load is a memory
  access, and with no L2 and only 16KB caches, if frame data doesn't fit
  in cache, memory stalls could easily dominate total processing time far
  more than the computation itself.

**Honest framing for Q&A:** "Our custom instruction's compute cost is
negligible; the real bottleneck is expected to be memory access patterns,
which we haven't measured yet." Don't claim a specific real-world speedup
number — the compute-only calculation above doesn't include memory, loop
control, or thresholding overhead.

## 3. FPU uses a software-style implementation (`bsv_float`), not
   hardware-optimized HardFloat

Confirmed via `core64.yaml`: `hardfloat: False`. The active floating-point
implementation lives in `src/fpu/bsv_float/fpu_bsvfloat.bsv` and — per
Shakti's own team — "currently uses hand-optimized iterative algorithms."

**What this means concretely:** `bsv_float` reuses one small piece of
hardware across multiple clock cycles per operation (like doing long
division by hand — one small circuit, many passes). Berkeley HardFloat,
by contrast, uses dedicated pipelined hardware — a separate physical
circuit for each step (align → compute → normalize → round), so it's
faster and has better throughput, at the cost of more chip area. Neither
is single-cycle — floating-point arithmetic (especially division)
requires multiple cycles even in fully hardware-optimized designs; the
real difference is *how many* cycles, not whether it's instant.

**Important nuance — this is a configurable trade-off, not a fixed
limitation.** The HardFloat implementation already exists in this same
C-Class repo (`src/fpu/hardfloat/`), and the Makefile is already wired to
find it — it's simply switched off (`hardfloat: False`) in our build.
Enabling it (`hardfloat: True` + regenerate config + rebuild) would very
likely resolve the speed concern at the cost of additional chip area —
**not yet tested or verified**, so don't claim it as done, only as an
available, understood option.

**Relevance to our actual work: none, currently.** Our packed byte-wise
absolute-difference instruction operates entirely on 8-bit integer pixel
values through the Base ALU — it never touches the FPU at all, regardless
of which floating-point implementation is active. This limitation only
becomes relevant if a future instruction needs to accelerate
floating-point computation (e.g., if Team 1's model uses unquantized FP32
weights rather than int8).

---

## Quick answers for panel Q&A

- **"Is compute the bottleneck?"** No — memory access almost certainly
  is, based on our own cycle-budget calculations. Compute uses under 1%
  of available cycles even at conservative clock speeds.
- **"Can you speed up the FPU?"** Yes, in principle — HardFloat is already
  in the repo, just disabled. Untested by us so far.
- **"Does the FPU limitation affect your instruction?"** No — our
  instruction is pure integer arithmetic, never touches the FPU.
