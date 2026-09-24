# Seminar Paper Approval — Briefing Notes

**Student:** Kevin Jose
**Project team:** Team 2 — Design of a Custom RISC-V Processor with AI and Vector Extensions
**Proposed seminar topic:** *Verification Methodologies for RISC-V Processors*

---

## 1. Why this topic

Our team is not designing a RISC-V core from scratch — we are taking an existing open-source
core (Shakti C-Class has been used for architectural study; the final target core is still
being decided) and extending it with custom instructions for edge video anomaly detection.
The work I have personally been doing is **verification**: running RISC-V
compliance tests (`add.S`, `fadd.S`), checking `tohost` results in instruction traces, and
debugging with waveform analysis in GTKWave.

Verification is therefore the aspect of the project I can speak about from direct experience,
and it is a distinct aspect from my teammates' topics:

| Team member | Seminar aspect |
|---|---|
| Junit Sarah Varghese | Custom instruction set extensions for AI acceleration |
| Eapen Luke | RISC-V vector extension for AI and edge computing |
| Devmanas S | *(to be confirmed)* |
| **Kevin Jose** | **Verification methodologies** |

This satisfies guideline 1(b) — team members choosing topics so that various aspects of the
project are covered.

---

## 2. Proposed papers

### Base paper

> **Gesper, S., Stuckmann, F., Wöbbekind, L. and Payá-Vayá, G. (2026)** 'A Self-Testing
> Framework for Verification and Validation of a RISC-V-Based System with a Co-processor',
> *International Journal of Parallel Programming*, 54(15). doi: 10.1007/s10766-026-00824-8

| Criterion | Status |
|---|---|
| Journal (not conference) | ✔ Springer |
| SCIE / Scopus indexed | ✔ |
| Published 2020–26 | ✔ 2026 |
| Not a survey / review | ✔ Original research |
| Open access — hard copy available | ✔ |

### Four supporting papers

| # | Paper | Venue | Year | Technique family |
|---|---|---|---|---|
| 1 | χRVFormal: Formal Verification of RISC-V Processor Chisel Designs | *Journal of Systems Architecture* (Elsevier) | 2026 | Formal — model checking |
| 2 | INSTILLER: Toward Efficient and Realistic RTL Fuzzing | *IEEE Trans. CAD of ICs and Systems* | 2024 | Coverage-guided RTL fuzzing |
| 3 | Polynomial Formal Verification of a RISC-V Processor | *IEEE Trans. Nanotechnology* | 2025 | Formal — BDD-based |
| 4 | Functional Verification of a RISC-V Vector Accelerator | *IEEE Design & Test* | 2023 | UVM co-simulation vs golden model |

All four are journal articles from IEEE / Springer / Elsevier, none are surveys, all
within 2020–26.

**Full citations for the supporting papers**

> Shen, S., Chen, S., Liu, Y., Zhang, L., Song, F. and Wu, Z. (2026) 'χRVFormal: Formal
> verification of RISC-V processor Chisel designs', *Journal of Systems Architecture*, 175,
> 103761.

> Zhang, G., Wang, P., Yue, T., Liu, D., Guo, Y. and Lu, K. (2024) 'INSTILLER: Toward
> Efficient and Realistic RTL Fuzzing', *IEEE Transactions on Computer-Aided Design of
> Integrated Circuits and Systems*, 43(7), pp. 2177–2190.

> Weingarten, L., Datta, K. and Drechsler, R. (2025) 'Polynomial Formal Verification of a
> RISC-V Processor', *IEEE Transactions on Nanotechnology*, 24, pp. 140–151.

> Jiménez, V., Rodríguez, M., Domínguez, M., Sans, J., Diaz, I., Valente, L., Guglielmi, V.L.,
> Quiroga, J.V., Genovese, R.I., Sonmez, N., Palomar, O. and Moretó, M. (2023) 'Functional
> Verification of a RISC-V Vector Accelerator', *IEEE Design & Test*, 40(3), pp. 36–44.
> doi: 10.1109/MDAT.2022.3226709

---

## 3. Why this base paper

**1. It matches our project's architecture almost exactly.** The paper verifies a custom
RISC-V implementation that has custom ISA extension support and an attached co-processor.
That is a description of what Team 2 is building — an extended open-source core, our `ADDP1` custom
instruction, and the ECE team's hardware accelerator.

