# Seminar Deck — Slide-by-Slide Content

**Topic:** Verification Methodologies for RISC-V Processors
**Format:** 18 slides · white background · one accent colour · plain bullets · thin-bordered
tables with the base-paper row highlighted · page numbers bottom-right.
Section tag (small caps, accent colour) sits above each title.

---

## SLIDE 1 — Title
- Small caps: **SEMINAR PRESENTATION**
- Title (big): **Verification Methodologies for RISC-V Processors**
- Subtitle (italic): *A review of how correctness is established for open, extensible
  processor implementations — focus on the base paper: A Self-Testing Framework for a
  RISC-V-Based System with a Co-processor*
- Bottom-left: **Presented by** — Kevin Jose · UID: ______ · Class: ______
- Bottom-right: **Under the guidance of** — ______ · Dept. of Computer Science & Engineering

---

## SLIDE 2 — Agenda
Numbered list:
1. Introduction and Objective
2. Literature Survey — Supporting Papers
3. Literature Survey — Base Paper
4. Applications and Relevance
5. Comparison with Alternate Approaches
6. Conclusion
7. References

---

## SLIDE 3 — Introduction and Objective
*Tag: 01 · INTRODUCTION AND MOTIVATION. Four labelled blocks (2×2).*

**Introduction**
- RISC-V is an open, extensible ISA now widely used in academia and industry
- Anyone can add custom instructions — but a fabricated processor cannot be patched
- Verification establishes that an implementation behaves as its specification requires

**The gap**
- The official compliance suite is handwritten and implementation-independent
- It cannot target a specific pipeline, hazard logic, or cache configuration
- Passing it is not the same as being correct

**Objective**
- Review five papers to trace how RISC-V verification has evolved
- Understand how each contributes a distinct capability
- Show how the base paper applies these to verifying custom instruction-set extensions —
  the core need of our project

**Core challenge** (callout)
- Verification normally checks a design against a golden reference. A custom instruction
  you invented has no golden reference — and exhaustive testing is impossible (a 32-bit
  adder alone has 2⁶⁴ input combinations). Every method trades off *where tests come from*
  against *how correctness is decided*.

---

## SLIDE 4 — Literature Survey Overview (table)
*Tag: 02 · LITERATURE SURVEY. Highlight row 5.*

| # | Paper (first author, year) | Core approach | Role |
|---|---|---|---|
| 1 | χRVFormal — Shen et al., 2026 | High-level (Chisel) formal model checking | Supporting |
| 2 | RISC-V Vector Accelerator — Jiménez et al., 2023 | UVM co-simulation vs Spike golden model | Supporting |
| 3 | INSTILLER — Zhang et al., 2024 | Coverage-guided RTL fuzzing (ant-colony) | Supporting |
| 4 | Polynomial Formal Verification — Weingarten et al., 2025 | BDD equivalence checking, proven time bounds | Supporting |
| 5 | **PATARA — Gesper et al., 2026** | **Self-testing (REVERSI), no golden model** | **Base paper** |

Footnote: *All five indexed in SCOPUS / SCIE · published 2023–2026 · four journal articles
+ one Springer journal base paper.*

---

## SLIDE 5 — Supporting Paper 1: χRVFormal
*Tag: 02 · LITERATURE SURVEY — PAPER 1*
Sub-line (italic): Shen, Chen, Liu, Zhang, Song & Wu · Journal of Systems Architecture
(Elsevier) · 2026

**Methodology**
- Reference model of RISC-V written in high-level Chisel, not Verilog
- Synchronisation mechanism (StateCheck / ActionCheck) aligns a single-cycle model with a
  pipelined / out-of-order design
- Reduces to a model-checking problem solved by Pono / SMTBMC with Boolector
- Differs from prior work: verify at the high-level source, not the generated Verilog

**Key findings**
- Reference model 4,609 lines vs riscv-formal's 104,911 — with more coverage
- Found 7 real, designer-confirmed bugs; riscv-formal found only 2 of them
- Scales to BOOM (out-of-order): 1,953 s avg vs riscv-formal 22,855 s
- A bug found in 0.52 s took symbolic execution 58 min

**Limitations**
- Bounded model checking (depth 40) — not a complete proof
- The synchronisation mechanism itself is unverified
- Slower than riscv-formal on very small designs

---

## SLIDE 6 — Supporting Paper 2: RISC-V Vector Accelerator
*Tag: 02 · LITERATURE SURVEY — PAPER 2*
Sub-line: Jiménez et al. · IEEE Design & Test · 2023 · European Processor Initiative

