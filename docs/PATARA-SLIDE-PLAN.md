# PATARA — Base Paper Deep Dive: Slide Content Plan (Slides 9–15)

**Template adaptation note:** the supplied template is written for an ML/vision paper.
Several slots have no equivalent in a hardware verification paper. Translations used:

| Template asks for | Hardware verification equivalent |
|---|---|
| Datasets (size, classes) | **Design Under Test** (ISA, pipeline depth, HDL, LOC) |
| Accuracy / Top-1 | **Code coverage metrics** (statement, branch, condition, FSM, toggle) |
| Model params (M) | **Number of test instructions executed** (cost proxy) |
| Optimizer, epochs, GPU | **Simulator, FPGA config, clock frequencies** |
| Prior SOTA baseline | **Official RISC-V compliance test suite** |
| Ablation study | **Table 5** — already structured exactly as an ablation |

---

## SLIDE 9 — (a) Overview

**Objective**
- Generate self-checking test programs for *any* RISC-V hardware implementation, without
  requiring a golden reference model
- Achieve full code coverage including implementation-specific hazards the official
  compliance suite cannot reach
- Extend verification to an attached programmable co-processor

**Main contributions** (name them as modules — matches "named components" in template)
1. **REVERSI-based self-test generation** ported to RISC-V (RV32IM)
2. **Pipeline hazard sequence generator** — all forwarding paths, depth-aware
3. **Operand swapping** — reaches the second source operand's forwarding path
4. **Cache-miss generation** — configurable dcache/icache miss provocation
5. **Twin-based co-processor verification** — dual-path execution, no external model

**Evaluated on** (replaces "datasets")
- EIS-V: RV32IM, 6-stage pipeline, VHDL implementation
- V2PRO: vertical vector co-processor, 8 clusters × 8 vector units

**HEADLINE RESULT — callout box**
> The official RISC-V compliance suite **passed the design with zero bugs**.
> PATARA raised condition coverage **79.12% → 100%** and found **real hazard-interaction
> bugs** in that same "verified" design.

**Block diagram**
```
        XML processor + ISA description
                     ↓
    ┌────────────────────────────────────┐
    │            PATARA                  │
    ├──────────┬───────────┬─────────────┤
    │ REVERSI  │  Hazard   │ Twin-based  │
    │ self-test│ sequence  │ co-processor│
    │ generator│ generator │ verification│
    └──────────┴───────────┴─────────────┘
                     ↓
     Self-checking RISC-V assembly programs
```

---

## SLIDE 10 — (b) The Problem

**What the baseline does**
- Official RISC-V compliance suite [26]: **handwritten** test cases, 17,765 test
  instructions for RV32IM
- Claims near-100% *functional* coverage
- **Result on their design: zero bugs found. Design declared correct.**

**Why that's insufficient**
- Handwritten tests are **implementation-independent** — they don't know your pipeline
  depth, hazard strategy, cache line size, or whether a co-processor is attached
- Achieved only **79.12% condition coverage** — over one fifth of logical conditions
  never fully exercised
- Never exercises *transitions between consecutive forwarding-path selections*
  (**use Fig. 9** — EX forward-select never switches WB → MEM2)
- Must be **manually rewritten** for a different pipeline depth

**The tradeoff that matters** (cost vs. capability, as template asks)

| | Manual effort | Adapts to implementation | Needs golden model |
|---|---|---|---|
| Handwritten compliance suite | Very high | No | No |
| Random generators (RISCV-DV) | Low | Partly | **Yes** |
| Formal verification | High | Yes | No |
| **PATARA** | **Low** | **Yes** | **No** |

**Why avoiding the golden model matters**
- ISSs don't model external components (memory, buses) → limits test scope
- Virtual prototypes fix that but **introduce their own bugs** (paper cites ref [20])
- Reference generation time "could be prohibitive"
- Post-silicon: limited internal observability makes external checking impractical

---

## SLIDE 11 — (c) Core Mechanism: REVERSI

**The key innovation:** make each test program verify *itself*.

