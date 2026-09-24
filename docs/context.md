# Project Context

Last updated: August 15, 2026
Purpose: persistent, standalone context for this project. If chat history is
ever lost, read this file first — it should be enough to reconstruct where
things stand without re-deriving anything.

---

## What this project is

An academic RISC-V processor project. Baseline core: **Shakti C-Class**
(chosen over the alternative option, PicoRV32 — see `decisions.md` for
why). Goal: understand the core deeply enough to extend it with a custom
ISA extension aimed at **edge video anomaly detection** — i.e., a
low-power device that watches video and flags unusual events, with some
of the compute accelerated via custom RISC-V instructions rather than
generic software.

Team: 4 people sharing this Claude account/session history.
User for this session: c2s (c2smainproject@outlook.com).
Machine: kevin's laptop, Windows 11 + WSL2 Ubuntu. Repo lives natively in
WSL at `~/projects/c-class` (NOT under `/mnt/d/...` — building there fails,
see `SHAKTI-SETUP-LOG.md`). A synced copy of docs lives on the Windows D:
drive at `D:\kevin stuff\Brave_Downloads\mainproject\docs\`.

Guiding philosophy (from the project brief): don't implement before
understanding, prefer the smallest viable modification, prove correctness
before optimizing for performance.

---

## ⏸ CHECKPOINT (Aug 13, 2026) — resume here

Work is paused mid-design on the second real instruction (packed
byte-wise absolute-difference, `rd = |rs1 - rs2|` per byte lane — the
frame-differencing primitive for anomaly detection). **Nothing has been
written to any `.bsv` file yet for this instruction** — we're still at the
design-decision stage. Here's exactly where we left off:

- We discovered the 4-bit ALU `fn` code space is now **fully exhausted**
  (all 16 values 0-15 claimed, the last free one used by `ADDP1`'s
  `FNADDP1=9`). This means the new instruction can't just reuse `ADDP1`'s
  pattern of "find a free fn code" — there isn't one.
- Two resolution options were discussed in depth:
  - **Option A**: widen the `fn` field from `Bit#(4)` to `Bit#(5)`
    everywhere it flows through the pipeline. More invasive — touches an
    existing type used by many instructions, likely including pipeline
    register/struct definitions between decode and execute stages (not
    just the two `function`s we've edited so far).
  - **Option B**: don't touch the existing `fn` mechanism at all; handle
    custom instructions through a separate path. Two sub-flavors:
    - **B1**: reuse one `fn` code (e.g. `fn=9`) as a generic "this is a
      custom instruction, go check the raw instruction bits" signal, and
      add a parameter (funct7 or the full instruction word) to
      `fn_base_alu`'s existing signature so it can disambiguate internally.
      Touches an existing, widely-called function signature.
    - **B2** *(current leaning — not yet decided for certain)*: add a
      brand-new sibling function (`fn_custom_alu` or similar) that custom
      instructions get routed to instead of `fn_base_alu`, with the
      routing decision made at whatever pipeline-stage module currently
      calls `fn_base_alu`. Keeps `fn_base_alu` and every existing caller
      **completely untouched** — new code only, matching the same
      "purely additive" safety property that made `ADDP1` easy to trust.
- **Immediate next action when resuming**: go find the actual call site
  of `fn_base_alu` (almost certainly inside a Stage 3 / Execute pipeline
  `module`, not a plain `function` — meaning it'll be `rule`-based code we
  haven't looked at yet) to confirm (a) the raw instruction word is
  available there to pass into a new `fn_custom_alu`, and (b) how to
  cleanly add the dispatch branch. This reconnaissance hasn't been done
  yet — it's the literal next step.
- A small reference doc was also created this session:
  `BLUESPEC-BSV-PRIMER.md` — explains what BSV/`bsc` actually is (a
  build-time compiler to Verilog, not something active during
  simulation), and the handful of BSV concepts relevant to this
  codebase (`function` vs `module`/`rule`, `Bit#(n)`, `` `define ``
  macros, `case ... matches`, `Vector#(n,t)`). Worth reading before
  diving into the Stage 3 module, since that'll be our first time
  working with `module`/`rule` code instead of plain `function`s.

## Current state of the work (as of Aug 13, 2026)

**Fully done:**
1. Shakti C-Class builds and runs in simulation on this machine (WSL2
   Ubuntu, native filesystem). Full toolchain working: `bsc` (prebuilt
   binary), Verilator, `soc_config`/`repomanager`, RISC-V GNU toolchain,
   `elf2hex` (the correct `riscv-fesvr` one, not SiFive's).
2. Verified the core's baseline correctness by compiling and running the
   official `add.S` RISC-V compliance test through the simulator and
   reading the raw instruction trace (`rtl.dump`) by hand — confirmed
   fetch → decode → execute → writeback all work correctly for a real
   instruction.
3. Designed and implemented a proof-of-concept **custom instruction**:
   `ADDP1` (`rd = rs1 + rs2 + 1`), using the unclaimed RISC-V `custom-1`
   opcode (`0101011`). Added via 4 small additive edits across
   `src/decoder.defines`, `src/decoder.bsv` (two functions), and
   `src/base_alu.bsv` — nothing existing was modified. Rebuilt the core
   and verified via trace: `x3 = 0x3` after executing our instruction on
   `x1=1, x2=1`, proving the full custom-instruction pipeline (encode →
   decode → ALU → writeback) works end to end. This was a **toy
   proof-of-concept**, not the real project deliverable.
4. **Waveform (VCD) tracing enabled** (Aug 15, 2026). Added `--trace` to
   `VERILATOR_FLAGS` in `makefile.inc`; the testbench already had VCD
   support built in and just needed the compile flag. Run with
   `./out +trace +rtldump` from `bin/` (after `mkdir -p logs`), view via
   `gtkwave logs/vlt_dump.vcd`. Base-ALU output FIFO is at
   `TOP > mkTbSoc > soc > ccore_0 > riscv > ff_baseout` — watch `ENQ`
   (result-written pulse) and `D_IN[79:0]` (the value). Verified working;
   real commit events visible. **Open limitation:** can't yet correlate a
   waveform timestamp to a *specific* instruction — 1 cycle = 10 ps in the
   VCD, but `rtl.dump` is a per-commit log with no cycle field, so there's
   no direct mapping. Full detail in `SHAKTI-SETUP-LOG.md` section 10.
5. Documented Shakti's actual architecture (not generic docs — pulled
   real values from our own build's `core64.yaml`/`rv64i_isa.yaml`/
   `makefile.inc`) and wrote up why Shakti was chosen over other cores,
   plus an honest limitations analysis for the video-anomaly-detection use
   case. See `SHAKTI-ARCHITECTURE-AND-RATIONALE.md`.

**Not yet done / open:**
1. **The real instruction design.** `ADDP1` proved the mechanism works;
   it is not useful for anomaly detection. Next real step: decide what
   actual operation the anomaly-detection pipeline needs accelerated
   (candidates discussed: multiply-accumulate for convolution, a
   SIMD/vector-style op for batched pixel processing, saturating
   arithmetic, a threshold/compare op) and design + implement that using
   the same 7-step recipe (documented in chat, not yet written to a file
   — see "Recipe for adding a new instruction" below).
2. Hardening `ADDP1` itself with more test cases (negative numbers,
   overflow) — optional, low priority now that the mechanism is proven.
3. No vector/SIMD extension exists on this core — identified as the
   single biggest architectural gap for the actual anomaly-detection
   workload. Any parallelism will have to be hand-built.
4. Camera/video/DMA input path — the base SoC has no such peripheral;
   would need a custom AXI peripheral if a real capture pipeline is
   needed later.
5. `spike` (reference ISA simulator) was never installed — `make test`'s
   automated pass/fail harness doesn't work; we've been manually
   compiling tests and reading `rtl.dump` by hand instead. Fine for now,
   but would need revisiting for a larger test suite.

---

## Key file locations

**Windows-visible docs (this folder):**
- `SHAKTI-SETUP-LOG.md` — full, reproducible build log: every command run
  to get from a fresh WSL install to a working simulator, every error hit
  and how it was fixed, and the custom-instruction build/test recipe with
  exact commands. This is the "how to redo everything from scratch" doc.
- `SHAKTI-ARCHITECTURE-AND-RATIONALE.md` — what C-Class actually is
  (architecture, verified against our real build config), why it was
  chosen over PicoRV32/Rocket/BOOM/CVA6/VexRiscv, and a full limitations
  analysis for the anomaly-detection use case.
- `context.md` — this file.
- `decisions.md` — decision log with reasoning, see that file.

**WSL (where the actual repo and build live):**
- `~/projects/c-class` — the real, buildable repo (native WSL filesystem,
  not `/mnt/d/...`).
- `~/projects/c-class/src/decoder.defines`, `decoder.bsv`, `base_alu.bsv`
  — where `ADDP1` was added; the template for adding future instructions.
- `~/projects/c-class/bin/out` — the built simulator executable. **Must be
  run from inside `bin/`**, not the repo root (relative-path lookups for
  `boot.LSB`/`boot.MSB`/`code.mem` will silently fail otherwise).
- `~/shakti-venv` — Python venv for `soc_config`/`repomanager`; must
  `source ~/shakti-venv/bin/activate` in every new terminal.
- `~/bsc-2026.01-ubuntu-22.04/bin` — the Bluespec compiler; must be on
  `PATH` (already added to `~/.bashrc`).

---

## Recipe for adding a new custom instruction (quick reference)

Full detail is in chat history and `SHAKTI-SETUP-LOG.md` section 9. Short
version:

1. Pick an opcode from RISC-V's reserved custom space (`custom-1`,
   `0101011`, is the one we've used and confirmed clean/unclaimed in this
   decoder — `custom-0`/`custom-2` are not clean, they overlap existing
   wildcard patterns).
2. Design the encoding (which instruction format — R-type, I-type, etc. —
   and which bits are fixed vs. operand fields).
3. Edit `decoder.defines` (new instruction bit-pattern + new ALU
   function-select constant if needed), `decoder.bsv`'s
   `fn_decode_insttype` (classify the instruction category) and
   `fn_decode_fn` (pick the ALU op code), and `base_alu.bsv`'s
   `fn_base_alu` (implement the computation) — or the relevant
   execute-stage file if the instruction isn't a simple ALU op.
4. Check whether `fn_decode_rs1type`/`rs2`/`rs2type`/`rdtype` need changes
   (only if using non-standard operand types like floating-point
   registers or memory).
5. `make generate_verilog && make link_verilator` to rebuild.
6. Hand-encode a test via `.word 0x...` (gcc doesn't know custom
   mnemonics) inside an RVTEST-macro-based assembly test.
7. Compile → `elf2hex ... > code.mem` (redirect, no filename arg) → run
   `bin/out +rtldump` **from inside `bin/`** → grep `rtl.dump` for the
   instruction's hex word and verify the register result.

---

## How to resume if this chat is lost

1. Read this file, then `decisions.md`, then skim
   `SHAKTI-SETUP-LOG.md`'s section headers for anything not summarized
   here.
2. Confirm the WSL environment still works:
   ```
   cd ~/projects/c-class
   source ~/shakti-venv/bin/activate
   export PATH=$HOME/bsc-2026.01-ubuntu-22.04/bin:$PATH
   cd bin && timeout 20 ./out +rtldump && wc -l rtl.dump
   ```
   A large `rtl.dump` (six digits of lines) confirms the core still
   builds/runs correctly.
3. Pick up at "Not yet done / open" above — the real next step is
   deciding the actual target instruction for the anomaly-detection
   workload, not more toy instructions.