**Methodology**
- UVM testbench with one agent per Open Vector Interface sub-channel (7 total)
- Spike ISS as the golden model — every vector instruction co-simulated step by step
- 50+ SystemVerilog assertions for observability on memory interfaces
- Google RISCV-DV for constrained-random generation + Jenkins CI

**Key findings**
- 3,005 errors found over ~1 year of continuous verification
- 95.79% functional coverage reached
- Ran 24 → 600 tests/night; chip successfully taped out
- Memory / narrowing / widening ops = ~70% of failures

**Limitations**
- Code coverage only 72.64% (49.83% toggle) — authors admit
- Targets deprecated RVV 0.7.1, not ratified 1.0
- Experience report — engineering, not a new algorithm

---

## SLIDE 7 — Supporting Paper 3: INSTILLER
*Tag: 02 · LITERATURE SURVEY — PAPER 3*
Sub-line: Zhang, Wang, Yue, Liu, Guo & Lu · IEEE Trans. CAD of Integrated Circuits &
Systems · 2024

**Methodology**
- Coverage-guided fuzzing: random instruction streams, ISS vs RTL differential check
- Ant Colony Optimization (VACO) distills tests — circuits = cities, length = ants
- Realistic multi-interrupt and exception injection with priorities
- Hardware-aware seed selection and mutation

**Key findings**
- +29.4% coverage and +17.0% mismatches vs DiFuzzRTL
- Test inputs 79.3% shorter; +6.7% execution speed
- Disabling VACO alone → 417% longer inputs (ablation)
- Interrupts / exceptions = >10% of coverage prior tools scored 0 on

**Limitations**
- 2 of 4 target cores are OpenRISC, not RISC-V
- "Mismatches" are candidate bugs, not designer-confirmed
- Fuzzing can never prove the absence of bugs

---

## SLIDE 8 — Supporting Paper 4: Polynomial Formal Verification
*Tag: 02 · LITERATURE SURVEY — PAPER 4*
Sub-line: Weingarten, Datta & Drechsler · IEEE Trans. on Nanotechnology · 2025 · Univ. Bremen

**Methodology**
- Binary Decision Diagrams: canonical form → equivalence = pointer check
- Isolate one instruction: pin control signals, mark data unknown, delete constants
- Control unit verified as an FSM walk against a golden reference
- Novelty: proves a polynomial BOUND on verification time itself

**Key findings**
- Proven bounds: O(n) Fetch, O(n²) Execute/Decode, O(k·m) Control
- Entire Execute unit verified in 11.95 ms
- All 32 control signals verified (up from 15 in prior work)
- A complete guarantee — for every possible input

**Limitations**
- Only MicroRV32 — multi-cycle, NON-pipelined
- Excludes HALT, TRAP and interrupt states entirely
- Finds zero bugs; closed-source tool
- χRVFormal states in print it cannot handle pipelined cores

---

## SLIDE 9 — Supporting Papers at a Glance (table)
*Tag: 02 · LITERATURE SURVEY*

| Paper | Test generation | Correctness oracle | Headline number |
|---|---|---|---|
| χRVFormal | Exhaustive (formal) | Model checking vs spec | 7 real bugs; 4.6k vs 105k LOC |
| Vector Accelerator | Constrained-random | Spike golden model | 3,005 errors; 95.8% func. cov. |
| INSTILLER | Coverage-guided fuzz | ISS differential | +29% cov; −79% test length |
| PFV | Exhaustive (formal) | BDD equivalence | O(n²); Execute unit 11.95 ms |

**Takeaway:** Every supporting paper depends on a reference model or an exhaustive proof.
The base paper removes that dependency entirely — which is exactly why it was chosen.

---

## SLIDE 10 — Base Paper Overview
*Tag: 03 · LITERATURE SURVEY — BASE PAPER*
Sub-line: Gesper, Stuckmann, Wöbbekind & Payá-Vayá · Int. Journal of Parallel Programming
(Springer) · 2026

**Objective**
- Generate self-checking tests — with no external golden model
- Cover implementation-specific hazards the compliance suite misses
- Extend verification to an attached co-processor

**Main contributions**
- REVERSI self-test generation ported to RISC-V
- Pipeline hazard-sequence generator (pipeline-depth aware)
- Operand swapping + cache-miss generation
- Twin-based co-processor verification

**Headline result** (callout):  **79.12% → 100%** condition coverage vs the official
compliance suite. The suite found 0 bugs — PATARA exposed real hazard bugs in that same
"verified" core.

