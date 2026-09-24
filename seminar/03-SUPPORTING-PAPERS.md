# Seminar Papers — Summaries & Talking Points

**Seminar topic:** Verification Methodologies for RISC-V Processors
**Student:** Kevin Jose — Team 2

The base paper (PATARA) is covered first, including why it was chosen as the
base paper. The four supporting papers follow. Each entry: what it is, what it
does, why it's in the set, honest weaknesses, and a 30-second verbal version
for the guide meeting. (Full-depth PATARA notes are in
`01-PATARA-FULL-EXPLAINER.md`.)

---

# BASE PAPER — PATARA: A Self-Testing Framework for Verification and
# Validation of a RISC-V-Based System with a Co-processor

**Gesper, S., Stuckmann, F., Wöbbekind, L. & Payá-Vayá, G. (2026)**
*International Journal of Parallel Programming*, 54(15).
doi: 10.1007/s10766-026-00824-8. TU Braunschweig. Springer, SCIE/Scopus.
Open access.

**What it is:** A framework that auto-generates test programs which **check
themselves** — no external golden reference model needed. Built on the REVERSI
approach: apply an instruction, apply its inverse, and confirm you get back
what you started with. Add 7, subtract 7 — if you don't land where you began,
the hardware is broken, and you never needed to know the "correct" answer.

**The problem it attacks:** The official RISC-V compliance suite is handwritten
and implementation-independent — it can't target *your* pipeline depth, hazard
logic, or cache configuration. And most automated generators need a golden
reference model (a simulator like Spike) to check answers, which is slow,
carries its own bugs, and is impractical post-silicon.

