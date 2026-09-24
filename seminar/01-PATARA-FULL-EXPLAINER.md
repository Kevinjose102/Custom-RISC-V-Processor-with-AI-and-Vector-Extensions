# PATARA — Full Explainer (Base Paper)

**Seminar topic:** Verification Methodologies for RISC-V Processors
**Student:** Kevin Jose — Team 2 (Custom RISC-V Processor with AI and Vector Extensions)

---

## 0. Citation and metadata

> Gesper, S., Stuckmann, F., Wöbbekind, L. and Payá-Vayá, G. (2026) 'A Self-Testing
> Framework for Verification and Validation of a RISC-V-Based System with a Co-processor',
> *International Journal of Parallel Programming*, 54(15).
> doi: 10.1007/s10766-026-00824-8

| Field | Value |
|---|---|
| Publisher | Springer Nature |
| Journal | International Journal of Parallel Programming, Vol. 54, Art. 15 |
| Indexing | SCIE / Scopus |
| Received / Accepted | 26 April 2024 / 4 April 2026 |
| Access | Open Access (CC BY 4.0) |
| Institution | Chip Design for Embedded Computing, TU Braunschweig, Germany |
| Funding | German BMBF, project 16ME0379 (ZuSe-KI-AVF) |
| Length | 29 pages |
| Tool | Open source — github.com/tubs-eis/PATARA |

**One-sentence summary:** The official RISC-V compliance test suite passed their processor
with zero bugs while leaving 21% of logical conditions untested; PATARA auto-generates
self-checking test programs that reach 100% condition coverage and found real bugs the
official suite had missed.

---

# PART 1 — THE PROBLEM

## 1.1 What compliance testing actually proves

The standard workflow: compile a test (`add.S`), run it on the simulator, check the `tohost`
write for a value of `1`, conclude the processor works.

That proves: *for the specific instruction sequences someone wrote by hand, the processor
produced correct answers.*

It does **not** prove the processor is correct. The gap between those two claims is the
entire subject of this paper.

## 1.2 Why handwritten test suites have a structural blind spot

The official RISC-V compliance suite is written once, by the RISC-V Foundation, for
everyone. That is simultaneously its strength and its fatal weakness: **it cannot know
anything about your specific implementation.**

Things it does not know about any given core:

- How many pipeline stages
- Whether the multiplier is single-cycle or split across stages
- Whether the divider is multi-cycle with variable latency
- Cache line size and cache organisation
- How forwarding and stall logic are structured
- Branch prediction strategy
- Whether a co-processor is attached

Every one of these choices produces behaviours that exist only in *that* chip. A generic
suite cannot systematically target them, because it was written before the chip existed.

## 1.3 The concrete failure that motivates the paper

The authors designed a 6-stage RV32IM processor in VHDL (called EIS-V). They ran the
official compliance suite.

> **Zero bugs found. The design passed functional verification.**

They then measured code coverage. Statement coverage was 99.40% — excellent. But
**condition coverage was 79.12%**: over one fifth of logical conditions in the design were
never fully exercised.

When they built better tests targeting those regions, they found **real bugs** in the same
design the compliance suite had declared correct.

## 1.4 The bugs found — study these, they are instructive

All four were in the **EIS-V core's own VHDL**, and all four are in *control* logic
(forwarding and stalling), not in arithmetic. The ALU computed correctly; the pipeline
mismanaged when results were available.

**Bug 1 — Forwarding during unfinished multi-cycle division.**
Location: data forwarding unit. The unit failed to correctly update the *source* of the
forwarded operand when a multi-cycle division had not yet completed. Because their divider
has variable latency, exposing this requires a division in flight *and* a dependent
instruction *and* the correct timing relationship. The paper notes it "requires several test
cases to cover all hazard and forwarding combinations."

**Bug 2 — Cache miss during multi-cycle multiply.**
Location: multiplication unit, split across EX and MEM1 stages. A data-cache miss (e.g.
from a Load) occurring *while* a multiply is in progress was mishandled by the stall logic.
This is a three-way interaction: multiplier state × cache state × stall logic.

**Bug 3 — Load → JALR forwarding.**
Forwarding a loaded value into the source register of a jump-and-link-return. An entirely
ordinary operation that the handwritten suite simply never wrote.

**Bug 4 (category) — Cache miss + stall combinations.**
"In general, several bugs related to a combination of cache misses and stall conditions were
found and fixed."

### The pattern

None of these is "ADD computes the wrong sum." **Every one is an interaction between two or
three mechanisms.** Handwritten tests check features one at a time, because that is how
humans think about testing. Bugs live in the combinations.

## 1.5 The detection method — two stages

This is worth understanding precisely, because it is commonly misunderstood.

**Stage 1 — Code coverage analysis identifies where to look.**
The compliance suite was run under Questa Sim with coverage instrumentation. It passed — no
failures. But the coverage report showed which VHDL lines, branches and conditions were
never exercised, clustered around hazard and stall logic. The paper's own language reflects
this: *"Another **not covered** hazard situation is related to the multiplication unit."*

**Stage 2 — PATARA generates tests reaching those regions; the REVERSI self-check detects
the bug.** When a test executes an instruction whose result is forwarded incorrectly, the
REVERSI round-trip breaks: modify a value, restore it, and it does not match. The
comparison fails.

> **Coverage analysis is the guide; self-checking is the detector.**
> Coverage never finds a bug by itself — it only tells you where you have not looked.

### Honest caveat on the bug reporting

The bug discussion is **one paragraph** (Section 5.2, p.22). The paper does not provide:
per-bug test sequences, failure traces, a precise count ("several"), or any external
confirmation. The bugs were found in the authors' own core during their own development.

Contrast: χRVFormal found 7 bugs in *third-party* cores (riscv-mini, NutShell), filed them
as GitHub issues, and had them **confirmed by the original designers**. That is stronger
evidence.