**Pipeline** (flow boxes): PATARA → REVERSI self-tests → Hazard + cache gen → Twin co-proc

---

## SLIDE 11 — Base Paper: The Problem
*Tag: 03 · BASE PAPER*

**The naive approach**
- Run the handwritten RISC-V compliance suite
- Same implementation-independent tests for every core
- Cannot target your pipeline depth, hazards, or cache config

**Why a golden model hurts**
- Reference simulators (Spike) are slow to run alongside RTL
- They carry their own bugs — two implementations, which is right?
- Impractical post-silicon: no internal observability on a real chip

**The trade-off that matters** (four rows, highlight the last)
- Handwritten suite — Low effort · no golden model · misses hazards
- Random + golden model — Adapts · but slow, reference can be wrong
- Formal verification — Complete · but poor scalability
- **PATARA (self-testing) — Adapts to implementation · NO golden model**

---

## SLIDE 12 — Base Paper: Core Mechanism (REVERSI)
*Tag: 03 · BASE PAPER*

**The key idea** (big): You do not need to know the right answer — you only need the
operation to be reversible.
- Add 7, then subtract 7. If you do not land back where you started, the hardware is
  broken — and you never needed a reference model.
- *Rule: the instruction under test appears ONLY in the modification step — so a systematic
  fault cannot cancel itself out during restoration.*

**Three-step flow** (boxes, highlight step 3):
1. **MODIFICATION** — `target = focus ⊕ random` — apply the instruction under test
2. **RESTORING** — `recovered = target ⊖ random` — apply its inverse
3. **COMPARISON** — `recovered == focus ?` — mismatch → hardware error

