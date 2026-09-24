# PATARA — Base Paper Study Guide

**Seminar topic:** Verification Methodologies for RISC-V Processors
**Prepared:** August 2026

---

## 1. Citation

> Gesper, S., Stuckmann, F., Wöbbekind, L. and Payá-Vayá, G. (2026) 'A Self-Testing
> Framework for Verification and Validation of a RISC-V-Based System with a
> Co-processor', *International Journal of Parallel Programming*, 54(15).
> doi: 10.1007/s10766-026-00824-8

| Field | Value |
|---|---|
| Publisher | Springer Nature |
| Journal | International Journal of Parallel Programming, Vol. 54, Art. 15 |
| Indexing | SCIE / Scopus |
| Received / Accepted | 26 April 2024 / 4 April 2026 |
| Access | Open Access (CC BY 4.0) — no paywall |
| Institution | Chip Design for Embedded Computing, TU Braunschweig, Germany |
| Funding | German BMBF, project 16ME0379 (ZuSe-KI-AVF) |
| Length | 29 pages |
| Tool | Open source: github.com/tubs-eis/PATARA |

---

## 2. One-sentence summary

The official RISC-V compliance test suite passed their processor with zero bugs, but
left 21% of logical conditions untested; PATARA auto-generates self-checking test
programs that reach 100% condition coverage and **found real bugs the official suite
had missed**.

---

## 3. Glossary — terms you must be able to define in Q&A

| Term | Meaning |
|---|---|
| **Pre-silicon verification** | Checking the design before manufacture, via simulation |
| **Post-silicon validation** | Checking the fabricated chip — catches fabrication faults, electrical errors, timing violations, not just design errors |
| **Golden reference model** | A trusted implementation (e.g. Spike, Imperas OVPSim) whose output you compare against |
| **Code coverage** | Metric quantifying how much of the HDL was exercised by tests |
| **Statement coverage** | % of HDL code lines executed |
| **Branch coverage** | % of if-then-else paths taken |
| **Expression coverage** | % of cases of an expression evaluated in an assignment |
| **Condition coverage** | % of logical conditions in branches that took **all** possible values — the strictest metric here, and where the compliance suite fails badly |
| **FSM coverage** | States reached and transitions taken |
| **Toggle coverage** | Per-signal bit-level 0↔1 transitions |
| **Data hazard** | Instruction needs a result not yet produced by an earlier instruction |
| **Forwarding (bypassing)** | Routing a result directly from a later pipeline stage back to an earlier one to resolve a hazard without stalling |
| **Stall** | Freezing the pipeline until a dependency resolves |
| **Positive testing** | Testing only with valid instruction streams |
| **DUT** | Design Under Test |

---

## 4. The problem (Sections 1–2)

### 4.1 Why generic verification frameworks fail

RISC-V is open, so implementations differ enormously — pipeline depth, whether M-extension
ops are single- or multi-cycle, hazard-resolution strategy, cache configuration, presence of
a co-processor. A **generic** test suite cannot know any of this, so it cannot systematically
exercise *your* hazards or *your* cache behaviour.

### 4.2 The two halves of any verification framework

The paper frames every verification approach as two questions:

**(a) Input stimulus** — what test programs run on the processor?
  - handwritten, or automatically generated

