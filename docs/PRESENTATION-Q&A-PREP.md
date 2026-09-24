# Presentation Q&A Prep — Key Terms Glossary

Last updated: August 16, 2026
Purpose: study material for the whole team before the intermediate
presentation. Every term below is explained both in general and in the
specific context of *our* project, so answers sound grounded rather than
like a textbook definition.

---

## 1. Core Concepts

### What is an ISA (Instruction Set Architecture)?
The ISA is the contract between hardware and software — the complete list
of instructions a processor understands (like `ADD`, `LOAD`, `BRANCH`),
their exact bit encodings, and the rules for how they behave. It's what
separates "x86" from "ARM" from "RISC-V" — different ISAs, different
instructions, different binary formats. Software compiled for one ISA
won't run on hardware built for a different one.

**In our project:** we're using the RISC-V ISA (specifically
`RV64IMAFDCSU_Zicsr_Zifencei` — the exact extension set our Shakti C-Class
build supports), and we've *added our own instruction* to it (`ADDP1`,
proof-of-concept), extending the ISA rather than replacing it.

### What is an "extensible" ISA?
RISC-V is deliberately designed with reserved, unclaimed regions of its
opcode space (`custom-0` through `custom-3`) specifically so anyone can
add their own instructions without conflicting with the standard ones or
needing anyone's permission. This is unlike proprietary ISAs (x86, ARM),
where you cannot legally or practically add your own instructions.

**In our project:** this extensibility is *the entire reason the project
is possible*. We used the `custom-1` opcode (`0101011`) — confirmed
unclaimed in Shakti's decoder — to add `ADDP1` without touching or
breaking any existing instruction.

### What does "open-source core" mean?
The complete hardware design (the actual logic that would become a chip)
is publicly available to read, modify, and rebuild — as opposed to a
proprietary core (like an ARM Cortex) where you only get a compiled,
locked "black box" you're licensed to use but never allowed to see inside.

**In our project:** Shakti C-Class's full RTL source (`.bsv` files) is
public on GitLab, under a BSD license, which is exactly what let us
directly edit `decoder.bsv` and `base_alu.bsv` to add our own instruction.
This would be *impossible* with a proprietary core.

### What are custom instructions?
New processor operations added to a base ISA, encoded into unused opcode
space, that a normal RISC-V binary wouldn't understand — but our
hardware-modified core does. They exist to do in one hardware cycle what
would otherwise take a slow multi-instruction software loop.

**In our project:** `ADDP1` (`rd = rs1 + rs2 + 1`, proof-of-concept) and
the packed byte-wise absolute-difference instruction (real target, in
design) are our two custom instructions.

---

## 2. Hardware Platforms and Tools

### What is an FPGA?
Field-Programmable Gate Array — a chip made of a huge grid of
reconfigurable logic blocks (LUTs), flip-flops, and memory (BRAM) that can
be "rewired" via software to become almost any digital circuit you
design — including an entire processor. Unlike an ASIC (a chip
permanently manufactured for one purpose), an FPGA can be reprogrammed
repeatedly, making it ideal for prototyping hardware designs like ours
before (if ever) committing to real silicon.

**In our project:** we have not yet synthesized/deployed onto an FPGA —
everything so far is Verilator *simulation* only. FPGA deployment
(Xilinx Artix-7/Zynq or Intel D-10 Lite, per our original scope) is future
work.

### What is Verilog?
A hardware description language (HDL) used to describe digital circuits
at the register-transfer level — the industry-standard "final" language
that actual chip synthesis tools understand.

**In our project:** we don't write Verilog directly. Our source is
Bluespec (BSV), a higher-level HDL, which gets *compiled into* structured
Verilog by the `bsc` compiler. That generated Verilog is what Verilator
and (eventually) Vivado actually consume.

### What is Vivado?
Xilinx's official FPGA design software — used for synthesis (converting
Verilog into an actual FPGA configuration), simulation, timing analysis,
and programming the physical FPGA board.

**In our project:** listed in our resources/toolchain, but not yet used —
we've only run Verilator-based *software* simulation so far, not real
FPGA synthesis.

### What is Verilator?
An open-source tool that compiles synthesizable Verilog into a fast C++
simulation model, letting you *run* your hardware design on a normal
computer instead of on real silicon or a licensed commercial simulator.

**In our project:** this is our entire simulation pipeline. Every test
we've run (`ADDP1`'s verification, the trace/waveform work) executed
through a Verilator-compiled `bin/out` binary, not real hardware.

### What is an ISS (Instruction Set Simulator)?
Software that mimics a processor's *behavior* at the instruction level —
given a program, it tells you what registers/memory would end up
containing, without modeling the actual internal hardware structure
(pipeline stages, caches, etc.) at all. `spike` is the standard RISC-V
ISS, used as a "golden reference" to check whether a real hardware
implementation computed the correct answer.

**In our project:** `spike` was never installed (a known, documented
gap) — we've been verifying correctness by manually reading Verilator's
`rtl.dump` trace instead of automatically diffing against a golden ISS.
This is worth being upfront about if asked how results are verified.