*(Optional: paste the paper's REVERSI figure here, captioned "Fig. — REVERSI self-test
structure (Gesper et al., 2026)".)*

---

## SLIDE 13 — Base Paper: Framework and Four Extensions
*Tag: 03 · BASE PAPER*
Sub-line (italic): Each extension patches a specific blind spot the previous configuration
leaves unreachable.

**XML-driven flow** — Processor + instruction set described in XML → selection → sequence
generation → self-checking assembly. ISA-independent.

**1 · Operand swapping** — Focus is always operand 1, so operand 2's forwarding path is
never tested. Swapping reaches it.

**2 · Hazard sequences** — All instruction-type permutations, sequence length sized to
pipeline depth (6 stages → 4 instrs).

**3 · Cache-miss generation** — Forces d-cache / i-cache misses to exercise stall × hazard
interactions.

**4 · Twin-based co-processor verification** (callout) — Many co-processor operations
(ABS, MIN/MAX, multiply) are not invertible, so REVERSI cannot apply. Instead the same
operation runs on the co-processor AND as software on the already-verified RISC-V core, and
the results are compared. The verified core becomes the golden model — no external
reference, and it works post-silicon.

---

## SLIDE 14 — Base Paper: Experimental Results (table + callouts)
*Tag: 03 · BASE PAPER*
Sub-line: DUT: 6-stage RV32IM core + V2PRO vector co-processor · Simulator: Questa Sim ·
Metric: code coverage (%). Highlight the last row.

| Configuration | Instructions | Condition cov. |
|---|---|---|
| Compliance suite (baseline) | 889,516 | 79.12% |
| Instruction combinations | 6,983 | 80.21% |
| + operand switching | 9,722 | 81.31% |
| + interleaving | 17,294 | 81.31% |
| + hazard sequences | 1,851,852 | 96.70% |
| **+ cache tests (full PATARA)** | **6,732,901** | **100.00%** |

**Key observations**
- +20.88 pts condition coverage over the compliance suite
- First config beats the suite with 127× fewer instructions
- Interleaving alone adds 0.00 pts — variety ≠ coverage

**Ablation** (callout): Removing hazard-sequence generation drops condition coverage to
81.31%. The compliance suite found 0 bugs; PATARA exposed 4 categories of real
hazard-interaction bugs.

---

## SLIDE 15 — Applications and Relevance
*Tag: 04 · APPLICATIONS*

**What it enables**
- Verifies a customized core the compliance suite cannot fully reach
- Self-checking tests run post-silicon with no golden model
- Twin method verifies an attached accelerator / co-processor

**Transferable insight**
- Separate the two questions: test generation vs. correctness oracle
- When no golden model exists, invertibility or a twin can replace it
- Coverage is necessary but not sufficient — 100% ≠ bug-free

**Relevance to our project (Team 2)**
- We are extending a RISC-V core with custom AI / vector instructions for edge video
  anomaly detection — exactly the scenario PATARA targets
- Custom instructions have no golden reference — the paper's core problem
- Invertible ops (e.g. ADD+1) → REVERSI self-test directly
- Non-invertible ops (e.g. packed abs-diff) → twin-based method
- The accelerator we integrate maps onto the co-processor twin flow

*Limitations: RV32IM only (no floating point) · CSRs and interrupts out of scope · single
design evaluated.*

---

## SLIDE 16 — Comparison with Alternate Approaches (table)
*Tag: 05 · COMPARISON. Highlight the PATARA row.*

| Paper | Approach | Strength | Main limitation |
|---|---|---|---|
| χRVFormal | High-level formal | Proves spec conformance; 7 real bugs | Bounded (depth 40) |
| Vector Accelerator | UVM + golden model | Industrial scale; 3,005 bugs; taped out | Code cov. only 72.6% |
| INSTILLER | Coverage-guided fuzz | Short tests; finds unthought-of cases | Incomplete; 2 non-RISC-V cores |
| PFV | BDD formal | Proven runtime bound; complete | Non-pipelined toy core |
| **PATARA (base)** | Self-testing | No golden model; 100% cov; post-silicon | RV32IM; no CSR / interrupts |

**Why the base paper was chosen:** PATARA is the only approach that verifies a customized
RISC-V core without a golden reference — the exact obstacle our custom instructions create.
It fuses systematic test generation, self-checking execution, and a twin-based co-processor
method, and directly matches our project's architecture and workflow.

---

## SLIDE 17 — Conclusion (one dense paragraph)
*Tag: 06 · CONCLUSION*

Across the surveyed work, RISC-V verification splits along two axes — where tests come from,
and how correctness is decided. Formal methods (χRVFormal, PFV) give complete guarantees but
trade away either scalability or completeness; industrial UVM co-simulation (Vector
Accelerator) and coverage-guided fuzzing (INSTILLER) scale to real cores but depend on a
reference model and can never prove the absence of bugs. The base paper, PATARA, fuses
systematic test generation with self-checking execution, removing the golden-model
dependency entirely — reaching 100% condition coverage where the official compliance suite
reached 79.12% and found no bugs, while exposing real hazard-interaction defects in that
same design. For our project, where custom instructions have no golden reference by
definition, this confirms self-testing and twin-based verification as the practical path
forward — and points toward extending it to floating-point and privileged-mode coverage.

---

## SLIDE 18 — References (IEEE style)
*Tag: 07 · REFERENCES*

[1] S. Gesper, F. Stuckmann, L. Wöbbekind & G. Payá-Vayá, "A Self-Testing Framework for
Verification and Validation of a RISC-V-Based System with a Co-processor," *Int. J. Parallel
Programming*, vol. 54, art. 15, 2026. **(BASE PAPER)**

[2] S. Shen, S. Chen, Y. Liu, L. Zhang, F. Song & Z. Wu, "χRVFormal: Formal verification of
RISC-V processor Chisel designs," *Journal of Systems Architecture*, vol. 175, 103761, 2026.

[3] V. Jiménez et al., "Functional Verification of a RISC-V Vector Accelerator," *IEEE
Design & Test*, vol. 40, no. 3, pp. 36–44, 2023.

[4] G. Zhang, P. Wang, T. Yue, D. Liu, Y. Guo & K. Lu, "INSTILLER: Toward Efficient and
Realistic RTL Fuzzing," *IEEE Trans. CAD of Integrated Circuits and Systems*, vol. 43,
no. 7, pp. 2177–2190, 2024.

[5] L. Weingarten, K. Datta & R. Drechsler, "Polynomial Formal Verification of a RISC-V
Processor," *IEEE Trans. on Nanotechnology*, vol. 24, pp. 140–151, 2025.

[6] A. Waterman & K. Asanović, "The RISC-V Instruction Set Manual, Volume I: Unprivileged
ISA," RISC-V International, 2019.

[7] E. Shazli & M. Tehranipoor, "REVERSI: Post-silicon validation via self-checking
randomized test programs" (foundational REVERSI method extended by the base paper).

---

### Figures worth adding (from the PDFs) to lift it to reference quality
- **Slide 12:** REVERSI modify→restore→compare figure from the base paper
- **Slide 13:** PATARA framework / XML-flow diagram from the base paper
- **Slide 5:** χRVFormal approach overview (Fig. 1)
- **Slide 6:** the vector accelerator / OVI block diagram
Caption each: *"Fig. N — <description> (Author et al., Year)."*