**Plain-terms explanation**
> Perform an operation, then perform its inverse. If you get back exactly what you
> started with, the hardware executed both correctly. No external reference needed.

**Three-stage structure**
```
1. MODIFICATION   test instruction:  (focus, random) → target
2. RESTORING      inverse operation: (target, random) → recovered
3. COMPARISON     recovered ≠ focus  ⇒  hardware error
```

**Worked example — ADD** *(use Fig. 4, cite: Gesper et al., 2026)*
```asm
    add   target, focus, random     ; modification
    sub   target, target, random    ; restoring
    bne   target, focus, fail       ; comparison
```

**Critical design rule — likely Q&A**
> The test instruction appears **only** in the modification operation. If it also appeared
> in the restoring operation, a systematic error in that instruction could cancel itself
> out and go undetected.

**Interleaving — building complexity**
- Chain modifications: output of test *n* feeds test *n+1*
- Restore in **reverse order** (stack / LIFO discipline)
- Nest multiple stacks → arbitrarily long tests with deep data dependencies

*Figures to use:* Fig. 4 (REVERSI assembly example)

---

## SLIDE 12 — (d) Overall Architecture

**Framework flow** *(use Fig. 5, cite: Gesper et al., 2026)*

```
XML processor + instruction descriptions
        ↓
[1] Instruction Selection        → which instructions to test
        ↓
[2] Sequence Generation          → single-instruction or complex sequences
        ↓
[3] Code Generation              → modification + restoring + comparison
        ↓
Assembly files (+ randomly initialised register file)
```

**What changes at each stage**

| Stage | Input | Output | Key decision |
|---|---|---|---|
| Selection | XML instruction list | Instruction set to test | Which ISA subset |
| Sequence generation | Test mode | Instruction ordering | Single / interleaved / hazard permutation |
| Code generation | Sequence | Assembly | Modification + inverse + compare |

**Key architectural property**
> PATARA's core is **ISA-independent**. Target architectures are described as plug-ins
> (XML). Demonstrated here on RV32IM; previously targeted a VLIW architecture.

*Optional supporting figure:* Fig. 6 (XML definition of ADD with SUB as reverse) — good
for showing how a new/custom instruction is declared.

---

## SLIDES 13a–13c — (e) Component Deep-Dives

*Template asks: what it is / what it captures / why cheap or expensive / its limitation and
how another component compensates. PATARA fits this structure unusually well because each
extension exists to fix the previous one's blind spot.*

### Component 1 — Pipeline Hazard Sequence Generation

- **What it is:** auto-generated fixed-length instruction sequences built from *all
  permutations of instruction types*, covering every data-dependency combination
- **What it captures:** all forwarding-path selections (EX-stage source multiplexers)
  and all stall mechanisms
- **Depth-aware:** required sequence length is a function of pipeline depth —
  **6 stages → 4 consecutive instructions** for full coverage
- **Refinement:** random *filler instructions* inserted that don't disturb the data
  dependency, reaching additional hazard-state switches
- **Why it's the expensive component:** requires ~1.85 M instructions to be effective
- **Impact:** condition coverage **81.31% → 96.70%** — the single biggest jump
- **Limitation:** still can't reach cache-related stall paths → Component 3 compensates

### Component 2 — Operand Swapping

- **What it is:** randomly swaps which source operand carries the focus value vs. the
  random value (probability configurable)
- **What it captures:** the forwarding path to **source operand 2**
- **Why it exists:** in a standard REVERSI test, the focus register is *always* operand 1,
  so operand 2's forwarding path is never exercised — a silent blind spot
- **Why it's cheap:** no new instructions, just a generation-time parameter
- **Impact:** condition coverage 80.21% → 81.31% (small but it closes a structural gap)

### Component 3 — Cache Miss Generation

- **What it is:** dcache — address generation modified to force cache-line misses based on
  configured line width; icache — jump + repeated filler to fill a cache line + a jump
  destination that misses
- **What it captures:** stall conditions arising from memory access, and the interaction
  between cache misses and pipeline hazards