**(b) Checking correctness** — how do you know the execution was right?
  - output reference, or golden-model simulator, or **self-checking** (PATARA's answer)

### 4.3 What's wrong with golden reference models

- Instruction Set Simulators (Spike, Imperas OVPSim) don't model external components
  (memory, buses), limiting test scope
- Virtual prototypes fix that but add complexity — **and introduce new sources of error**
  (the paper cites ref [20] showing exactly this: bugs in the reference model itself)
- Generating reference results costs time; the paper notes it "could be prohibitive"
- Post-silicon, observability is limited — you can't monitor internal signals on a real chip

### 4.4 Related work they position against

| Approach | Ref | Limitation |
|---|---|---|
| Official RISC-V unit + compliance suites | [25],[26] | Handwritten; implementation-independent; claims ~100% *functional* coverage but misses hardware-architecture coverage |
| Google RISCV-DV | [1],[2] | Randomized instruction streams, but **requires a reference simulator** to verify traces |
| Evolutionary algorithm test generation | [28] | Reached only ~90% code coverage on RV32IMFC (RI5CY) |
| SMT-solver-based unconstrained generation | [7] | Formal ISA description-driven |
| Redundant multi-core execution / software checkers | [19] | Online validation only |
| Formal verification of co-processors | [27] | "expensive manual steps required, complexity limitations" |

---

## 5. The system under test (Section 3)

### 5.1 The RISC-V core (EIS-V)

- **RV32IM**, VHDL, **6 pipeline stages**: IF → ID → EX → MEM1 → MEM2 → WB
- Hazard detection unit in **ID** stage inserts stalls for load-data hazards
- **Multiplier split across EX and MEM1** → causes a data hazard, one-cycle stall
- **Divider is multi-cycle**, variable latency, chosen for small area (embedded focus) —
  stalls the pipeline until complete
- **Static branch prediction**: always assume not-taken. Branch condition evaluated in EX →
  **2 instructions flushed** if taken. Unconditional jumps resolve in ID → only 1 flushed
- Data cache miss stalls the pipeline (in-order execution)
- CSR access in ID and EX stages

> **Why this matters:** every one of these implementation choices creates hazard corner
> cases that a generic test suite knows nothing about. This is the paper's whole thesis.

### 5.2 The V2PRO vector co-processor

- Vertical (sequential) vector execution, SIMD via instruction broadcast to parallel lanes
- **24-bit datapath**, 48-bit accumulator
- Three-operand machine (2 inputs, 1 output)
- 3-D addressing: `Address = x·α + y·β + z·γ + δ`
- Hierarchy: Clusters → Vector Units → 2 processing Vector Lanes + 1 Load/Store lane +
  local memory; DMA per cluster; shared cache (DCMA) to DDR4 over AXI
- **Chaining**: neighbouring lanes pass data directly via FIFOs
- Instruction FIFO decouples vector execution from RISC-V instruction issue
- Controlled via **memory-mapped addresses** — the RISC-V issues vector instructions using
  ordinary load/store instructions
- ISA includes ADD, SUB, MULL/MULH, MAC, shifts, MIN, MAX, **ABS**, conditional moves,
  full logic set, LOAD/LOADS/LOADB/STORE

> **Note the hardware deliberately has no hazard-resolution logic** in the vector lanes
> (to hit high frequency), so test generation must *avoid* generating RAW hazards.

---

## 6. REVERSI — the core method (Section 4.1)

### 6.1 The idea

A self-test program verifies itself with no external reference:

```
1. MODIFICATION  — apply the test instruction to (focus, random) → target
2. RESTORING     — apply the inverse to (target, random) → recovered focus
3. COMPARISON    — if recovered ≠ original focus, hardware error
```

Example for ADD:
```asm
    add  target, focus, random     ; modification
    sub  target, target, random    ; restoring
    bne  target, focus, fail       ; comparison
```

### 6.2 The three rules

1. **The test instruction appears ONLY in the modification operation.** Otherwise a
   systematic error in that instruction could cancel itself out during restoration and
   go undetected. (Critical design point — likely exam question.)
2. **Operand roles are fixed**: focus register + random register → target register in
   modification; target + random → restore focus.
3. **Non-invertible instructions need control code.** For e.g. shift-left, bits are lost
   during modification. Extra code preserves what's needed to restore.

### 6.3 Interleaving — how complexity is built

- Chain modification operations: output of test *n* is input to test *n+1*
- Perform restorations in **reverse order** (stack discipline — LIFO)
- Nest multiple stacks for arbitrarily long, arbitrarily complex tests

This is what creates the deep data dependencies that trigger forwarding paths.

---

## 7. The PATARA framework (Section 4.2)

Flow (Figure 5):

```
XML processor + instruction descriptions
        ↓
Instruction Selection  (which instructions to test)
        ↓
Instruction Sequence Generation  (single-instruction or complex, per test mode)
        ↓
Code Generation  (modification + restoring + comparison in assembly)
        ↓
Assembly files + randomly initialised register file
```

Figure 6 shows the XML definition of `ADD` with `SUB` declared as its reverse.

### Custom ISA extension support — the key passage for our project

> *"For instruction set extensions (such as custom ISA extensions in RISC-V), the
> description files require the layout of the new instructions and the corresponding
> sequence to restore custom operations. Depending on the complexity of the custom
> operations, the restoring operation includes multiple instructions to restore the
> original data. For higher-level implementations of restore procedures, algorithmic
> functions can be called in the reversing procedure."*

PATARA's core is **ISA-independent**; target ISAs are described as plug-ins. The paper
demonstrates RV32IM; the framework previously targeted a VLIW architecture.

---

## 8. The four RISC-V extensions they added (Section 4.3)

**1. Variable immediate widths.** `shamt` in shift instructions is 5 bits vs 12 for normal
I-type. The XML encodes immediate length per instruction so random immediates respect it.

**2. Interleaving sequence-length limits.** Conditional branches have a ±4 KiB target range.
Tests like BEQ put the branch in the modification and its target in the restoring operation,
so interleaved sequences can't grow past that range.

**3. Pipeline hazard generation.** *(The most important extension.)*
- Generates fixed-length instruction sequences covering **all forwarding path selections**
  (the EX-stage source multiplexers) and all stall mechanisms
- Sequences built from **all permutations of instruction types**, covering every data
  dependency combination
- **Required sequence length = f(pipeline depth)**: a 6-stage implementation needs
  4 consecutive instructions for full coverage
- **Random filler instructions** are inserted that don't disturb the data dependency but
  reach additional hazard-state switches

**4. Operand swapping.** Normally the focus register is always source operand 1, so the
forwarding path to **operand 2 is never tested**. PATARA randomly swaps focus and random
positions (probability configurable).

**Plus cache testing:**
- *dcache*: address generation modified to force cache-line misses based on the configured
  line width
- *icache*: a jump + repeated filler instructions to fill the cache line + a jump
  destination that misses

---

## 9. Twin-based co-processor verification (Section 4.4)

REVERSI cannot be used here — many vector instructions aren't invertible. Instead:

```
        random vector instruction generation (on the RISC-V)
                    ↓                    ↓
     Path 1: V2PRO hardware      Path 2: C++ software twin on RISC-V
                    ↓                    ↓
        results DMA'd to external memory      reference arrays
                    ↓                    ↓
                     COMPARE → pass/fail
```

**The verified RISC-V core becomes the golden model.** No external reference, no host
communication — which is what makes it usable post-silicon.

Details:
- Random parameters: operations, operands + addressing parameters, vector lengths, lane
  assignments
- Software twin implemented in C++ with **bit-exact masks** (shifts, multiply precision)
- Chaining emulated by sequential interleaving of element calculations
- The twin is a **coarse-grained model** — it ignores lane pipeline details and stall
  conditions
- Results copied out by DMA to a reserved external memory region, then compared
- On failure: reports instruction sequence, in/out data, hardware register states

**Constraints during generation** (important — shows real engineering depth):
- Vector operand addresses checked so no **RAW hazards** are generated within a window
  equal to pipeline depth (the hardware has no hazard logic by design)
- Chain deadlock avoidance — if every lane waits for chained data, nothing issues
- Chain-finishing instructions appended so sequences terminate validly
- A long instruction is prepended to give the RISC-V time to fill the instruction FIFO

---

## 10. Results (Section 5)

Simulator: **Questa Sim-64 2021.3**. FPGA: V2PRO at 400 MHz (8 clusters × 8 units),
RISC-V and AXI at 200 MHz.

### 10.1 Official compliance suite — Table 4 (RV32IM, 17,765 test instructions)

| Metric | Coverage |
|---|---|
| Statement | 99.40% |
| Branch | 99.07% |
| Expression | 98.33% |
| **Condition** | **79.12%** |
| FSM states / transitions | 100% / 88.63% |
| Toggle | 87.87% |

### 10.2 PATARA build-up — Table 5 (the money table)

| Configuration | Instructions | Condition |
|---|---|---|
| All instruction combinations | 6,983 | 80.21% |
| + operand switching | 9,722 | 81.31% |
| + interleaving | 17,294 | 81.31% |
| + randomized sequences | 1,851,852 | 96.70% |
| **+ multiple sequences + cache tests** | **6,732,901** | **100.00%** |

**Read this table carefully — it tells a story:**
- Interleaving alone adds **nothing** to condition coverage
- The 81% → 97% jump comes entirely from **hazard sequence generation**
- The final 3% requires **cache-miss tests**
- Cost: 6.7 million instructions vs the suite's 17,765 (~380× more)

Toggle coverage caps at **86.60%** — unreachable address-space bits, same limitation as
the handwritten suite.

### 10.3 Bugs actually found (Section 5.2) — THE HEADLINE

The compliance suite found **zero** bugs; the design "passed." PATARA then found:

1. **Data forwarding unit** — failed to correctly update the forwarded operand source when
   a multi-cycle division had not yet finished. Variable-latency divide means many test
   cases are needed to expose it.
2. **Multiplication unit** — split across EX/MEM1; mishandles a data-cache miss (from a
   Load) occurring during a multi-cycle multiply.
3. **Load → JALR forwarding** — never exercised by the handwritten suite.
4. **Cache-miss + stall combinations** — "several bugs" found and fixed.

**Why the suite missed them (Figure 9):** it never exercises *transitions between
consecutive forwarding-path selections* — e.g. EX forward-select going WB → MEM2 or
WB → MEM1 in sequence.

### 10.4 System-level with co-processor — Table 6 (84 handwritten tests)

| Component | Statement | Condition | FSM States/Trans | Toggle |
|---|---|---|---|---|
| RISC-V | 96.04% | 80.85% | 73.33% / **38.83%** | 72.62% |
| V2PRO | 95.03% | 87.87% | 93.75% / 90.09% | 79.83% |
| System | 93.38% | 77.57% | 80.00% / 48.04% | 68.29% |

**38.83% FSM transition coverage** on the RISC-V — handwritten testing of a coupled system
is badly inadequate.

### 10.5 Co-processor random testing — Table 7

Sequences of length 7, scaled up:

| Test count | V2PRO Statement | V2PRO Condition |
|---|---|---|
| Random [1] | 92.11% | 87.27% |
| Random [10] | 99.06% | 98.18% |
| Random [100] | 100.00% | 98.78% |
| Random [1000] | 100.00% | 98.78% |
| **Random [1000] + FIFO + modified constraints** | **100.00%** | **100.00%** |

Note the last row: uniform random vector-length generation **under-represents short
vectors**, so a second constraint set forcing small lengths was needed to hit chaining
stall corner cases. Long sequences were needed to test FIFO-full logic.

### 10.6 Execution time breakdown (per random sequence, ≥7 vector instructions)

| Phase | Time |
|---|---|
| Random sequence generation (on RISC-V) | 86.04 ms |
| Data generation (24,576 B, xoroshiro128plus) | 2.68 ms |
| DMA transfers | 0.05 ms |
| **V2PRO execution** | **0.01 ms** |
| RISC-V reference calculation (software twin) | 16.10 ms |

> Observation worth making in the seminar: actual hardware execution is **0.01 ms** —
> effectively free. Verification cost is entirely in *generating* and *checking*.

---

## 11. Limitations — state these openly

The paper is honest about most of these; Section 5.6 is titled *"What does 100% Coverage
Mean for Hardware Verification?"*

**Their own admissions:**

> *"A coverage report with 100% code coverage only indicates that all the code lines and
> conditional expressions were executed... even with complete code coverage, it cannot be
> guaranteed that a specific RISC-V implementation is completely correct."*

> *"As the verification of V2PRO co-processor execution relies on a software twin on the
> RISC-V (implementation of a golden model), failures can be masked by erroneous execution
> on this model as well."*

**Scope exclusions (Section 5.1):**
- **CSR / system-class instructions not executed** — coverage excludes them
- **Interrupts not tested**; sleep mode not tested; coverage disabled for those entities
  via pragma directives
- Privileged architecture explicitly "out of the scope of this paper, which focuses on
  the unprivileged specification"

**Other weaknesses to acknowledge:**
- **REVERSI is not their invention** — from ref [31] (Shazli & Tehranipoor). Their
  contributions are the RISC-V port + the four extensions + twin-based co-processor method
- Extends their own prior paper [10] — incremental
- **RV32IM only** — no F/D/A/C. Floating-point is hard for REVERSI (rounding destroys
  invertibility)
- **One design evaluated** — their own core; no cross-validation on riscv-mini, Rocket, etc.
- Requires **invertible** instructions, or extra control code, or the twin approach
- Uses commercial simulator (Questa Sim) for coverage measurement
- Journal tier below IEEE TCAD / Journal of Systems Architecture
- Very recent (2026) — limited citation record
- Minor internal inconsistency: abstract says **78.94%** condition coverage for the
  handwritten suite; Table 4 and the conclusion say **79.12%**

---

## 12. Relevance to our project (Team 2)

| Paper element | Our project |
|---|---|
| Custom RISC-V implementation | Shakti C-Class (pipelined, BSV) |
| Compliance suite as baseline | We run `add.S`, `fadd.S` and check `tohost` |
| Custom ISA extension support (§4.2) | `ADDP1` (`rd = rs1+rs2+1`), custom-1 opcode |
| Co-processor twin verification (§4.4) | ECE team's hardware accelerator |
| Hazard-interaction bugs missed by suite | We modified `decoder.bsv` + `base_alu.bsv` — shared logic |
| Pre-silicon → FPGA validation | Our Verilator sim → planned FPGA target |

### Applying REVERSI to our instructions

**ADDP1** — fully invertible, works immediately:
```
modification:  ADDP1 target, focus, random     ; target = focus + random + 1
restoring:     SUB   target, target, random
               ADDI  target, target, -1
comparison:    BNE   target, focus, fail
```

**Packed byte-wise absolute difference** (`rd = |rs1-rs2|` per byte) — **NOT invertible**;
absolute value destroys sign. Note that V2PRO's ISA also contains `ABS`, and the authors
solved it with the **twin-based approach** rather than REVERSI. Same solution applies:
compute once in our custom hardware, once as a plain software loop on the base ISA,
compare.

---

## 13. Likely Q&A — prepare answers

**Q: Why must the test instruction appear only in the modification operation?**
A: If it also appeared in the restoring operation, a systematic error in that instruction
could cancel itself out — the test would pass despite broken hardware.

**Q: Does 100% coverage mean the processor is correct?**
A: No, and the authors say so in §5.6. It means every line and condition was executed.
Faults can still be masked. Coverage is a *necessary* not *sufficient* condition.

**Q: What's the novelty if REVERSI already existed?**
A: The RISC-V ISA port, four extensions (variable immediates, branch-range handling,
hazard sequence generation, operand swapping), cache-miss generation, and the twin-based
co-processor methodology.

**Q: Why not just use a golden model like Spike?**
A: Reference simulators don't model external components, introduce their own bugs (ref
[20]), cost time to generate references, and are impractical post-silicon where internal
observability is limited.