**2. It directly challenges what we are currently doing.** We conclude our core works because
compliance tests pass. This paper's central finding is that on their own 6-stage RV32IM
processor, the official compliance suite **found zero bugs and declared the design correct** —
while leaving 21% of logical conditions untested. Better tests then found **real bugs** in
that same design. That is a live question for our project, not an abstract one.

**3. It documents custom ISA extension support.** Section 4.2 describes adding custom
instructions to the framework via XML description files. Our `ADDP1` instruction
(`rd = rs1 + rs2 + 1`) is invertible and maps directly. Our planned packed absolute-difference
instruction is not invertible — and the paper documents the alternative (twin-based)
methodology for exactly that case.

**4. I can present it from experience.** I have run the compliance suite, inspected
instruction traces, and debugged with waveforms. This is the workflow the paper analyses.

**5. Practical.** Open access, PDF obtained, hard copy ready for signature.

---

## 4. Headline results (for the approval discussion)

| Metric | Official compliance suite | PATARA |
|---|---|---|
| Statement coverage | 99.40% | 100.00% |
| **Condition coverage** | **79.12%** | **100.00%** |
| FSM transition coverage | 88.63% | 100.00% |
| Bugs found | **0** | Several (4 categories) |

Bugs the compliance suite missed, all in pipeline control logic:
- Forwarding during an unfinished multi-cycle division
- Cache miss occurring during a multi-cycle multiply
- Load → JALR forwarding
- Cache-miss / stall condition combinations

**Common pattern:** none are single-instruction arithmetic errors. All are *interactions*
between two or three mechanisms — which handwritten tests systematically miss because humans
test features one at a time.

---

## 5. How the five papers fit together

The set covers the complete verification lifecycle, with each paper representing a distinct
technique family:

```
   PATARA           →  generate tests targeting THIS implementation
   (base)              self-testing, NO golden model, works post-silicon
        ↕  ← direct methodological opposition
   Vector           →  UVM + Spike co-simulation, assertions, CI
   Accelerator         WITH a golden model — the industrial standard
        ↓
   INSTILLER        →  find bugs nobody thought to test for
                       randomized fuzzing of CPU RTL
        ↓
   χRVFormal        →  prove conformance to the ISA specification
   + PFV               formal methods — and where they hit scalability limits
```

**The central tension the set explores — the golden model question.**
My base paper's entire premise is *avoiding* a reference model: reference simulators are slow,
introduce their own bugs, and are impractical post-silicon. The Vector Accelerator paper takes
the opposite position, building its whole environment around Spike co-simulation. Both verify
a RISC-V co-processor. Their results are instructive:

| | PATARA | Vector Accelerator |
|---|---|---|
| Golden model | None (self-checking) | Spike co-simulation |
| Code coverage | **100%** | 72.64% (49.83% toggle) |
| Functional coverage | — | 95.79% |
| Errors found | "several" | **3,005** |
| Silicon status | FPGA + 45nm | **Taped out** |

PATARA wins decisively on coverage; the Vector Accelerator paper wins decisively on bugs found
and industrial validation. **High coverage and high bug yield are not the same thing** — that
is the most interesting comparison in the set, and it is a genuine finding rather than a
manufactured contrast.