**Presentation guidance:** describe PATARA's bug finding as *coverage-guided,
self-check-detected, self-reported.* Lead with the **coverage** result, which is measured,
tabulated across six metrics and reproducible; treat the bugs as supporting evidence.

## 1.6 The second problem — golden reference models

Most automated generators (including Google's RISCV-DV) generate random instruction streams
but then need a **golden reference model** — usually an ISS such as Spike — to check answers.

Three problems:

1. **Slow.** Everything runs twice; reference generation becomes the bottleneck.
2. **The reference model has its own bugs.** The paper cites prior work (ref [20])
   demonstrating exactly this. You then have two implementations that disagree and no way
   to know which is wrong.
3. **Useless post-silicon.** On a physical chip you cannot easily observe internal signals
   or stream results to a host. Validation must run *on the chip itself*.

## 1.7 So PATARA must solve two things

1. Generate tests targeting *this specific implementation's* hazards and corner cases
2. Check correctness **without any external reference model**

---

# PART 2 — REVERSI, THE CORE MECHANISM

## 2.1 The insight

You do not need to know the right answer. You only need the operation to be **reversible**.

Add 7 to a number, subtract 7, and if you do not get the original back, something is broken —
without ever knowing what the "correct" intermediate value was. The round trip proves itself.

## 2.2 The three-stage structure

```
1. MODIFICATION   — apply the instruction under test
2. RESTORING      — apply its inverse
3. COMPARISON     — did we get back the original?
```

```asm
    add   target, focus, random     ; modification: target = focus + random
    sub   target, target, random    ; restoring:    target = target - random
    bne   target, focus, fail       ; comparison
```

Three registers with fixed roles:

- **focus** — the value being round-tripped; what you are protecting
- **random** — arbitrary data, freshly randomised; provides input variety
- **target** — scratch space for the result

The register file is initialised with random values at program start, so each run exercises
different data patterns.

## 2.3 Rule 1 — the test instruction appears ONLY in the modification

> *"The test instruction should only be used in the modification operation so that a
> systematic error in the instruction does not mask an error that occurs inside the
> modification and restoring operation."*

**Intuition:** do not use the thing under test to check itself. It is proofreading your own
essay — you make the same mistake twice and read past it.

**Concretely:** if you tested `ADD` by adding, then adding the negated operand back, both
operations flow through the same adder. A systematic fault applies in both directions and
**cancels itself out**. You get the original value back, the test passes, and broken hardware
ships. Restoring with `SUB` routes the reverse through different control logic, so the fault
has nothing to cancel against.

**This is the most likely Q&A question on the method. Know why, not just what.**

## 2.4 Rule 2 — information loss must be handled

Some instructions destroy information and cannot be simply inverted.

The paper's example is **shift left**: `SLL x, 4` pushes the top four bits off the end.
Shifting right by 4 does not restore them. A naive round trip would fail on *correct*
hardware.

Their solution: *"control code is added to the test instruction in the modification and
restoring operations to enable the full restorability of the focus register."* Extra
instructions preserve the bits about to be lost so restoration can rebuild the original.

**Cost:** every instruction in the ISA needs a human to design its modification/restoring
pair, and for lossy instructions this is non-trivial. It is also why floating-point is hard
for REVERSI — rounding destroys information in a way that is not cleanly recoverable, part
of why the paper covers RV32I**M** only, with no F or D extensions.

## 2.5 Interleaving — and why simple tests are weak

The three-instruction test above exercises exactly **one** forwarding path (EX → EX), because
the producer and consumer are adjacent.

A 6-stage pipeline has forwarding paths from EX, MEM1, MEM2 and WB. To exercise MEM2 → EX,
producer and consumer must be **three instructions apart**. Simple tests never create that
distance.

**Interleaving** chains modifications so each test's output feeds the next:

```asm
    add   t, focus, r1        ; test 1 modification
    sub   t, t, r2            ; test 2 modification — consumes test 1's result
    xor   t, t, r3            ; test 3 modification
    sll   t, t, r4            ; test 4 modification
    ...
    srl   t, t, r4            ; test 4 restore
    xor   t, t, r3            ; test 3 restore
    add   t, t, r2            ; test 2 restore
    sub   t, t, r1            ; test 1 restore
    bne   t, focus, fail      ; one comparison for the whole stack
```

Restorations happen in **reverse order** — stack/LIFO discipline. Multiple stacks can be
nested for arbitrarily long tests.

Two benefits: varied producer-consumer distances (different forwarding paths), and a single
comparison validating a long chain.

## 2.6 The honest result about interleaving

| Configuration | Condition coverage |
|---|---|
| All instruction combinations | 80.21% |
| + operand switching | 81.31% |
| **+ interleaving** | **81.31%** |

**Interleaving contributed exactly 0.00 percentage points to condition coverage** — and FSM
transition coverage actually *dropped* slightly (94.28% → 93.18%).

Why: interleaving is *random*. It creates complexity but does not systematically enumerate
hazard scenarios. **Randomness gives variety, not coverage.** This is precisely why the
explicit hazard-permutation generator was needed.

---

# PART 2b — THE PATARA TOOL

## 2b.1 REVERSI vs PATARA — the distinction

- **REVERSI** is an *idea* — modify, restore, compare. From earlier work by Shazli &
  Tehranipoor (ref [31]). A principle, not software.
- **PATARA** is the *tool* implementing and automating that idea. Open source, built by this
  group in earlier work. **This paper adds RISC-V support plus four extensions.**

## 2b.2 What the tool does, end to end

```
        XML description files
        (processor + instruction set)
                    ↓
    ┌───────────────────────────────────┐
    │  [1]  Instruction Selection       │
    │       which instructions to test  │
    ├───────────────────────────────────┤
    │  [2]  Sequence Generation         │
    │       ordering, per test mode     │
    ├───────────────────────────────────┤
    │  [3]  Code Generation             │
    │       modification + restoring    │
    │       + comparison                │
    └───────────────────────────────────┘
                    ↓
      Assembly (.S) files + randomly
      initialised register file
```

**Input:** XML describing your processor and instruction set.
**Output:** self-checking RISC-V assembly test programs.

You compile and run those `.S` files exactly as you currently run `add.S` — same toolchain,
same simulator. **PATARA does not touch your RTL and does not run simulation.** It is purely
a test *generator*, sitting before your existing workflow and replacing the handwritten
compliance tests.

## 2b.3 The three stages

**[1] Instruction Selection** — reads XML, picks which instructions to test (whole ISA or
subset).

**[2] Sequence Generation** — arranges tests per *test mode*: single-instruction tests, or
complex procedures (interleaved stacks, hazard sequences, cache-miss provocation).

**[3] Code Generation** — emits assembly: modification, restoring, comparison, plus setup
code filling the register file with random values.

## 2b.4 The XML instruction description

Figure 6 shows the definition for `ADD`:

- **Line 3** — the sequence instruction definition, used when building sequences
- **Line 5** — the **reverse counterpart** (`SUB`), plus variants for immediate forms and
  signed/unsigned data
- **Line 7 onward** — instruction-specific variants generating derivatives (e.g. `ADDI`)

Describing an instruction means stating: what it looks like, what undoes it, what variants
exist.

## 2b.5 Why the plug-in architecture matters

> *"The core of the PATARA framework is independent of the target instruction set
> architecture... The target instruction-set architectures are described with plug-ins."*

The engine — REVERSI logic, interleaving, hazard sequence construction — knows nothing about
RISC-V. Figure 5 lists **VLIW XML** alongside **RISC-V XML** as inputs, because the framework
previously targeted a VLIW architecture. Adding RV32IM meant writing a description file, not
rewriting the tool.

**This is what makes custom instructions tractable — your instruction is another XML entry,
not a code change.**

## 2b.6 Custom ISA extensions

> *"For instruction set extensions (such as custom ISA extensions in RISC-V), the description
> files require the layout of the new instructions and the corresponding sequence to restore
> custom operations. Depending on the complexity of the custom operations, the restoring
> operation includes multiple instructions to restore the original data. For higher-level
> implementations of restore procedures, algorithmic functions can be called in the reversing
> procedure."*

For `ADDP1` you would supply:

1. **Layout** — `funct7=0000000`, `rs2`, `rs1`, `funct3=000`, `rd`, `opcode=0101011`, R-type
2. **Restoring sequence** — `SUB` then `ADDI -1` (two instructions — exactly what the paper
   means by "the restoring operation includes multiple instructions")
3. **Variants** — none for `ADDP1`

PATARA would then treat `ADDP1` as first-class: included in interleaved stacks, pulled into
hazard permutation sequences, operands swapped, exercised alongside every other instruction.

**Compare to current state:** one hand-encoded `.word 0x002081ab` checking 1+1+1=3.

### ⚠ Honest caveat

The paper does **not** show a worked example of adding a custom instruction. Section 4.2 is a
paragraph of prose plus the `ADD` figure. Phrase any claim as *"the framework documents
support for custom ISA extensions, which would apply to our instruction"* — not *"the paper
shows how to verify our instruction."*

---

# PART 3 — THE FOUR EXTENSIONS

Each extension patches a specific blind spot. Scoreboard:

| Configuration | Instructions | Condition cov. |
|---|---|---|
| Instruction combinations only | 6,983 | 80.21% |
| + operand switching | 9,722 | 81.31% |
| + interleaving | 17,294 | 81.31% |
| + hazard sequences | 1,851,852 | 96.70% |
| + multiple sequences + cache tests | 6,732,901 | **100.00%** |

## 3.0 Background: what a forwarding path is

Essential for understanding extensions 3 and 4.

### The problem

```asm
    add  x5, x1, x2      ; produces x5
    sub  x7, x5, x3      ; needs x5
```

```
cycle:     1     2     3     4     5     6     7
add:      IF    ID    EX   MEM1  MEM2   WB
sub:            IF    ID    EX   MEM1  MEM2   WB
                      ↑     ↑
              reads regs   needs x5 here
```

`add` computes x5 at the end of cycle 3 (EX) but writes it to the register file in cycle 6
(WB). `sub` reads registers in cycle 3 — three cycles too early. It gets a stale value.

### Two fixes

- **Stall** — freeze `sub` until x5 is written. Correct, but three wasted cycles.
- **Forward (bypass)** — the value already exists in the EX/MEM1 pipeline register. Route it
  **directly** to the ALU input. No stall, correct answer. That route is a **forwarding path**.

### The hardware

```
                    ┌─────────────────────────┐
   register file ──►│                         │
   EX/MEM1 reg   ──►│  MUX  (operand 1)       │──► ALU input A
   MEM1/MEM2 reg ──►│                         │
   MEM2/WB reg   ──►│                         │
                    └─────────────────────────┘
                              ▲ forward-select

                    ┌─────────────────────────┐
   register file ──►│                         │
   EX/MEM1 reg   ──►│  MUX  (operand 2)       │──► ALU input B
   MEM1/MEM2 reg ──►│                         │
   MEM2/WB reg   ──►│                         │
                    └─────────────────────────┘
                              ▲ forward-select
```

Each mux input is a **forwarding path**. Which is selected depends on distance:

| Distance | Value currently in | Path |
|---|---|---|
| Adjacent | EX/MEM1 register | forward from EX |
| 2 apart | MEM1/MEM2 register | forward from MEM1 |
| 3 apart | MEM2/WB register | forward from MEM2 |
| 4+ apart | register file | none needed |

The control logic selecting the input is the **hazard detection / forwarding unit** — where
two of the paper's four bugs lived.

**Two operands means two independent multiplexers**, each with its own forwarding paths and
its own control logic.

## 3.1 Extension 1 — Variable immediate widths

**Blind spot:** RISC-V immediates are not uniform. Normal I-type carries 12 bits, but shift
instructions use `shamt` — only **5 bits**, because shifting a 32-bit register by more than
31 is meaningless. Naively generating 12-bit immediates for everything produces illegal
encodings or silently truncated values, so interesting shift amounts never get tested.

**Fix:** XML encodes immediate length per instruction; PATARA respects it when generating
random values.

**Significance:** small, but the kind of ISA-specific detail separating a working generator
from a broken one.

## 3.2 Extension 2 — Branch range limits on interleaving

**Blind spot:** conditional branches reach only **±4 KiB**. Under REVERSI, a branch sits in
the modification operation and its target in the restoring operation. Interleaving inserts
other tests *between* them — stack it deep enough and the target drifts beyond 4 KiB. The
branch physically cannot reach its target; the test will not assemble.

**Fix:** cap interleaving depth for branch-containing tests.

**Significance:** illustrates that automated generation is not "generate random stuff" — the
generator must respect real architectural constraints.

## 3.3 Extension 3 — Operand swapping

**The blind spot (subtle and important).**

In a standard REVERSI test:

```asm
    add   target, focus, random
                    ↑       ↑
              operand 1  operand 2
```

`focus` is the value carrying the dependency chain — the freshly-computed result needing
forwarding. It is **always operand 1**. `random` is arbitrary data from the register file,
**always operand 2**.

Therefore **operand 2's multiplexer permanently selects "register file."** Its forwarding
inputs are never chosen, its control logic never enters those states. The hardware stays dark
**no matter how many tests you run** — the bias is structural, not statistical.

**Fix:** randomly swap which operand carries `focus` vs `random`, with configurable
probability.

**Result:**

| Metric | Before | After |
|---|---|---|
| Condition coverage | 80.21% | 81.31% |
| **FSM transitions** | **88.63%** | **94.28%** |

Only +1.1 pp condition, but **+5.65 pp FSM transitions** — because forwarding multiplexers
are state-machine-controlled and half their transitions were unreachable.

**Transferable lesson:** a systematic bias in how tests are *constructed* creates a systematic
hole in coverage. More testing does not fix it; only changing test structure does.

## 3.4 Extension 4 — Pipeline hazard sequence generation (the big one)

**81.31% → 96.70%.** This is where the coverage comes from.

**Blind spot 1:** interleaving creates dependencies *randomly*. You might place producer and
consumer three apart, hitting MEM2 → EX. Or you might not. Table 5 proves random variety is
not systematic coverage — interleaving delivered 0.00 pp.

**Blind spot 2 (the sharpest insight in the paper):** it is not enough to *use* each
forwarding path. You must cover the **transitions between them.** The EX-stage forward-select
is effectively a state machine. Figure 9 shows a transition the compliance suite never
triggers:

```
cycle n:      forward select = WB
cycle n+1:    forward select = MEM2      ← never occurs
```

Each individual selection can be well covered while specific *sequences* of selections never
occur. That is why FSM transition coverage lagged FSM state coverage.

**How the sequences are generated:**

1. **Enumerate all permutations of instruction types** in the ISA, covering every data
   dependency combination — systematically, not randomly
2. **Sequence length derived from pipeline depth** — for 6 stages, **4 consecutive
   instructions** are needed for full coverage. The generator reads pipeline depth from the
   processor description. Change to 5 stages and it regenerates correctly; a handwritten
   suite would need manual rewriting
3. **Instructions within a sequence randomly selected by instruction type** — structure
   systematic, contents random
4. **Random filler instructions** inserted that do not disturb the data dependency; they
   shift timing relationships and reach additional forward-select transitions (the Figure 9
   case)
5. Builds on the interleaving mechanism — data forwards from one test instruction to the next

**Cost:** 17,294 → 1,851,852 instructions, roughly **107× more tests** for +15.4 pp condition
coverage.

## 3.5 Extension 5 — Cache miss generation

**Blind spot:** compliance tests are small programs; small programs fit in cache. Cache-miss
handling — and critically the *interaction* between cache stalls and pipeline hazards — is
essentially never exercised.

The paper is explicit: *"since instruction cache misses only rarely occur on small test
cases, only a few tests, like the long branch test case, generate cache misses. As the branch
test focuses on the branch instructions, other hazards in combination with those instruction
cache misses are not covered."*

Even when the suite accidentally produces a cache miss, it happens during a test focused on
something else, so the miss never coincides with hazards worth testing alongside it.

**Fix — two mechanisms:**

**Data cache:** address generation modified to deliberately produce cache-line misses, based
on the cache line width declared in the processor description.

**Instruction cache:** a constructed pattern —
```asm
    jump  destination
    filler                ; repeated to fill a cache line
    filler
    ...
destination:              ; guaranteed to miss
```

**Result:** the final **96.70% → 100%**, plus 100% expression coverage (stuck at 95.58%
through every earlier configuration).

**And it found bugs** — two of the four documented bug categories are cache-related.

## 3.6 The pattern

```
REVERSI alone
   └─ blind spot: focus always in operand 1
        └─ OPERAND SWAPPING
             └─ blind spot: dependencies random, not systematic
                  └─ HAZARD SEQUENCE GENERATION
                       └─ blind spot: small programs never miss cache
                            └─ CACHE MISS GENERATION
                                 └─ 100%
```

Each extension exists because the previous configuration left something structurally
unreachable.

---

# PART 4 — TWIN-BASED CO-PROCESSOR VERIFICATION

## 4.1 Why REVERSI collapses here

Count the invertible operations in V2PRO's ISA (Table 3):

| Instruction | Invertible? |
|---|---|
| `ADD`, `SUB` | Yes |
| `MULL` / `MULH` | No — only low or high half retained |
| `MIN`, `MAX` | No — `MIN(3,7)=3` says nothing about the 7 |
| **`ABS`** | **No — sign destroyed** |
| `MV_PL`/`MV_MI`/`MV_ZE`/`MV_NZ` | No — a no-op branch leaves no trace |
| `AND`, `OR`, `NAND`, `NOR` | No — lossy by construction |
| `MACL` / `MACH` | No — accumulator state folded in |

Only a handful survive, and no amount of control code rescues the rest — the information is
genuinely gone.

**Second problem:** the co-processor is a *different machine* with its own register files,
local memories and addressing model. RISC-V assembly self-tests cannot reach inside it.

## 4.2 The idea

```
        random vector instruction sequence + input data
                (generated on the RISC-V)
                    ↓                    ↓
    ┌───────────────────────┐   ┌──────────────────────────┐
    │  TWIN 1               │   │  TWIN 2                  │
    │  V2PRO hardware       │   │  C++ software emulation  │
    │  (thing under test)   │   │  on the verified RISC-V  │
    └───────────────────────┘   └──────────────────────────┘
                    ↓                    ↓
              results DMA'd        reference arrays
              to external mem            ↓
                    └──────► COMPARE ◄───┘
```

**The already-verified RISC-V core becomes the golden model.**

Ordering matters: first verify the RISC-V with REVERSI, *then* use that verified core to
check the co-processor. Trust is bootstrapped — earned on the simple machine, spent on the
complex one.

Benefit: no external simulator, no host communication, no shipped reference model.
Everything runs on-chip — viable post-silicon.

## 4.3 What V2PRO is

Vertical vector co-processor: elements processed *sequentially* within a lane, many lanes in
parallel.

- 24-bit datapath, 48-bit accumulator
- Hierarchy: clusters → vector units → 2 processing lanes + 1 load/store lane + local memory
- FPGA config: 8 clusters × 8 units, 400 MHz (RISC-V and AXI at 200 MHz)
- **3-D addressing:** `Address = x·α + y·β + z·γ + δ`
- **Chaining:** neighbouring lanes pass data directly through FIFOs, bypassing memory
- **Instruction FIFO** decouples vector execution from RISC-V issue
- Controlled via **memory-mapped addresses** — the RISC-V issues vector instructions using
  ordinary load/store instructions

**Critical design decision:** the vector lanes deliberately contain **no hazard-resolution
logic**, stripped out to reach 400 MHz. The hardware will execute a sequence containing a
read-after-write hazard and produce wrong results *by design*. Software must guarantee it
never issues one.

## 4.4 Mechanics

Random parameters: operations, operands and addressing parameters (α, β, γ, δ), vector
lengths, lane assignments.

The software twin is **C++ with bit-exact masks** — shifts, multiply precision and
accumulator width modelled at bit level. Chaining emulated by sequentially interleaving
element calculations.

Results return via DMA: vector lane register files and local memories copied to a reserved
external memory region; DCMA flushes; the RISC-V reads and compares. On mismatch the
framework reports instruction sequence, input/output data and hardware register states.

For coverage evaluation, generation was done offline with a fixed seed for repeatability —
but the same generator runs **as a single RISC-V program on-chip** for post-silicon
validation.

## 4.5 The constraints — where the real engineering is

**1. RAW hazard avoidance.** Because the hardware has no hazard logic, the generator checks
no instruction reads a vector element another is still writing, within a window equal to
pipeline depth. *The test generator must model the hardware's timing to avoid producing tests
the hardware was never designed to handle.*

**2. Chain deadlock avoidance.** A lane awaiting chained data stalls. If *every* lane waits,
nothing issues and the co-processor deadlocks. A constraint check prevents this.

**3. Chain-finishing instructions.** If a sequence ends with open chains, the test never
completes. The generator appends closing instructions.

**4. FIFO filling.** To test the instruction FIFO's full condition, a long-running instruction
is **prepended**, giving the RISC-V time to push enough subsequent instructions to fill it.

**Theme:** generic random generation does not work; the generator must be parameterised by
the implementation — same as the RISC-V half.

## 4.6 Results (Table 7)

| Test sequences | V2PRO statement | V2PRO condition |
|---|---|---|
| Random [1] | 92.11% | 87.27% |
| Random [10] | 99.06% | 98.18% |
| Random [100] | 100.00% | 98.78% |
| Random [1000] | 100.00% | **98.78%** ← plateau |
| Random [1000] + FIFO + modified constraints | 100.00% | **100.00%** |

**Rows 3–4: 10× more testing moved condition coverage by 0.00 pp.**

**Why:** vector lengths were drawn *uniformly* between 1 and maximum, so short vectors are
massively under-represented — yet certain chaining stall conditions only occur with very
short vectors.

**Fix:** a **second constraint set** biasing generation toward short vector lengths, plus
longer sequences for FIFO-full logic. That closed the final 1.22%.

**Transferable lesson:** uniformly random testing has systematic blind spots. When coverage
plateaus, more of the same tests is wasted effort — change the *distribution*, not the
*quantity*. Parallels the operand-swapping insight exactly.

## 4.7 Handwritten tests by comparison (Table 6, 84 test cases, full system)

| Component | Statement | Condition | FSM states/transitions | Toggle |
|---|---|---|---|---|
| RISC-V | 96.04% | 80.85% | 73.33% / **38.83%** | 72.62% |
| V2PRO | 95.03% | 87.87% | 93.75% / 90.09% | 79.83% |
| Lane 0 | **97.43%** | 72.00% | 100% / 100% | 89.41% |
| Lane 1 | **89.93%** | 72.00% | 100% / 100% | 77.57% |
| System | 93.38% | 77.57% | 80.00% / 48.04% | 68.29% |

Two things to notice:

- **38.83% FSM transition coverage** on the RISC-V — under two-fifths of state transitions
  ever taken
- **Lane 0: 97.43% vs Lane 1: 89.93%** — *identical hardware, duplicated, tested unevenly.*
  A concrete illustration of how arbitrary manual test coverage is

## 4.8 Execution time breakdown (per sequence, ≥7 vector instructions)

| Phase | Time |
|---|---|
| Random sequence generation (on RISC-V) | 86.04 ms |
| Data generation (24,576 B, xoroshiro128plus) | 2.68 ms |
| DMA transfers | 0.05 ms |
| **V2PRO execution** | **0.01 ms** |
| RISC-V reference calculation (software twin) | 16.10 ms |

The hardware under test runs for **0.01 ms** — effectively free. 86 ms goes to *generating*
and 16 ms to *checking*. **Verification cost is almost entirely generation and checking, not
execution** — which explains why avoiding an external golden model matters so much.

## 4.9 The limitation the authors admit

> *"As the verification of V2PRO co-processor execution relies on a software twin on the
> RISC-V (implementation of a golden model), failures can be masked by erroneous execution on
> this model as well."*

The twin **is** a golden model — just one running on-chip. If the C++ emulation shares the
hardware's misunderstanding of the spec, both produce the same wrong answer and the
comparison passes.

They also state the twin is **coarse-grained**: functionally correct but ignoring lane
pipeline details and stall conditions. Timing-related control bugs are outside what this
method can catch.

---

# PART 5 — READING THE RESULTS

## 5.1 What each coverage metric measures

```vhdl
if (a = '1' and b = '1') then
    x <= y + z;
end if;
```

| Metric | Asks | Satisfied when |
|---|---|---|
| **Statement** | Did this line execute? | Any run where condition true |
| **Branch** | Both paths taken? | Condition true *and* false |
| **Expression** | All cases of `y + z` evaluated? | Varied operand cases |
| **Condition** | Did `a` and `b` *each* take both values? | All four combinations |
| **FSM** | States reached, transitions taken | Every state, every legal transition |
| **Toggle** | Every signal bit flipped 0↔1? | Every bit of every signal changed |

**Condition coverage is the strict one.** You can reach 100% statement and branch coverage
while `b` never equals 0 — you always enter via `a=1, b=1`. That is exactly the gap this
paper exposes, and why the headline is a condition-coverage number.

## 5.2 Table 4 — compliance suite results

| Test set | Instructions | Statement | Branch | Expression | **Condition** | FSM trans. | Toggle |
|---|---|---|---|---|---|---|---|
| RV32I | 860,973 | 91.17% | 89.46% | 90.00% | **53.84%** | 81.81% | 75.68% |
| RV32M | 28,543 | 91.56% | 87.06% | 90.00% | **57.14%** | 84.09% | 82.79% |
| RV32IM | 889,516 | 99.40% | 99.07% | 98.33% | **79.12%** | 88.63% | 87.87% |

**Read rows 1–2 carefully.** The base integer suite alone reaches **53.84%** condition
coverage; the M-extension suite alone **57.14%**. Only combined do they reach 79.12% — because
integer tests happen to exercise conditions in multiplier logic and vice versa. Coverage
accumulates across suites in ways nobody planned. **That is an accident, not a design.**

**Note the volume:** RV32I uses 860,973 instructions for 53.84% condition coverage. Volume is
not the problem; *structure* is.

## 5.3 Table 5 — the ablation, column by column

| Configuration | Instr. | Statement | Branch | Expression | **Condition** | FSM trans. | Toggle |
|---|---|---|---|---|---|---|---|
| Instruction combinations | 6,983 | 98.61% | 98.52% | 95.58% | 80.21% | 88.63% | 83.37% |
| + operand switching | 9,722 | 98.71% | 98.70% | 95.58% | 81.31% | **94.28%** | 83.53% |
| + interleaving | 17,294 | 98.80% | 98.89% | 95.58% | **81.31%** | 93.18% | 84.39% |
| + hazard sequences | 1,851,852 | 99.50% | 99.81% | 97.05% | **96.70%** | **100%** | 84.98% |
| + multi-seq + cache | 6,732,901 | **100%** | **100%** | **100%** | **100%** | **100%** | 86.60% |

**Four observations, each a slide bullet:**

**1. Row 1 already beats the compliance suite.** 80.21% condition coverage from **6,983
instructions** vs the suite's 79.12% from 889,516 — **127× fewer instructions for slightly
better coverage.** Self-testing with systematic instruction combinations is dramatically more
efficient per instruction.

**2. Operand switching moves FSM transitions 88.63% → 94.28%** while barely touching
condition coverage. Exactly as predicted — forwarding multiplexers are state-machine
controlled.

**3. Interleaving contributes 0.00 pp to condition coverage, and FSM transitions *drop*
94.28% → 93.18%.** A small regression: interleaving reshuffles generated sequences and loses
a few transitions previously caught by chance. Evidence that random restructuring ≠
systematic coverage.

**4. Expression coverage frozen at 95.58% for three configurations**, then 97.05% with hazard
sequences, only 100% with cache tests. **Some expressions are only evaluated during cache-miss
handling** — no amount of instruction-level testing touches them.

**Cost:** 17,294 → 6,732,901 is a **389× increase** for +18.69 pp condition coverage. The
curve is brutally non-linear.

## 5.4 Head-to-head summary

| | Compliance suite | PATARA (full) | Δ |
|---|---|---|---|
| Instructions | 889,516 | 6,732,901 | 7.6× more |
| Statement | 99.40% | 100.00% | +0.60 |
| Branch | 99.07% | 100.00% | +0.93 |
| Expression | 98.33% | 100.00% | +1.67 |
| **Condition** | **79.12%** | **100.00%** | **+20.88** |
| FSM transitions | 88.63% | 100.00% | +11.37 |
| Toggle | **87.87%** | 86.60% | **−1.27** |

**Lead with +20.88 pp condition coverage.** Every other metric was already high.

**Say the toggle line out loud.** PATARA *loses* here — both limited by unreachable
address-space bits. Volunteering the one row where the base paper underperforms is cheap and
buys credibility.

## 5.5 Section 5.6 — the intellectual honesty section

The paper titles a subsection *"What does 100% Coverage Mean for Hardware Verification?"* and
answers against its own interest:

> *"A coverage report with 100% code coverage only indicates that all the code lines and
> conditional expressions of the hardware architecture description were executed during
> simulations... **even with complete code coverage, it cannot be guaranteed that a specific
> RISC-V implementation is completely correct.**"*

**What 100% coverage proves:** every line, branch, condition and FSM transition *in the code
that was written* got exercised.

**What it does not prove:**

- **Missing logic is invisible to coverage.** If a designer forgot a case entirely, there is
  no code for it, so no coverage hole to report. Coverage measures the code you wrote, not
  the code you should have written. *This is the deepest limitation, and why formal methods
  exist.*
- **Errors can be masked.** A wrong intermediate value can be overwritten or cancelled before
  reaching the comparison.
- **Conformance to the RISC-V spec is not checked.** REVERSI proves *internal consistency* —
  that `SUB` undoes what `ADD` did. If both are wrong in mutually-cancelling ways, the round
  trip still closes.

> **REVERSI verifies self-consistency, not specification conformance.** That is a genuinely
> different guarantee from χRVFormal, which checks the design against a reference model built
> from the ISA manual.

## 5.6 Scope exclusions — do not get caught out

From Section 5.1, stated by the authors:

- **CSR / system-class instructions were not executed** — coverage excludes CSR access paths
- **Interrupts and sleep mode not tested** — coverage *disabled* for those entities using
  pragma directives in the VHDL
- Privileged architecture *"out of the scope of this paper, which focuses on the unprivileged
  specification"*

So "100% coverage" means 100% of the *unprivileged, non-interrupt* design.

**Prepared answer:** *"The authors scope it to the unprivileged spec and point to other
methods for privileged verification. It's a real gap — and one of my literature review papers
(INSTILLER) quantifies it: over 10% of coverage and roughly 10% of bugs live in
multi-interrupt and exception handling."*

---

# PART 6 — ALL LIMITATIONS, CONSOLIDATED

**Authors' own admissions**
1. 100% coverage does not guarantee correctness (§5.6)
2. Twin-based verification can be masked by an erroneous software twin (§5.6)
3. The twin is coarse-grained — ignores lane pipeline details and stall conditions (§4.4)
4. CSRs, interrupts, sleep mode and the privileged spec are out of scope (§5.1)

**Additional weaknesses to acknowledge**
5. **REVERSI is not their invention** — ref [31], Shazli & Tehranipoor. Their contributions:
   the RISC-V port, four extensions, cache-miss generation, twin-based co-processor method
6. Extends their own prior paper [10] — incremental
7. **RV32IM only** — no F/D/A/C; floating-point is hard for REVERSI because rounding destroys
   invertibility
8. **One design evaluated** — their own core; no cross-validation on riscv-mini, Rocket, etc.
9. Requires **invertible** instructions, or control code, or the twin approach
10. Bug reporting is one paragraph — no per-bug traces, no count, no external confirmation
11. Uses a commercial simulator (Questa Sim) for coverage measurement
12. Journal tier below IEEE TCAD / Journal of Systems Architecture
13. Very recent (2026) — limited citation record
14. Minor internal inconsistency: abstract says **78.94%** condition coverage for the
    handwritten suite; Table 4 and the conclusion say **79.12%**

---

# PART 7 — RELEVANCE TO OUR PROJECT

| Paper element | Our project (Team 2) |
|---|---|
| Custom RISC-V implementation | Shakti C-Class (pipelined, Bluespec) |
| Compliance suite as baseline | We run `add.S`, `fadd.S`, check `tohost` |
| Custom ISA extension support (§4.2) | `ADDP1` (`rd = rs1+rs2+1`), custom-1 opcode |
| Co-processor twin verification (§4.4) | ECE team's hardware accelerator |
| Hazard-interaction bugs missed by suite | We modified `decoder.bsv` + `base_alu.bsv` — shared logic every instruction flows through |
| Pre-silicon → FPGA validation | Verilator sim → planned FPGA target |

## 7.1 Applying REVERSI to ADDP1

```asm
    ADDP1  target, focus, random     ; modification: target = focus + random + 1
    SUB    target, target, random    ; restoring
    ADDI   target, target, -1        ; restoring (undo the +1)
    BNE    target, focus, fail       ; comparison
```

Satisfies Rule 1 — `ADDP1` appears only in the modification; restoration uses `SUB`/`ADDI`,
entirely different decode paths. If the `FNADDP1` case in `fn_base_alu` is wrong, nothing
cancels it.

## 7.2 The packed absolute-difference instruction

`rd = |rs1 − rs2|` per byte **breaks Rule 2 fundamentally.** Absolute value destroys sign —
from `|a−b|` you cannot tell whether `a > b` or `b > a`. Unlike shift-left, no control code
fixes this; the lost information is a property of the operation, not a few stashed bits.

The authors hit exactly this (V2PRO includes `ABS`) and abandoned REVERSI for the
co-processor, using the twin approach instead. **The same solution applies to us:** compute
once through the custom hardware, once as a plain software loop on the base ISA (subtract,
test sign, negate if needed, per byte), compare.

**This is a usable verification plan for an instruction we have not yet built, derived
directly from the base paper.** Worth stating in the seminar conclusion.

## 7.3 What this implies about our current verification

Our `fadd.S` passing tells us floating-point add works *in isolation*. It tells us nothing
about whether `ADDP1` behaves correctly when stalled mid-pipeline, or when its operands
arrive by forwarding from three stages back, or whether our decoder change altered timing
under a specific hazard.

The single hand-encoded test (`.word 0x002081ab`, checking 1+1+1=3) exercises exactly one
forwarding condition.

---

# PART 8 — Q&A PREPARATION

**Q: Why must the test instruction appear only in the modification operation?**
A: If it also appeared in the restoring operation, a systematic error in that instruction
could cancel itself out — the test would pass despite broken hardware. You would be using the
thing under test to check itself.

**Q: Does 100% coverage mean the processor is correct?**
A: No, and the authors say so in §5.6. It means every line and condition was executed. Faults
can still be masked, missing logic is invisible to coverage, and REVERSI checks
self-consistency rather than conformance to the ISA specification. Coverage is necessary, not
sufficient.

**Q: What is the novelty if REVERSI already existed?**
A: The RISC-V ISA port; four extensions (variable immediates, branch-range handling, hazard
sequence generation, operand swapping); cache-miss generation; and the twin-based
co-processor methodology.

**Q: Why not just use a golden model like Spike?**
A: Reference simulators do not model external components, introduce their own bugs (ref [20]),
cost significant time to generate references (16.10 ms vs 0.01 ms hardware execution), and
are impractical post-silicon where internal observability is limited.

**Q: How does this apply to your project?**
A: Directly. We run the same compliance suite this paper shows is insufficient, on a
pipelined core with custom instructions and a planned accelerator. §4.2 documents adding
custom ISA extensions; §4.4 covers co-processor verification.

**Q: Could this verify your custom instruction?**
A: `ADDP1` yes — invertible via `SUB` + `ADDI -1`. The packed absolute-difference instruction
no — not invertible; it would need the twin-based approach, exactly as the authors did for
V2PRO's `ABS`.

**Q: What are the paper's weaknesses?**
A: RV32IM only (no floating point); CSRs, interrupts and the privileged spec excluded; one
design evaluated; REVERSI borrowed from prior work; coverage ≠ correctness; bug reporting is
thin and self-reported.

**Q: Why does interleaving contribute nothing to condition coverage?**
A: Because it is random. It creates complexity and varied dependency distances, but does not
systematically enumerate hazard scenarios. Randomness gives variety, not coverage — which is
why the explicit hazard-permutation generator was necessary.

**Q: Why did co-processor coverage plateau at 98.78%?**
A: Uniform random vector-length generation under-represents short vectors, and certain
chaining stall conditions only occur with very short vectors. Ten times more tests changed
nothing; changing the *distribution* closed the gap.

---

# PART 9 — NUMBERS CHEAT SHEET

| Fact | Value |
|---|---|
| Handwritten suite condition coverage | 79.12% (abstract says 78.94%) |
| PATARA condition coverage | 100.00% |
| Improvement | +20.88 pp |
| Handwritten suite instructions | 889,516 (17,765 test instructions) |
| PATARA instructions for full coverage | 6,732,901 |
| PATARA first configuration | 6,983 instructions → 80.21% (already beats the suite) |
| RV32I suite alone (condition) | 53.84% |
| RV32M suite alone (condition) | 57.14% |
| Toggle coverage ceiling | 86.60% (suite: 87.87% — PATARA loses) |
| Interleaving contribution to condition cov. | 0.00 pp |
| Operand swapping → FSM transitions | 88.63% → 94.28% |
| Hazard sequences → condition | 81.31% → 96.70% |
| Cache tests → condition | 96.70% → 100% |
| Pipeline stages | 6 (IF, ID, EX, MEM1, MEM2, WB) |
| Sequence length for full hazard coverage | 4 consecutive instructions |
| RISC-V FSM transition cov. (system, handwritten) | 38.83% |
| Lane 0 vs Lane 1 statement coverage | 97.43% vs 89.93% (identical hardware) |
| V2PRO clock / RISC-V clock | 400 MHz / 200 MHz |
| V2PRO datapath / accumulator | 24-bit / 48-bit |
| V2PRO config | 8 clusters × 8 vector units |
| Random sequence generation time | 86.04 ms |
| V2PRO execution time | 0.01 ms |
| Software twin reference calc time | 16.10 ms |
| Branch range limit | ±4 KiB |
| `shamt` immediate width | 5 bits (vs 12 for I-type) |
| Bugs found by compliance suite | 0 |
| Bugs found by PATARA | "several" — 4 categories documented |
| Simulator | Questa Sim-64 2021.3 |
| PRNG used | xoroshiro128plus |

---

# PART 10 — FIGURE INVENTORY

| Fig. | Content | Best used for |
|---|---|---|
| Fig. 1 | System overview: RISC-V + V2PRO + DMA + memory | Experimental setup |
| Fig. 2 | 6-stage RV32IM pipeline structure | Problem / setup |
| Fig. 3 | V2PRO schematic, lane chaining network | Twin-based section |
| **Fig. 4** | **REVERSI assembly example (add/sub)** | **Core mechanism** |
| **Fig. 5** | **PATARA framework overview** | **Architecture** |
| Fig. 6 | XML definition of ADD with reverse SUB | Architecture / custom instructions |
| **Fig. 7** | **Twin-based verification framework** | **Co-processor section** |
| Fig. 8 | Valid chaining combinations | Optional |
| **Fig. 9** | **Missed FSM transition for hazard** | **Problem statement** |

Caption format: *"Fig. 5 — PATARA framework overview (Gesper et al., 2026)"*