### What is GTKWave?
An open-source waveform viewer — it displays a `.vcd` file (a
cycle-by-cycle recording of every signal's value over simulated time) as
visual timing diagrams, letting you inspect exactly what the hardware did
on any wire, at any clock cycle.

**In our project:** we enabled VCD tracing (one Verilator compile flag,
`--trace`) and used GTKWave to navigate down into the core's internal
signal hierarchy, finding the base-ALU output FIFO and observing a real
`ENQ` (result-write) event — confirming waveform-level verification is a
working capability alongside our text-based trace analysis.

### What is a compiler / toolchain?
A compiler translates source code into machine instructions for a
specific target. A toolchain is the full set of tools needed to go from
source code to a running program — compiler, assembler, linker, debugger.

**In our project:** we use the RISC-V GNU toolchain (`gcc-riscv64-unknown-elf`,
GNU Binutils, GDB) to build test programs. Since `gcc` has no idea our
custom instructions exist, we hand-encode them as raw `.word 0x...` bytes
in assembly — there is no compiler support for our custom instructions
(that's exactly the job of Team 3, the compiler team, going forward).

### What is a benchmark suite?
A standardized set of test programs/workloads used to measure and compare
performance (speed, power, code size) under consistent conditions, so
results are meaningful and comparable rather than one-off anecdotes.

**In our project:** we don't have one yet — we've only run individual
hand-written test cases (`add.S`, `addp1_test.S`). Building a proper
benchmark (comparing custom-instruction vs. software-loop performance
across multiple test cases) is planned future work, not done yet.

### What is "accelerator firmware"?
Low-level software specifically written to configure, control, and
communicate with a hardware accelerator — distinct from general
application code, and usually the piece that actually issues the special
instructions or manages a co-processor's handshaking.

**In our project:** not yet developed — this would be the software layer
that calls our custom instruction as part of a larger frame-differencing
routine, not yet written.

### What is a "custom instruction spec"?
The formal, written definition of exactly what a custom instruction does:
its opcode encoding, operand format, and precise behavior — the document
someone would need to implement support for it correctly (in hardware,
in a compiler, or in a simulator), without having to read your source
code.

**In our project:** currently informal (documented in `SHAKTI-SETUP-LOG.md`
and design chat), not yet written as a standalone formal spec — worth
having one ready if Team 3 (compiler) needs to target our instructions.

---

## 3. Project-Specific Concepts

### What is frame differencing?
A classical (non-machine-learning) motion-detection technique: subtract
one video frame from the frame before it, pixel by pixel. Where the scene
is static, the difference is near zero; where something moved, the
difference is large. It's the simplest possible way to detect "something
changed here."

Formula: `D(x,y) = |Frame_t(x,y) − Frame_(t-1)(x,y)|`

**In our project:** this is the target workload our custom instruction
accelerates — though the *final* algorithm choice belongs to Team 1
(model team); frame differencing is our provisional, literature-backed
assumption about what the likely bottleneck operation is.

### Why is absolute difference used for video specifically?
Because pixel brightness values are unsigned (0–255) — a plain
subtraction could go negative depending on which frame is brighter at a
given pixel, which doesn't make sense for "how much did this change."
Taking the *absolute* value gives you a magnitude of change regardless of
direction (frame got brighter vs. got darker), which is what actually
matters for detecting motion or novelty.

### What is the packed byte-wise absolute difference instruction, and why parallel per instruction?
Our planned custom instruction. Instead of computing one pixel's absolute
difference per instruction (slow — one comparison, one subtraction, one
loop iteration per pixel), it treats a single 64-bit register as 8
separate 8-bit lanes (8 pixels), and computes `|a-b|` on *all 8 lanes
simultaneously*, in one clock cycle, using 8 physically parallel pieces of
comparator/subtractor hardware.

**Why do this instead of a normal loop?** Throughput. A software loop
needs one instruction (or several) per pixel; this needs one instruction
per *8* pixels — an 8× reduction in instruction count for this operation,
which matters because Shakti C-Class is single-issue in-order (only one
instruction executes per cycle, no help from out-of-order or superscalar
execution). This is a form of "sub-word SIMD parallelism" — the same
underlying trick used by early x86 MMX instructions, applied inside our
core's existing registers instead of building a dedicated vector unit.

### What is parallelism, in this context?
Doing more than one unit of work at the same time, rather than one after
another. Our project achieves a narrow, specific form of it — 8 pixels
computed simultaneously per instruction — without a general-purpose
vector unit (RVV), which would allow much larger, runtime-configurable
parallelism at significantly higher hardware design cost. Worth being
ready to explain *why* we chose the cheaper, narrower form (semester
timeline, complexity of building a real vector unit — see
`SHAKTI-ARCHITECTURE-AND-RATIONALE.md` for the full comparison).

---

## 4. Motivation-Related Terms

### Why "high latency" for general-purpose processors on this workload?
General-purpose CPUs execute AI/vision-style operations (pixel-by-pixel
comparisons, convolutions) using generic instructions never designed for
that pattern — every pixel needs several separate instructions (load,
subtract, compare, store), so total processing time per frame is high
relative to hardware specifically built for the task.

### Why "high power draw"?
More instructions executed to do the same work directly means more
energy consumed — every fetch/decode/execute cycle costs power, so doing
an operation in 1 custom instruction instead of 8+ generic ones
meaningfully reduces energy per frame, which matters for an always-on
edge device that can't rely on constant external power/cooling like a
data center GPU.

### Why "poor real-time performance"?
For live video monitoring, frames must be processed at least as fast as
they arrive (matching camera frame rate) to avoid falling behind and
building an unbounded backlog. A general-purpose processor doing this
work in software may not keep pace at typical frame rates, especially
under power/clock-speed constraints typical of edge deployment.

---

## How to use this document

Each team member should be able to explain, in their own words, at
minimum: what ISA/custom instructions/open-source core mean, why Shakti
C-Class over PicoRV32, what each tool in the toolchain does (Verilator,
GTKWave, Vivado, RISC-V GCC), and why the packed absolute-difference
instruction is designed the way it is (8 lanes, why absolute value, why
this over a real vector unit). These are the most likely follow-up
questions given the presentation content.