**A second, citable cross-paper link.** PATARA's related work section explicitly positions
against **RISCV-DV** (Google's random instruction generator), noting it *"uses a reference
simulator to verify execution traces."* The Vector Accelerator paper uses RISCV-DV and Spike
directly, and describes the extensions they had to make to it. My base paper therefore
critiques, by name, the exact approach one of my supporting papers embodies.

**A third cross-paper argument.** χRVFormal's related work section directly critiques the
Polynomial Formal Verification approach, stating that BDD-based formal verification *"cannot
be applied to verify pipelined RISC-V processor designs."* Two of my papers are in printed
disagreement — relevant to us, since the core we extend is pipelined.

---

## 6. Known limitations — stated upfront

I have read all five papers in full and want to be transparent about their weaknesses:

**Base paper (PATARA)**
- The REVERSI method itself is from prior work (Shazli & Tehranipoor). The authors'
  contributions are the RISC-V port, four framework extensions, and the twin-based
  co-processor method
- Covers RV32IM only — no floating point (our build enables hardfloat)
- CSRs, interrupts and the privileged specification are explicitly out of scope
- Only one design evaluated (their own core)
- Bug reporting is one paragraph, self-reported, without external confirmation
- The authors themselves state (§5.6) that 100% code coverage does **not** guarantee
  correctness

**Supporting papers**
- *Polynomial Formal Verification* verifies a non-pipelined toy processor (MicroRV32) and
  explicitly excludes interrupt and trap states. It is included deliberately, as the
  illustration of where formal methods hit their scalability ceiling
- *INSTILLER* — two of its four target cores (mor1kx, or1200) are OpenRISC rather than RISC-V
- *χRVFormal* — its case studies are written in Chisel rather than Verilog. The paper
  explicitly supports a Verilog/SystemVerilog flow as an alternative, and Chisel is a
  high-level HDL that generates Verilog — the same relationship Bluespec has to Verilog
- *Functional Verification of a RISC-V Vector Accelerator* — it is a "General Interest"
  article (9 pages), closer to an industrial experience report than a full research paper;
  it targets RVV 0.7.1 rather than the ratified 1.0; and its code coverage is low (72.64%
  average, 49.83% toggle), which the authors acknowledge

---

## 7. Guideline compliance checklist

| Guideline | Status |
|---|---|
| 1(a) Topic current and closely related to project research area | ✔ Verification is my direct project work |
| 1(b) Team members cover various aspects of the project | ✔ Distinct from ISA extension / vector / accelerator topics |
| 4(a) Base paper 2020–26, SCI/SCIE/SCOPUS indexed | ✔ Springer, SCIE/Scopus, 2026 |
| 4(a) Base paper helps team's comprehensive literature review | ✔ Directly addresses our verification workflow and custom instructions |
| 4(b) Hard copy for guide approval | ✔ Open access, printed |
| 4(c) At least four further journal / reputed conference papers | ✔ Four journal papers (IEEE ×3, Springer, Elsevier) |
| 5(b) Comparative analysis of methodologies | ✔ Five distinct technique families; comparison table prepared |

**Coverage of technique families**

| Family | Paper |
|---|---|
| Self-testing test generation (no golden model) | PATARA *(base)* |
| Simulation-based UVM co-simulation (with golden model) | Vector Accelerator |
| Randomized fuzzing | INSTILLER |
| Formal — model checking | χRVFormal |
| Formal — BDD with complexity bounds | PFV |

Four of the five are RISC-V-specific; three involve co-processors or accelerators.

---

## 8. Questions for the guide

1. Is the base paper choice appropriate, or would you prefer one with a stronger venue
   (χRVFormal in *Journal of Systems Architecture*, or INSTILLER in IEEE TCAD) even though
   they are less directly connected to our project?

2. The guidelines permit *"journal articles / reputed conference proceedings"* for the four
   supporting papers. I have restricted myself to journals only. If conference papers are
   acceptable, one further substitution is available — a 2025 IEEE paper on **RISC-V
   floating-point verification** (efficient coverage models and constraint-based test
   generation, benchmarked against Google's RISCV-DV). It would cover floating point, which
   my base paper explicitly excludes and which our build enables via hardfloat.

3. Devmanas and I may need to swap subtopics — he was provisionally assigned verification
   while I had "Hardware Accelerators for CNN Inference on FPGA." Should this be confirmed
   with the seminar coordinator before proceeding?

---

## 9. One-paragraph summary (if asked for a verbal pitch)

> My seminar covers verification methodologies for RISC-V processors — how you establish that
> a processor actually does what the specification says, which is the exact work I have been
> doing on our team's core. My base paper is a 2026 Springer journal article presenting
> PATARA, a self-testing verification framework. Its central result is that the official
> RISC-V compliance test suite passed their processor with zero bugs while leaving 21% of
> logical conditions untested — and when they generated better tests, they found real bugs in
> that same "verified" design. It also documents support for custom ISA extensions and for
> verifying an attached co-processor, both of which our project needs. The four supporting
> papers cover the other major technique families: UVM co-simulation against a golden model,
> randomized RTL fuzzing, and two formal-verification approaches. The most interesting
> comparison is between my base paper, which deliberately avoids a golden reference model, and
> the Vector Accelerator paper, which builds its entire environment around one — the first
> reaches 100% code coverage, the second found 3,005 errors and taped out in silicon.
