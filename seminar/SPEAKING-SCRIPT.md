# Seminar Speaking Script — Verification Methodologies for RISC-V Processors
**Kevin Jose · Guide: Dr. Jomina John**

How to use this: each slide has **SAY** (natural spoken lines — don't read verbatim, talk it) and **KEYWORDS** (plain definitions you can drop in if you say the term or get asked). Aim ~30–60 seconds per content slide.

> ⚠️ FIX BEFORE PRESENTING: Slide 4 ROLE column still says "Survey" for papers 1–4. Change to "Supporting" — they are not survey papers.

---

## Slide 1 — Title

**SAY:**
"Good morning. My seminar is on Verification Methodologies for RISC-V Processors. It's tied to my main project, where our team is building a custom RISC-V processor with AI and vector extensions — so the question of *how you prove a processor is actually correct* is something we deal with directly. I'll cover five papers: four supporting papers and one base paper."

---

## Slide 2 — Agenda

**SAY:**
"I'll start with the introduction and motivation, then walk through the four supporting papers, then do a deeper dive on the base paper. After that: how it applies to our project, its advantages and limitations, a comparison across all five papers, and a conclusion."

*(Keep this short — 10 seconds. Don't read all 8 items aloud; just signal the shape.)*

---

## Slide 3 — Introduction & Motivation

**SAY:**
"RISC-V is an open, royalty-free instruction set — anyone can use it and, importantly, anyone can add their own custom instructions. That's exactly what our project does. But once a processor is fabricated, a bug can't be patched — so verification really matters. Verification just means establishing that the processor actually behaves the way its specification says.

The motivation for this whole topic is on the right: the official RISC-V compliance suite is handwritten, and it's the *same* tests for every core. So it can't target *your* specific pipeline, your hazard logic, or your cache. And that leads to the theme of my whole seminar — passing the compliance suite is *not* the same as being correct."

**KEYWORDS:**
- **ISA (Instruction Set Architecture):** the list of instructions a processor understands — the contract between software and hardware.
- **Compliance suite:** a standard set of hand-written test programs from RISC-V International that every core is expected to pass.
- **Verification:** proving the hardware does what the spec says (vs *testing*, which only checks specific cases).

---

## Slide 4 — Literature Survey Overview

**SAY:**
"Here are my five papers. Four are supporting papers, each representing a *different* verification approach — formal verification, golden-model testing, fuzzing, and polynomial formal verification — and the fifth is my base paper, which uses self-testing with no golden model. I chose them so each one covers a different point on the spectrum of how you decide a processor is correct."

*(Point across the CORE APPROACH column — that's the useful column. Don't read author lists.)*

**KEYWORDS:**
- **Golden (reference) model:** a trusted implementation, like the simulator Spike, that tells you the correct answer to compare against.

---

## Slide 5 — Supporting Paper 1: χRVFormal (Formal Verification)

**SAY:**
"The first paper is my formal-verification paper. Formal verification means *mathematically proving* the processor matches the spec for *every* possible input — not just testing some inputs.

Their method: they built a reference model — the 'correct answer' — but in a high-level language called Chisel, in about 4,600 lines, versus the existing tool's 105,000 lines of Verilog. The clever part is the *synchronisation* — their reference does one instruction at a time, but a real processor runs many at once, out of order. StateCheck and ActionCheck are two strategies to line those up so a model checker can prove they always agree.

Results: they found real bugs — 2 in one core, 5 in another — confirmed by the original designers, and they caught all 15 injected bugs, where the old tool caught only 2 of the 7 real ones. It even scaled to BOOM, an out-of-order core."

**KEYWORDS:**
- **Formal verification:** proving correctness for all inputs mathematically, not by testing samples.
- **Reference model:** a trusted description of what each instruction *should* do.
- **Model checker:** the mathematical engine that proves the design matches the reference.
- **Chisel:** a modern high-level hardware design language (like Bluespec, which we use).
- **Out-of-order / BOOM:** a processor that runs instructions in a different order internally for speed, but commits results in program order.
- **StateCheck / ActionCheck:** StateCheck compares the *whole* architectural state at each instruction commit (good for simple cores); ActionCheck compares just *each instruction's effect* (lighter, scales to out-of-order cores).

---

## Slide 6 — Supporting Paper 2: Vector Accelerator (Golden-Model)

**SAY:**
"The second paper is the industry-practice paper, and it's the exact *opposite* of my base paper — it's built entirely *around* a golden model. They verified a real RISC-V vector accelerator that actually taped out into silicon.

The method: run every vector instruction twice — once on the real hardware, once on Spike, the trusted simulator — and compare with a UVM scoreboard. They add SystemVerilog assertions on the interfaces for visibility, use Google's RISCV-DV to auto-generate random instructions, and run it all continuously for about a year.

Results: 3,005 errors, nearly 96% functional coverage, and the chip shipped. About 70% of the bugs were in memory-type instructions — the hardest part of vector verification."

**KEYWORDS:**
- **Vector accelerator:** a specialist unit that does many data elements per instruction in parallel (SIMD), sitting next to the main scalar core.
- **UVM:** an industry-standard framework for building testbenches (the scaffolding that feeds inputs and checks outputs).
- **Scoreboard:** the UVM component that compares hardware output vs the golden model.
- **SystemVerilog Assertion (SVA):** a rule embedded in the design that fires the instant it's violated, pinpointing where a bug is.
- **RISCV-DV:** Google's tool that auto-generates random-but-legal RISC-V instruction sequences.
- **Functional coverage:** did the tests exercise all the intended functional scenarios (vs code coverage: did they hit every line of RTL).

*(If asked "3,005 vs the 7 from paper 1 — is this better?": "No — different counting. These are internal error reports over a year in their own design; paper 1's 7 were previously-unknown bugs in other people's cores, confirmed by the designers. Not comparable.")*

---

## Slide 7 — Supporting Paper 3: INSTILLER (Fuzzing)

**SAY:**
"The third paper is fuzzing — and it's from the top EDA journal. Fuzzing means bombarding the processor with large volumes of automatically-generated random instruction sequences, running each on both a reference simulator and the real RTL, and flagging any disagreement as a candidate bug. It's *coverage-guided*, meaning it's a feedback loop — it measures what it has tested and steers new tests toward what it hasn't.

Their main contribution is an ant-colony algorithm called VACO that keeps the tests *short*. Fuzzing tests tend to bloat over time; VACO trims them while keeping coverage. They also add realistic interrupts and exceptions, which older tools ignored.

Results versus the previous best tool: 29% more coverage with tests that are 79% shorter. And their ablation shows that turning VACO off makes tests 417% longer — so that algorithm is really what's doing the work."

**KEYWORDS:**
- **Fuzzing:** testing by throwing large amounts of auto-generated semi-random input at a design to find bugs.
- **Coverage-guided:** a feedback loop that uses coverage measurements to steer what gets tested next.
- **Differential testing:** run the same input on the design and on a reference simulator, compare — a disagreement ("mismatch") flags a candidate bug.
- **Seed / mutation:** a seed is a previous interesting test; mutation is changing it to make a new test.
- **VACO (ant colony optimisation):** an algorithm inspired by how ants find short paths, used here to keep tests short but effective.
- **Ablation:** turning off one part of the system to measure how much it contributed.

*(If asked: "mismatches are *candidate* bugs, not designer-confirmed like paper 1's.")*

---

## Slide 8 — Supporting Paper 4: PFV (Polynomial Formal Verification)

**SAY:**
"The fourth paper is the most rigorous, and deliberately the most limited. It's also formal verification, but with an extra twist: it proves not only that the design is correct, but a mathematical *bound on how long the verification itself takes* — polynomial, not exponential. That predictability is the reason industry hesitates to use formal methods, so it's a real contribution.

It uses Binary Decision Diagrams — a canonical way of representing logic, so that checking two circuits are equal becomes a simple pointer comparison. They isolate one instruction at a time, feed symbolic 'any-value' inputs, and compare against a reference built from the maths.

The catch — and this is the point of including it — is that it only works on a tiny non-pipelined integer core. BDDs blow up on multiply, divide, and floating point, so it can't handle a real core like ours. It's here to show the *ceiling* of formal methods."

**KEYWORDS:**
- **Polynomial vs exponential time:** polynomial (like n²) grows manageably; exponential (2ⁿ) explodes — the whole point is proving it stays polynomial.
- **BDD (Binary Decision Diagram):** a canonical graph of a logic function; two equal functions produce identical graphs, so comparison is instant.
- **Canonical:** a unique standard form — same function always gives the same representation.
- **Symbolic simulation:** running the circuit with "any value" inputs instead of concrete numbers, so you cover all inputs at once.

*(If asked why it's in the set: "It's the scalability counterpoint to paper 1 — that one scales but is bounded to 40 cycles; this one is complete but only on a toy core. And they actually disagree in print about whether BDDs can handle pipelines. That trade-off is the core of my comparison.")*

---

## Slide 9 — Base Paper: Overview

**SAY:**
"Now the base paper — PATARA, from 2026. This is the one my own project work is built on. Its goal is to verify a custom RISC-V core *and* an attached co-processor *without* a golden reference model at all — and to show that conventional compliance testing isn't enough.

Its main contributions are REVERSI-based self-testing, extra test generation for pipeline hazards and cache misses, and a twin-based method for the co-processor. They evaluated it on their own 6-stage RV32IM core with a vector co-processor, benchmarked against the official compliance suite."

**KEYWORDS:**
- **Self-testing:** tests that check their own correctness, with no external reference.
- **Co-processor:** a separate specialist unit attached to the main core.
- **RV32IM:** 32-bit RISC-V with integer (I) and multiply/divide (M) — no floating point.

---

## Slide 10 — The Core Idea: REVERSI

**SAY:**
"The core idea is called REVERSI, and it's genuinely elegant. Normal verification has to know the correct answer, which means computing it somewhere else — a golden reference model that's slow and can have its own bugs.

REVERSI sidesteps that completely. You apply an operation, then apply its inverse — and you must land back where you started. Add 7, subtract 7 — if you don't get the original value back, the hardware is broken. You never needed to know the *right* answer, only that going forward and back cancels out. So the test checks itself."

**KEYWORDS:**
- **REVERSI:** apply an operation then its inverse; if you don't return to the start, there's a bug. (From earlier work by Shazli & Tehranipoor — PATARA applies it to RISC-V.)
- **Invertible operation:** one you can undo (add ↔ subtract). Non-invertible ones need the twin method later.

---

## Slide 11 — Code for an ADD Test-Instruction

**SAY:**
"Here's it concretely, in three lines. First the modification — the instruction under test, ADD. Then the restoring operation — its inverse, SUB. Then the comparison — check we got the original value back. If the branch doesn't take, the test failed.

One important rule: the instruction under test appears *only* in the first line. If you used ADD to both do and undo, a fault in the adder would cancel itself out and the test would pass on broken hardware. Restoring with SUB routes through different logic, so nothing cancels."

**KEYWORDS:**
- **Modification / restoring / comparison:** the three steps of a REVERSI test.
- **focus / target / random registers:** focus is the value being round-tripped, target is scratch, random is fresh random data for variety.

---

## Slide 12 — The PATARA Tool Flow

**SAY:**
"PATARA is the tool that automates this. It's a three-stage Python pipeline. Instruction Selection picks which instructions to test from an XML description. Sequence Generation arranges them into orders that deliberately create pipeline hazards. Code Generation emits the ready-to-run self-checking assembly. The output is test programs that need no external reference — each one carries its own pass/fail check.

The key design point is that the instruction set is described in XML — data, not code — so the tool itself never changes when you add a new instruction."

**KEYWORDS:**
- **XML instruction description:** a small file listing each instruction's forward and reverse operation, so the tool knows how to test and undo it.
- **Pipeline hazard:** when one instruction needs a result another hasn't finished producing yet.

---

## Slide 13 (image) — XML: ADD and reverse SUB

**SAY:**
"This is what one instruction definition looks like — the ADD instruction, with its reverse defined as SUB. That's all it takes to teach the tool a new instruction. For our own custom instruction ADDP1, we'd add one entry like this, with the reverse being SUB then subtract-one."

---

## Slide 14 (13 in deck) — What They Verified: A Real Pipelined Core

**SAY:**
"This is the design they verified — a real 6-stage pipeline. Instructions overlap, several in flight at once. The execute stage has three units — a single-cycle ALU, and multi-cycle multiply and divide — so instructions finish at different times. To avoid stalling, results are *forwarded* back to earlier stages.

That forwarding is where the hardest bugs live. They're not in single instructions — they're in *interactions*, like forwarding a result while a divide is still running, or a cache miss during a multiply. You only trigger those with a specific sequence at a specific timing — which a generic compliance suite can't systematically produce. This matters to us because our Shakti core is also pipelined with forwarding."

**KEYWORDS:**
- **Pipeline / stages (IF, ID, EX, MEM, WB):** the assembly line a processor breaks each instruction into.
- **Forwarding (bypassing):** routing a just-computed result directly to a waiting instruction instead of making it wait for write-back.
- **Hazard / stall:** a timing conflict; stalling is pausing to resolve it.

---

## Slide 15 (14) — Four Extensions

**SAY:**
"Plain REVERSI has blind spots, so PATARA adds extensions. Hazard sequence generation systematically creates instruction combinations to hit forwarding and stall interactions — that's the big one, taking coverage from 81 to 97%. Operand swapping reaches the second operand's forwarding path, which basic tests never touch. Cache-miss generation deliberately forces misses. And the twin method handles operations REVERSI can't reverse — I'll come to that next. Together they turn REVERSI from a single-instruction check into a systematic pipeline-interaction test."

**KEYWORDS:**
- **Operand swapping:** swapping which input carries the dependency, so the *second* operand's forwarding logic gets tested too.
- **Cache miss:** when required data isn't in the fast cache and must be fetched from slower memory.

---

## Slide 16 (15) — The Twin Method

**SAY:**
"REVERSI only works if you can undo the operation. But some operations throw information away — absolute value, or a dot product — you can't recover the inputs from the output, so you can't reverse them.

The solution is the twin method: run the operation on the hardware you're testing, *and* run the same operation as software on the already-verified core, then compare. The verified core becomes the reference. The order matters — you verify the basic core first with REVERSI, then use it to check everything else. No external simulator needed.

This is the part directly relevant to us: our custom instruction PDOT8 is a dot product, so it's non-invertible — and we verified it exactly this way, with zero mismatches over 16,384 outputs."

**KEYWORDS:**
- **Non-invertible operation:** one you can't undo because it discards information (dot product, absolute value).
- **Twin method:** compute the operation two ways — hardware and trusted software — and compare.
- **PDOT8:** our custom 8-lane dot-product instruction — non-invertible, so it uses this method.

---

## Slide 17 (16) — The Results

**SAY:**
"Here's the headline. The same core was tested two ways. The official compliance suite ran on it and found zero bugs — it 'passed' — but left condition coverage at only 79%. PATARA reached 100% and found real bugs in that same passing design — all timing interactions like forwarding during a divide or a cache miss during a multiply.

On the co-processor side, the twin method also reached 100% coverage — with one interesting finding: ten times more random tests gave zero improvement. They had to make the tests *smarter*, not just run more. The takeaway is the spine of my whole seminar: passing the compliance suite is not the same as being correct — and that's exactly how our team currently justifies our core."

**KEYWORDS:**
- **Condition coverage:** did every logical condition take both true and false values — a strict coverage metric (the one where the gap showed up).

---

## Slide 18 (17) — Application & Relevance to the Project

**SAY:**
"Three concrete ways this applies to us. One — custom instruction verification: our instructions are invented, so no golden reference exists for them, which is exactly the problem PATARA solves. Two — pipeline hazard bugs: our Shakti core is pipelined with forwarding, and we modified shared decode and ALU logic that every instruction flows through, so the timing-interaction bugs PATARA targets are a real risk for us. Three — it gives us a stronger baseline than 'compliance passed,' which is our current justification."

**KEYWORDS:**
- **Custom ISA extension:** an instruction we added that isn't in the standard RISC-V spec.

---

## Slide 19 (18) — Advantages & Limitations

**SAY:**
"To be balanced. Advantages: no golden reference model; it targets our specific pipeline; it's proven effective at 100% coverage with real bugs found; it's extensible to custom instructions; and it's efficient — its simplest configuration beat the compliance suite with about 127 times fewer instructions.

Limitations, and I'll be honest about these: it's RV32IM only — no floating point, because rounding breaks the invertibility REVERSI relies on. Crucially, 100% coverage doesn't mean correct — REVERSI proves self-consistency, not conformance to the actual spec, which is exactly why I included the formal-verification papers. It excludes CSRs and interrupts. The twin method can be fooled by a buggy software twin. And the bug evidence is thin — one core, 'several' bugs, self-reported."

**KEYWORDS:**
- **Self-consistency vs spec conformance:** REVERSI proves SUB undoes ADD (internal consistency); it does *not* prove ADD matches the RISC-V manual (conformance). Formal methods prove the latter.
- **CSR (Control/Status Register):** special registers for system control — outside this paper's scope.

---

## Slide 20 (19) — Comparison of the Papers

**SAY:**
"Pulling it together. Each approach trades something. χRVFormal proves spec conformance and found confirmed bugs, but its proof is bounded to 40 cycles. The vector accelerator paper works at industrial scale and shipped silicon, but its code coverage was low. INSTILLER's fuzzing finds corner cases with short tests, but it's incomplete and half its cores aren't even RISC-V. PFV gives complete proofs with a time bound, but only on a toy core. And my base paper needs no golden model and reaches 100% coverage and works post-silicon — but only covers integer instructions, no CSRs or interrupts. The real message is: no single method wins — verification is about trade-offs."

*(This is your synthesis slide — deliver it slowly, it's where you sound like you understood the whole field.)*

---

## Slide 21 (20) — Conclusion

**SAY:**
"To conclude. My base paper verifies a custom RISC-V core with self-checking tests and no golden reference, plus a twin method for non-invertible operations. Its key finding is that passing the compliance suite isn't the same as being correct — better tests found real bugs in a design that had passed. The wider set shows no single method wins — self-testing, golden-model, fuzzing, and formal methods each trade coverage, scalability, or completeness. And it matters to us directly: we currently justify our core with 'compliance passed,' and this work gives us a stronger, systematic path — one we've already started using with the twin method on our own custom instruction."

---

## Slide 22 (21) — References

**SAY:**
"These are my five papers plus the RISC-V manual and the original REVERSI paper. All five are from 2023 to 2026, all indexed journals, none are surveys."

*(Don't read them out — just gesture. Only pause here if a panel wants a specific citation.)*

---

## Slide 23 (22) — Thank You

**SAY:**
"Thank you — I'm happy to take any questions."

---

# TOP LIKELY QUESTIONS (have these ready)

1. **"Why is PATARA your base paper and not the stronger formal paper?"**
   → "A base paper is the one my project is built on — I reproduced its twin method on my own instruction. And formal verification proves conformance to the *spec*, but my custom instructions aren't in the spec, so it can't verify the thing my project actually needs. PATARA's the only one whose method fits custom instructions."

2. **"Does 100% coverage mean the processor is correct?"**
   → "No, and the authors say so. It means every line and condition was exercised. REVERSI checks self-consistency, not conformance to the spec — which is why I also have the formal papers. Coverage is necessary, not sufficient."

3. **"How many bugs did PATARA find exactly?"**
   → "The paper only says 'several' — it's self-reported in their own core. So the stronger, measured result is the coverage: 79% to 100%."

4. **"Could any of your other papers verify your custom instruction?"**
   → "Not off the shelf — they all need a reference for the standard ISA, and my instruction isn't in any standard. That's exactly why the base paper's reference-free approach fits."

5. **"What did χRVFormal actually invent?"**
   → "Two things: a compact Chisel reference model, and — more importantly — a synchronisation mechanism that lets a single-cycle reference be compared against a pipelined or out-of-order core."

6. **"You said the reference is single-cycle but they verified out-of-order BOOM — how?"**
   → "Out-of-order execution but *in-order commit*. The core updates architectural state one instruction at a time in program order, via the reorder buffer — so the committed sequence matches a single-cycle reference. They compare only at commit."