- **Why it exists:** instruction cache misses "only rarely occur on small test cases"
- **Impact:** closes the final **96.70% → 100%**
- **Found real bugs here:** cache-miss + stall combinations

### Component 4 — Twin-Based Co-Processor Verification

*(This deserves its own slide — use Fig. 7, cite: Gesper et al., 2026)*

- **What it is:** dual-path execution — the same randomly generated vector instructions run
  (1) on the V2PRO hardware and (2) as a C++ software twin on the already-verified RISC-V
- **Why REVERSI can't be used:** many vector operations (e.g. `ABS`, `MIN`, `MAX`) are
  **not invertible**
- **The verified RISC-V core becomes the golden model** — no external reference, no host
  communication → usable post-silicon
- **Constraints during generation** (real engineering depth worth showing):
  - Vector operand addresses checked so no **RAW hazards** are generated (the hardware
    deliberately omits hazard logic to hit 400 MHz)
  - Chain-deadlock avoidance — prevent all lanes waiting on chained data
  - Chain-finishing instructions appended so sequences terminate validly
  - Long instruction prepended so the instruction FIFO can fill
- **Limitation the authors admit:** the twin is a **coarse-grained model** — ignores lane
  pipeline details and stall conditions, so *"failures can be masked by erroneous execution
  on this model as well"*

---

## SLIDE 14 — (f) Experimental Setup

**Design Under Test** *(replaces "datasets")*

| | RISC-V core (EIS-V) | V2PRO co-processor |
|---|---|---|
| ISA | RV32IM | Custom vector ISA (Table 3) |
| Structure | 6-stage pipeline, VHDL | 8 clusters × 8 vector units |
| Datapath | 32-bit | 24-bit (48-bit accumulator) |
| Notable | Multi-cycle divide; multiplier split EX/MEM1; static not-taken branch prediction | Chaining between lanes; instruction FIFO; 3-D addressing |
| Coverage bins | 1,012 statement / 515 branch / 94 condition | 1,712 / 1,149 / 165 |

**Tooling** *(replaces "training details")*
```
Simulator:   Questa Sim-64 2021.3
FPGA:        V2PRO @ 400 MHz;  RISC-V + AXI @ 200 MHz
Framework:   PATARA (open source, github.com/tubs-eis/PATARA)
Twin model:  C++, bit-exact masks
RNG:         xoroshiro128plus (on RISC-V)
```

**Coverage metrics defined** (one line each — template asks for compact definitions)
- **Statement** — HDL lines executed
- **Branch** — if-then-else paths taken
- **Expression** — cases of an expression evaluated in an assignment
- **Condition** — every logical condition took *all* possible values *(strictest)*
- **FSM** — states reached and transitions taken
- **Toggle** — per-signal bit-level 0↔1 transitions

**Scope exclusions — state these honestly**
- CSR / system-class instructions not executed
- Interrupts and sleep mode not tested (coverage disabled via pragma directives)
- Privileged architecture explicitly out of scope

---

## SLIDE 15 — (g) Results

### Main comparison table *(bold = base paper's method)*

| Test method | Instructions | Statement | Branch | Expression | **Condition** | FSM Trans. | Toggle |
|---|---|---|---|---|---|---|---|
| Compliance suite (RV32I) | 860,973 | 91.17% | 89.46% | 90.00% | 53.84% | 81.81% | 75.68% |
| Compliance suite (RV32M) | 28,543 | 91.56% | 87.06% | 90.00% | 57.14% | 84.09% | 82.79% |
| Compliance suite (RV32IM) | 889,516 | 99.40% | 99.07% | 98.33% | 79.12% | 88.63% | 87.87% |
| **PATARA (full)** | **6,732,901** | **100.00%** | **100.00%** | **100.00%** | **100.00%** | **100.00%** | 86.60% |

### Key observations (exact deltas — as template requires)

- **+20.88 percentage points condition coverage** over the official compliance suite
  (79.12% → 100.00%)
