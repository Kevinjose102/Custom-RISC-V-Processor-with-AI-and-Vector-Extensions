# Bluespec (BSV) Primer

Last updated: August 13, 2026
Purpose: a small, project-focused reference for the language Shakti C-Class
is actually written in — enough to read and safely edit the files we've
been touching (`decoder.bsv`, `base_alu.bsv`, etc.), not a full language
course.

---

## What BSV actually is

BSV (Bluespec SystemVerilog) is a hardware description language — a
different language from plain Verilog/SystemVerilog, despite the similar
name and some shared syntax. It's used to *describe* hardware; it is not
something that runs live when the core executes.

**The build pipeline, in order:**

```
BSV source (.bsv files)
   |  compiled by: bsc (Bluespec compiler)
   v
Structural Verilog (.v files, in build/hw/verilog/)
   |  compiled by: Verilator
   v
C++ simulation executable (bin/out)
   |  this is what actually runs when you do ./out +rtldump
   v
rtl.dump (the trace we read)
```

**Key point:** by the time you run `bin/out`, BSV and `bsc` are completely
out of the picture. You're running compiled C++ that behaves like the
hardware. BSV's whole job is happening earlier and once — turning a
high-level hardware description into a fixed, synthesizable Verilog netlist.

## Why Shakti uses BSV instead of plain Verilog

BSV's type system and its rule-based execution model catch certain classes
of bugs at compile time — like two pieces of logic implicitly racing to
drive the same signal in the same cycle — that plain Verilog would only
surface later, in simulation or (worse) in real silicon. For a design this
size (6 pipeline stages, caches, FPU, debug module, AXI fabric), that
compile-time safety net is a big part of why the whole thing was tractable
to build as an open-source academic/research project in the first place.

## Concepts you'll actually run into in this codebase

**`function` — pure combinational logic.** Most of what we've edited so
far (`fn_decode_insttype`, `fn_decode_fn`, `fn_base_alu`, `fn_add`) are
BSV `function`s — they take inputs, return an output, have no internal
state, and get compiled straight into combinational Verilog logic
(wires/muxes), not registers. This is why our `ADDP1` edits were "just"
adding cases to `case` statements inside functions — no clocking, no state
machine changes involved.

```bsv
function Bit#(4) fn_decode_fn(Bit#(32) inst, CSRtoDecode csrs);
  ...
endfunction
```

**`module` — stateful hardware with rules.** Elsewhere in the codebase
(the actual pipeline stages, caches, register file) you'll see `module`
definitions instead — these can hold registers (`Reg#(...)`), FIFOs, and
`rule`s, which are BSV's mechanism for describing clocked, conditional
actions ("when this condition holds, do this state update"). We haven't
needed to touch any of these yet, since `ADDP1` was purely combinational
logic living inside existing `function`s.

**`Bit#(n)` — a fixed-width bit vector.** The core numeric type in BSV.
`Bit#(4)` is a 4-bit value (this is exactly the `fn` ALU-selector type we
ran out of room in), `Bit#(32)` is a full instruction word, `` Bit#(`xlen) ``
is a full register-width value (64 in our build, via the `` `xlen `` macro
defined at compile time in `makefile.inc`'s `BSC_DEFINES`).

**`` `define `` and backtick-macros — compile-time constants.** Things
like `` `FNADD ``, `` `ADDP1_INSTR ``, `` `xlen `` are preprocessor macros
(from `decoder.defines`), resolved by `bsc` before real compilation — this
is the same C-style preprocessor mechanism, not a BSV-specific language
feature. This is exactly what we added two lines to when we defined
`FNADDP1` and `ADDP1_INSTR`.

**`case (inst) matches` — pattern matching on bits.** This is how the
decoder recognizes instructions: each `` `SOMETHING_INSTR `` macro expands
to a bit-pattern template (fixed bits + `?` wildcards for operand fields),
and `matches` checks the actual fetched instruction word against each
template in order. This is the exact mechanism `fn_decode_insttype` and
`fn_decode_fn` use, and where we added our `` `ADDP1_INSTR `` case.

**`Vector#(n, t)` — fixed-size arrays of typed elements.** From the
`Vector` library (`import Vector::*`), used for things like packing/
unpacking a wide bit-vector into byte lanes. This is what our *next*
planned instruction (packed absolute-difference) will lean on — splitting
a 64-bit register into 8 independent `Bit#(8)` byte lanes via
`Vector#(8, Bit#(8)) v = unpack(op1);`, operating on each lane, then
`pack`ing the result back into a `Bit#(64)`. `fn_add` already uses a
related Vector-library function (`duplicate`), so the library is already
imported in `base_alu.bsv`.

**`interface` — the "ports" a module exposes.** Defines what
methods/values a `module` makes available to whatever instantiates it —
roughly analogous to a Verilog module's port list, but with proper types
and method semantics rather than raw wires. We haven't had to define one
yet, since all our edits have been inside existing `function`s and `case`
statements, not new modules.

## What this means practically for future edits

Every edit we've made so far, and the `ADDP1` proof-of-concept in general,
stayed entirely inside the "pure `function`, combinational logic, add a
`case`" category — which is why it was safe, small, and easy to verify.
The moment a future instruction needs *state that persists across cycles*
(e.g. a genuine multi-cycle MAC accumulator, not just a single-cycle ALU
op), we'd be stepping into `module`/`rule`/`Reg#(...)` territory instead —
a meaningfully bigger kind of change, and worth flagging explicitly when
we get there rather than discovering it mid-edit.

## Quick vocabulary reference

| BSV term | Rough Verilog equivalent | Where we've seen it |
|---|---|---|
| `function` | combinational logic (assign/always_comb) | `fn_decode_fn`, `fn_base_alu`, `fn_add` |
| `module` + `rule` | clocked always_ff block with conditions | pipeline stages, caches (not yet edited) |
| `Bit#(n)` | `[n-1:0]` wire/reg | everywhere |
| `` `define `` | `` `define `` (same, it's the preprocessor) | `decoder.defines` |
| `case ... matches` | `casez`/`case` with wildcard patterns | `fn_decode_insttype`, `fn_decode_fn` |
| `Vector#(n,t)` | packed array `[n-1:0]` of `t`-wide elements | `fn_add` (`duplicate`), planned abs-diff instruction |
| `interface` | module port list | not yet touched |