**Q: How does this apply to your project's core?**
A: Directly — we run the same compliance suite this paper shows is insufficient, on a
pipelined core with custom instructions and a planned accelerator. §4.2 documents adding
custom ISA extensions; §4.4 covers co-processor verification.

**Q: Could this verify your custom instruction?**
A: `ADDP1` yes — invertible via SUB + ADDI -1. The packed absolute-difference instruction
no — not invertible, would need the twin-based approach.

**Q: What are the paper's weaknesses?**
A: RV32IM only (no floating point); CSRs, interrupts and privileged spec excluded; one
design evaluated; REVERSI borrowed from prior work; coverage ≠ correctness.

---

## 14. Numbers cheat sheet

| Fact | Value |
|---|---|
| Handwritten suite condition coverage | 79.12% (abstract: 78.94%) |
| PATARA condition coverage | 100.00% |
| Handwritten suite test instructions | 17,765 |
| PATARA instructions for full coverage | 6,732,901 |
| Toggle coverage ceiling | 86.60% |
| Pipeline stages | 6 |
| Sequence length for full hazard coverage | 4 consecutive instructions |
| RISC-V FSM transition cov. (system, handwritten) | 38.83% |
| V2PRO clock / RISC-V clock | 400 MHz / 200 MHz |
| V2PRO datapath / accumulator | 24-bit / 48-bit |
| V2PRO execution time per sequence | 0.01 ms |
| Reference calc time per sequence | 16.10 ms |
| Reference model LOC (C++ twin) | — coarse-grained |
| Bugs found by compliance suite | 0 |
| Bugs found by PATARA | several (4 categories documented) |