- **+11.37 pp FSM transition coverage** (88.63% → 100.00%)
- Cost: **≈7.6× more executed instructions** (889,516 → 6,732,901)
- **Toggle coverage is the one metric PATARA does not win** (86.60% vs 87.87%) — both
  limited by unreached address-space bits. *Say this out loud; it shows you read critically.*

### ABLATION CALLOUT *(Table 5 — this is already an ablation study)*

| Configuration | Instructions | Condition Coverage |
|---|---|---|
| All instruction combinations | 6,983 | 80.21% |
| + operand switching | 9,722 | 81.31% |
| + interleaving | 17,294 | 81.31% |
| + randomized hazard sequences | 1,851,852 | 96.70% |
| **+ multiple sequences + cache tests** | **6,732,901** | **100.00%** |

> **Removing hazard sequence generation drops condition coverage to 81.31%.**
> **Interleaving alone contributes 0.00 pp to condition coverage** — the gain comes
> entirely from hazard-permutation sequences and cache-miss tests.

### Bugs found — the strongest result

The compliance suite found **zero** bugs. PATARA found:

1. **Data forwarding unit** — failed to update forwarded operand source when a multi-cycle
   division had not completed (variable latency ⇒ needs many test cases to expose)
2. **Multiplication unit** — mishandles a data-cache miss during a multi-cycle multiply
   (unit split across EX and MEM1)
3. **Load → JALR forwarding** — never exercised by the handwritten suite
4. **Cache-miss + stall combinations** — several bugs found and fixed

### Co-processor results (Table 7)

| Test sequences | V2PRO Statement | V2PRO Condition |
|---|---|---|
| Random [1] | 92.11% | 87.27% |
| Random [10] | 99.06% | 98.18% |
| Random [100] | 100.00% | 98.78% |
| **Random [1000] + FIFO + modified constraints** | **100.00%** | **100.00%** |

*Note worth making:* uniform random vector-length generation **under-represents short
vectors**, so a second constraint set forcing small lengths was required to hit chaining
stall corner cases.

### Honest closing bullet (recommended)

> The authors state in §5.6: *"even with complete code coverage, it cannot be guaranteed
> that a specific RISC-V implementation is completely correct."*
> Coverage is **necessary but not sufficient** — this motivates the formal methods covered
> in the literature review.

*That last line is your bridge into the χRVFormal / PFV supporting-paper slides.*

---

## Figure inventory — what to lift from the paper

| Fig. | Content | Use on slide |
|---|---|---|
| Fig. 1 | System overview: RISC-V + V2PRO + DMA + memory | 14 (setup) |
| Fig. 2 | 6-stage RV32IM pipeline structure | 10 or 14 |
| Fig. 3 | V2PRO schematic, lane chaining network | 13c (twin) |
| **Fig. 4** | **REVERSI assembly example (add/sub)** | **11 (core mechanism)** |
| **Fig. 5** | **PATARA framework overview** | **12 (architecture)** |
| Fig. 6 | XML definition of ADD with reverse SUB | 12 (or custom-instruction slide) |
| **Fig. 7** | **Twin-based verification framework** | **13c** |
| Fig. 8 | Valid chaining combinations | 13c (optional) |
| **Fig. 9** | **Missed FSM transition for hazard** | **10 (problem)** |

Caption format: *"Fig. 5 — PATARA framework overview (Gesper et al., 2026)"*

---

## Optional extra slide — link to our project

If you have room, one slide connecting the paper to Team 2's work:

- We run the same compliance suite this paper shows is insufficient (`add.S`, `fadd.S`,
  `tohost` checking)
- §4.2 documents adding **custom ISA extensions** via XML — directly applicable to `ADDP1`
  (`rd = rs1 + rs2 + 1`); restoring operation = `SUB` + `ADDI -1`
- Our planned packed absolute-difference instruction is **not invertible** → would need the
  twin-based approach, exactly as the authors did for V2PRO's `ABS`
- We modified shared logic (`decoder.bsv`, `base_alu.bsv`) — precisely the regression risk
  this paper's hazard testing is designed to catch