**What they did:** REVERSI self-tests + four extensions that each patch a
specific blind spot — (1) hazard sequence generation (all instruction-type
permutations, sized to pipeline depth), (2) operand swapping (reaches the
second operand's forwarding path, which is otherwise never tested), (3)
cache-miss generation, (4) a twin-based method for the co-processor (run the
same op on the co-processor and on the already-verified RISC-V core, compare).

**Headline result:** The official compliance suite ran on their 6-stage RV32IM
core and **found zero bugs — the design passed** — while leaving condition
coverage at **79.12%**. PATARA reached **100%** and found real hazard-
interaction bugs in that same "verified" design (forwarding during multi-cycle
division; cache miss during multiply; load→JALR forwarding; cache-miss/stall
combinations).

**Weaknesses (state them openly):**
- REVERSI itself is from prior work (Shazli & Tehranipoor); the contributions
  are the RISC-V port, the four extensions, and the twin method
- RV32IM only — no floating point (our build enables hardfloat)
- CSRs, interrupts, and the privileged spec are explicitly out of scope
- Only one design evaluated (their own core)
- §5.6 admits 100% code coverage does not guarantee correctness

## Why this was chosen as the base paper

1. **It matches our project's architecture almost exactly.** It verifies a
   custom RISC-V implementation with custom ISA extension support and an
   attached co-processor — a description of what Team 2 is building.

2. **It documents custom ISA extension support (§4.2).** Our custom
   instructions map onto its XML-based flow — ADDP1 is invertible (restore with
   SUB + ADDI -1); our non-invertible instruction would use the twin method,
   exactly as the paper did for the co-processor's ABS.

3. **It directly challenges what we currently do.** We conclude our core works
   because compliance tests pass. This paper's central finding is that passing
   the compliance suite is not the same as being correct — a live question for
   our project, not an abstract one.

4. **I can present it from experience.** I have run the compliance suite,
   inspected instruction traces, and debugged with waveforms — the exact
   workflow the paper analyses.

5. **Practical:** open access, PDF in hand, hard copy ready for signature.
   (Both IEEE papers in the set are paywalled.)

6. **It anchors the whole set.** It is the only paper that avoids a golden
   model entirely — which is precisely its argument — so every supporting paper
   defines itself against something PATARA does or deliberately refuses to do.

**30-sec verbal:**
> "My base paper's finding is that the official RISC-V compliance suite passed
> their processor with zero bugs while leaving a fifth of the design's logical
> conditions untested — and better tests then found real bugs in that same
> design. That's directly relevant to us, because passing the compliance suite
> is exactly how we currently conclude our core works. It also documents
> support for custom ISA extensions and for verifying an attached co-processor,
> both of which our project needs."

---

## How the five papers fit together

Verification has two separable parts: (a) where the tests come from, and
(b) how correctness is decided. Presenting the set on these two axes is
stronger than a flat "five techniques" list, because it shows the real
overlaps rather than hiding them.

| Paper | Where tests come from | How correctness is decided |
|---|---|---|
| **PATARA** (base) | Systematic — all instruction-type permutations | **Self-checking** (invertibility) + software twin |
| Vector Accelerator | Constrained-random + directed | **Golden model** (Spike) |
| INSTILLER | **Coverage-guided**, self-optimising | Golden model (ISS) |
| χRVFormal | None — exhaustive by construction | **Formal** — model checking vs Chisel spec |
| PFV | None — exhaustive by construction | **Formal** — BDD equivalence checking |

- Papers 2 and 3 share an oracle (a reference simulator) but sit at opposite
  ends of the generation axis (hand-directed vs self-optimising feedback loop).
- Papers 4 and 5 share an approach (formal proof) but differ enormously in
  scale — and disagree in print about whether the BDD approach scales.
- The base paper is the only one that avoids a golden model entirely, which
  is precisely its argument.

---

# SUPPORTING PAPERS

---

# 1. χRVFormal — Formal Verification of RISC-V Processor Chisel Designs

**Shen, S. et al. (2026)** *Journal of Systems Architecture*, 175, 103761.
Chinese Academy of Sciences. Elsevier, SCIE/Scopus.

**What it is:** Formal verification — mathematically proving a design matches
the RISC-V spec for all inputs, rather than testing with examples.

**The problem:** To prove a processor correct you need the spec in
machine-readable form. The existing standard tool, riscv-formal, has a
reference model of **104,911 lines of Verilog** — unmaintainable, and despite
its size it supports no privileged instructions, no CSRs, no virtual memory.

**What they did:** Rewrote the reference model in **Chisel** (a high-level HDL)
in **4,609 lines** — ~4% the size, with *more* coverage: three privilege
levels, CSRs, Sv39 virtual memory. Plus a synchronisation mechanism (two
strategies: StateCheck and ActionCheck) so a single-cycle reference model can
be compared against a pipelined or out-of-order processor. Backend: transition
system → model checkers Pono/SMTBMC with Boolector.

**Result:** **7 previously-unknown real bugs** in riscv-mini and NutShell,
confirmed by the original designers (riscv-formal found only 2). All 15
injected bugs found. Works on BOOM (out-of-order superscalar). Example bugs:
`mtval` high bits not writable; Sv39 physical addresses 32-bit instead of
56-bit; missing privilege check on `SRET`.

**Weaknesses:**
- Loses on small designs (riscv-mini: 3.1 s vs riscv-formal's, χRVFormal 13.7 s)
- The synchronisation mechanism itself is not formally verified (they say so)
- Bounded model checking to depth 40 — proves no bug within 40 cycles, not a
  complete proof; unbounded methods (k-induction, PDR) were too large to finish

**Chisel objection, answered:** Chisel and Bluespec are both high-level HDLs
that generate Verilog — same relationship. The paper explicitly supports a
Verilog/SystemVerilog flow. Its thesis (verify at high-level source, not
generated Verilog) applies more directly to a Bluespec project, not less.

**Why it's in the set:** The formal-methods pillar. RISC-V-native, real
confirmed bugs, handles a complex core. Directly critiques PFV in print, which
gives the comparison section a real argument.

**30-sec verbal:**
> "This is the formal verification paper. The existing standard tool needs a
> 105,000-line Verilog reference model that's unmaintainable and doesn't cover
> privileged instructions. These authors rewrote it in Chisel in 4,600 lines
> with better coverage, and found seven real bugs the old tool missed five of.
> It's the counterpart to my base paper — PATARA checks internal consistency,
> this checks conformance to the actual specification."

---

# 2. Functional Verification of a RISC-V Vector Accelerator

**Jiménez, V. et al. (2023)** *IEEE Design & Test*, 40(3), pp. 36–44.
Barcelona Supercomputing Center, European Processor Initiative. SCIE/Scopus.

**What it is:** An industrial verification campaign for **Vitruvius+**, a RISC-V
vector coprocessor (8 lanes, up to 256×64-bit elements, one FMA per lane),
connected to a scalar core over the 7-channel Open Vector Interface. The chip
**taped out**. This is original engineering work and results — NOT a survey.

**How they verified it:** Run every vector instruction twice — once on the real
design, once on **Spike** (the trusted RISC-V simulator, the *golden model*) —
and compare via a UVM scoreboard. Four techniques stacked:
1. **UVM testbench** — one agent per sub-interface; only ISSUE is randomised,
   the other six react (the interdependence made full random infeasible)
2. **Spike as golden model** — acts as both scalar core and reference
3. **50+ SystemVerilog assertions** — mostly on memory interfaces, for
   observability (a mismatch says *something* broke, not *where*)
4. **RISCV-DV** (Google's random generator), extended for vectors
Plus **Jenkins CI** running 24 → 600 tests/day for about a year.

**Result:** **3,005 errors found** over ~1 year. 95.79% functional coverage.
Code coverage only 72.64% (49.83% toggle) — which they honestly admit.

**Weaknesses:**
- Low code coverage, acknowledged ("not driving the design appropriately")
- Targets RVV 0.7.1, a deprecated draft, not ratified 1.0
- They criticise their own 7-agent architecture; would use one agent next time
- 9-page experience report — engineering contribution, no novel algorithm

**Why it's in the set — best comparison pairing:** The direct opposite of the
base paper. PATARA's premise is *avoid* the golden model; this is built
entirely *around* one. Both verify a RISC-V co-processor:

| | PATARA | Vector Accelerator |
|---|---|---|
| Golden model | None | Spike |
| Code coverage | **100%** | 72.64% |
| Errors found | "several" | **3,005** |
| Silicon | FPGA + 45nm | **Taped out** |

PATARA wins on coverage; this wins on bugs found + industrial validation.
**High coverage and high bug yield are not the same thing** — the most
interesting observation in the whole set. Citable link: PATARA's related-work
criticises RISCV-DV by name; this paper uses RISCV-DV.

**30-sec verbal:**
> "This is the industry-practice paper. They verified a vector coprocessor by
> running every instruction twice — real design vs a trusted simulator — and
> comparing. Found 3,005 errors, and the chip shipped. It's the opposite of my
> base paper, which argues you shouldn't need a reference simulator. The
> interesting bit: PATARA gets better coverage, this finds far more bugs."

---

# 3. INSTILLER — Toward Efficient and Realistic RTL Fuzzing

**Zhang, G. et al. (2024)** *IEEE Transactions on Computer-Aided Design of
Integrated Circuits and Systems*, 43(7), pp. 2177–2190. NUDT. Best venue in
the set.

**What it is:** Fuzzing for CPUs — bombard the design with random instruction
sequences, run them through both a reference simulator and the RTL, and flag
disagreements ("mismatches") as candidate bugs. This is *coverage-guided* — a
closed feedback loop where coverage steers what gets generated next.

**Three problems attacked:**
1. **Tests bloat** — sequences grow longer over time but coverage doesn't grow
   proportionally; simulation time is wasted
2. **Interrupts under-tested** — prior tools handle one simple interrupt, no
   exceptions/priorities; the authors show >10% of coverage and ~10% of bugs
   live there, where old tools score zero
3. **Software-derived heuristics** — ignore hardware specifics

**What they built:**
- **Input distillation via ant colony optimization (VACO)** — ants converge on
  short paths via pheromone trails; mapped as "circuits = cities, test length =
  ants." Keeps tests short and effective; triggers when coverage-per-length
  declines
- **Realistic interrupts/exceptions** — 9 interrupts, 14 exceptions, up to 3
  each, with priority handling
- **Hardware-aware seed selection and mutation**

**Result vs DiFuzzRTL (previous best), 10× 24h runs, stats-tested:**
+29.4% coverage, +17.0% mismatches, **−79.3% test length**, +6.7% speed.
Ablation: disabling VACO → 417% length increase. Targets: Rocket, BOOM (+ two
OpenRISC cores).

**Weaknesses:**
- Two of four target cores (mor1kx, or1200) are **OpenRISC, not RISC-V**
- "Mismatches" are candidate bugs, not designer-confirmed
- Loses on mor1kx (DiFuzzRTL finds more)
- Fuzzing can never prove absence of bugs

**Why it's in the set:** The randomised, self-optimising test-generation family.
Best venue (IEEE TCAD). Quantifies the base paper's blind spot: PATARA excludes
CSRs/interrupts/privileged spec; INSTILLER measures what that costs.

**Note on overlap with paper 2:** both use differential testing against a
reference simulator (same oracle). The difference is in *generation* — paper 2
is hand-directed + constrained-random (open loop); INSTILLER is
coverage-guided and self-optimising (closed loop). Present it as
"self-optimising test generation," not "a different way of checking."

**30-sec verbal:**
> "This is the fuzzing paper — random instruction sequences thrown at the
> processor, compared against a reference simulator. Their trick is an
> ant-colony algorithm that keeps tests short instead of letting them bloat —
> 29% more coverage with 79% shorter tests. From IEEE TCAD, the top EDA
> journal. It measures something my base paper openly doesn't cover: interrupts
> and exceptions, where about 10% of bugs live."

---

# 4. Polynomial Formal Verification of a RISC-V Processor

**Weingarten, L., Datta, K. & Drechsler, R. (2025)** *IEEE Transactions on
Nanotechnology*, 24, pp. 140–151. University of Bremen / DFKI.

**What it is:** Formal verification with a twist — it doesn't just prove the
design correct, it proves a **mathematical bound on how long the verification
itself takes** (polynomial, not exponential).

**The problem it solves:** Formal verification's practical flaw is
unpredictable runtime — might finish instantly or never. Proving a polynomial
bound makes it plannable, which is what industry complains is missing.

**How it works:** Uses **Binary Decision Diagrams** — a canonical logic
representation where two equivalent circuits produce identical graphs, so
comparison is a pointer check. To verify one instruction: pin control signals
to select it, mark data as unknown (ternary 0/1/x), simulate, delete every node
that collapsed to a constant — what remains is only that instruction's logic —
then compare its BDD to a reference BDD built from the maths. Control unit
handled as an FSM walk instead.

**Result:** Proven bounds — O(n) Fetch, O(n²) Execute/Decode, O(k·m) Control.
Entire Execute unit verified in ~12 ms. All 32 control signals (up from 15 in
prior work).

**Weaknesses — and these are the POINT of including it:**
- Processor is **MicroRV32: multi-cycle, non-pipelined**. No hazards, no
  forwarding. Every other paper in the set uses real cores
- Explicitly excludes HALT, TRAP, INTP states — no interrupts
- **Finds zero bugs** — verifies an already-correct design, reports timing
- Closed-source tool
- **χRVFormal states in print** that this BDD approach "cannot be applied to
  verify pipelined RISC-V processor designs"

**Why keep a paper with these problems:** The weaknesses are the argument. The
seminar is about *trade-offs*, and formal verification's trade is complete
guarantees for poor scalability. PFV is that trade at its extreme — it uniquely
offers a *proven verification-time bound*, and pays with a processor too simple
to be real. Next to χRVFormal (handles BOOM, but only bounded to depth 40), you
get a genuine argument: formal methods scale only by giving something up —
either design complexity (PFV) or completeness of proof (χRVFormal). And two
papers in the set disagree in print, which makes the comparison feel like
analysis, not summary.

**30-sec verbal:**
> "This is the most rigorous paper in my set and, deliberately, the most
> limited. Formal verification, with the added contribution of proving how long
> the verification itself takes — which is what stops industry using formal
> methods. But it only works on a tiny non-pipelined processor and skips
> interrupts. I included it to show formal verification's ceiling — and because
> another paper in my set states in print that this approach can't scale to
> pipelined designs. That disagreement is the heart of my comparison."

---

# The three tensions for the comparison slide (guideline 5b)

1. **Golden model vs none** — Vector Accelerator (Spike) vs PATARA (self-check)
2. **Systematic vs random vs proof** — PATARA vs INSTILLER vs χRVFormal/PFV
3. **Scalability vs completeness** — χRVFormal (BOOM, bounded) vs PFV
   (toy core, complete + time-bounded)

Each tension has papers on both sides. That is what turns a summary into an
argument.
