# Shakti C-Class: Architecture, Rationale, and Limitations

Last updated: August 16, 2026 (added official Shakti Week 2019 presentation
details, resolved the 5-stage vs. 6-stage naming question)
Companion to `SHAKTI-SETUP-LOG.md` — that file covers *how we built and
extended* the core; this file covers *what the core actually is* and *why
we're using it* for the edge video anomaly detection project.

**A note on accuracy:** the first version of this doc was written from
Shakti's general public documentation. We've since pulled the *actual*
resolved configuration our own build uses — `sample_config/c64/core64.yaml`,
`sample_config/c64/rv64i_isa.yaml`, and the generated `makefile.inc` — and
corrected several details below where the generic docs were vague, wrong,
or just different from what we actually built. Anywhere you see "confirmed
from our build," that's a real, verified number, not a docs quote.

---

## 1. Architecture overview

Shakti is a family of open-source RISC-V processor cores developed by the
RISE group at IIT Madras, spanning everything from tiny microcontroller
cores (E-Class) to multicore/datacenter-class designs (I-Class, M-Class,
H-Class). We're using **C-Class**, the "controller-grade" member of the
family — the one purpose-built for IoT/industrial/automotive-style
embedded workloads, capable of running RTOSes and full Linux.

A block diagram of the SoC as we've configured it (`rv64i_isa.yaml` +
`rv64i_custom.yaml`, the config we ran through `soc_config`) is shown above
in this conversation. Summary of each piece:

**Pipeline (5 architectural stages, 6 RTL modules, in-order, single-issue).**
Worth resolving up front, since it's caused confusion: our own build config
(`core64.yaml`) names six pipeline modules, `stage0` through `stage5`, which
looks like a 6-stage pipeline. But Shakti's own official documentation
(Neel Gala's "C-Class Core: A walkthrough," Shakti Week 2019, IIT Madras —
see Sources) explicitly brands C-Class as **"a simple 5 stage in-order
32/64 bit core."** Both are correct, just counting differently: the six
named stages are PC-Gen, Fetch, Decode, Execute, Memory, and Write-Back —
but PC-Gen (next-PC generation + branch prediction) isn't counted as a full
architectural stage in Shakti's official "N-stage" branding, matching the
classic RISC pipeline convention (IF/ID/EX/MEM/WB) where PC generation is
folded conceptually into instruction fetch rather than counted separately.
**For presentations, say 5-stage** — that's Shakti's own terminology and
matches the project abstract's original framing. If asked about the build
config specifically, the honest answer is "6 named RTL modules
implementing 5 architectural stages, PC-Gen plus the classic 5."

Fetch generates the next
PC and predicts branches using a `gshare` predictor with a 32-entry branch
target buffer, 512-entry branch history table, and an 8-entry return
address stack (**confirmed from our build** — `sample_config/c64/core64.yaml`;
generic public docs quote a 6-entry RAS, ours is configured for 8). In
short: since Fetch has to guess what comes next before a branch is
actually evaluated, `gshare` predicts ordinary branches using recent
global branch history, and the RAS is a small dedicated stack just for
function-return addresses (push on call, pop on return) — not something
we expect to touch for this project, just useful to recognize in the
diagram. Decode
extracts the opcode/`funct3`/`funct7` fields and classifies the instruction
(this is the `decoder.bsv` logic we've been editing directly). Register
Read pulls operands from the integer and floating-point register files,
checking a scoreboard for in-flight hazards; the register file also
forwards the latest same-cycle commit, interrupts and CSR access
violations are checked here, and `WFI` (wait-for-interrupt) stalls the
pipe at this stage. Execute is where the actual computation happens —
routed to the Base ALU, the FPU (F-Box), or the Mbox (multiply/divide
unit) depending on instruction type, all executed in-order; this is where
our custom `ADDP1` instruction now lives. Per Shakti's own docs: "bypass
logic is small and simple," and branch mispredictions are detected at this
stage, not earlier. Memory handles loads/stores against the D-Cache and
will stall if the cache response is delayed, also catching any trap the
cache raises. Writeback commits results back to the register file through
a bypass network (so dependent instructions don't have to stall waiting
for a value to physically land in the register file) — cacheable stores
don't stall here, but non-cacheable stores do, and can trap.

**Memory subsystem.** 16KB instruction cache and 16KB data cache, both
4-way set-associative (**confirmed from our build**: I-Cache =
`64 sets × 4 ways × 16-word blocks × 4 bytes/word` = 16,384 bytes; D-Cache =
`64 sets × 4 ways × 8-word blocks × 8 bytes/word` = 16,384 bytes). **No L2
cache is present in our build** — `core64.yaml` has no L2 section at all,
so this isn't an "optional feature we didn't need," it's simply absent.
**The MMU is present and fully active**, not optional as we first assumed:
`makefile.inc` bakes in `sv39` (39-bit virtual address translation) and
`user supervisor` (both U-mode and S-mode privilege levels implemented,
confirmed by `ISA: RV64IMAFDCSUZicsr_Zifencei` in `rv64i_isa.yaml` — note
the `S` and `U`). This is what makes the core genuinely Linux-capable, not
just "capable in principle." Each cache also has its own TLB
(instruction-side and data-side), each sized 4 entries
(`itlb_size`/`dtlb_size` in `core64.yaml`).

**A real, non-obvious constraint: 32-bit physical address space.** Despite
being a 64-bit ISA with 64-bit virtual addresses (via Sv39 translation),
`physical_addr_sz: 32` in `rv64i_isa.yaml` (and `paddr=32` in
`makefile.inc`) caps actual physical memory at 4GB. Worth keeping in mind
for anything involving large external frame buffers or memory-mapped
peripherals later.

**Execute-stage units.** Besides the base ALU (integer arithmetic, logic,
shifts — and now our custom op), C-Class includes an IEEE-754
single/double-precision FPU, and an Mbox for integer multiply/divide (the
`M` extension). **Important detail confirmed from our build:**
`core64.yaml` sets `hardfloat: False` — meaning our FPU uses Shakti's own
`bsv_float` software-style floating-point implementation, *not* the
well-known Berkeley HardFloat library most other RISC-V cores use. This is
a real, specific design choice, not a generic "low overhead" FPU as public
docs vaguely put it — worth remembering if FP performance becomes a
bottleneck later. Confirmed by Shakti's own team: the F-Box "currently uses
hand-optimized iterative algorithms" (retimed/pipelined versions are listed
as future work on their end, not something present in the version we're
using). The Mbox is configured with `mul_stages_in=1, mul_stages_out=1`
(fast, effectively single-cycle multiply) but `div_stages=32` (an
iterative, 32-cycle divider) — multiply is cheap, divide is expensive;
Shakti's own docs describe this as "an iterative non-restoring division
algorithm," and note that both F-Box and M-Box are the pipeline's
multicycle units (everything else is single-cycle).

**Debug.** A JTAG Debug Transport Module plus a RISC-V-spec-compliant debug
module (spec 0.13) — this is what would let you single-step, set
breakpoints, and inspect registers on real hardware (we've been using
`+rtldump` trace inspection instead, since we're running in simulation).
Also present: 4 PMP (Physical Memory Protection) region entries
(`pmpentries=4` in `makefile.inc`), giving fine-grained memory access
control independent of the full MMU.

**System interconnect and peripherals.** Everything hangs off an AXI4 /
AXI4-Lite bus fabric (64-bit bus width, 4-bit transaction ID width,
confirmed from `core64.yaml`'s `bus_protocol_configuration`) — UART for
serial I/O, CLINT for timer interrupts and inter-processor interrupts, a
BootROM holding the reset vector (`reset_pc: 4096` = `0x1000`, exactly the
PC we've watched every trace boot from), on-chip BRAM, and (in our
simulation setup) `code.mem`/`boot.LSB`/`boot.MSB` standing in for external
memory. The simulated test memory space is 64MB (`test_memory_size:
67108864` in `core64.yaml`).

**Configurability.** Every piece above is tunable through `soc_config`'s
YAML files — cache sizes, whether the FPU/Mbox are present at all, which
RISC-V extensions are enabled (confirmed enabled in our build: `I`, `M`,
`A`, `F`, `D`, `C`, `S`, `U`, `Zicsr`, `Zifencei`, and now our own custom-1
addition). This is the same mechanism that made it possible for us to add
`ADDP1` without touching anything unrelated — the decoder is designed
around exactly this kind of additive extension.

### How an instruction actually moves through this, in plain terms

Since the config above is dense, here's what it means operationally, using
our own `ADDP1` instruction as the running example: Fetch reads the raw
32-bit word `0x002081ab` from `code.mem` at whatever PC it's pointing at,
and — because `gshare` had no branch to predict here — just advances to
`PC+4` for next cycle. Decode looks at the low 7 bits (`0101011`, our
`custom-1` opcode) and, because we taught `fn_decode_insttype` to recognize
it, tags this instruction as `ALU`-bound; `fn_decode_fn` then further tags
it with our `FNADDP1` operation code. Register Read fetches the current
values of `x1` and `x2` from the integer register file (no scoreboard
stall needed, since nothing else was writing to them). Execute routes the
operands and the `FNADDP1` code into `base_alu.bsv`'s `fn_base_alu`, which
runs our added `fn_add(...) + 1` logic. Memory does nothing this cycle
(not a load/store). Writeback commits the result, `0x3`, into `x3` — which
is exactly the line we found in `rtl.dump`. Every instruction the core ever
executes, from a boot-time register clear to a floating-point multiply,
follows this same six-stage shape; only *which* execute unit gets used and
*what* happens at each stage changes.

---

## 2. Why Shakti, and not another core

Our guide framed the choice as Shakti vs. PicoRV32, so that's the direct
comparison, followed by where Shakti sits against the wider RISC-V
open-source core landscape.

**Shakti C-Class vs. PicoRV32.** PicoRV32 is a minimal multicycle RV32I
implementation — no caches, no virtual memory, no privileged
specification, and it does not implement the machine/supervisor mode
infrastructure needed to boot an RTOS or Linux. It's excellent for tiny
FPGA soft-core use cases (bit-banging peripherals, small control logic)
but it's not really a "processor architecture" in the sense our project
needs to study and extend — there isn't much pipeline to trace, and adding
a custom instruction to it wouldn't teach us much about decode/execute
staging, caches, or how a real ISA extension interacts with a memory
hierarchy. C-Class, by contrast, is described by its own documentation as
"amongst the most configurable, Linux-capable, in-order RISC-V open-source
cores available" — branch prediction, blocking caches, TLBs, and a proper
AXI4 system bus. That's a much closer analog to what a real edge-AI SoC
would actually look like, which matters if the end goal is a believable
prototype rather than a toy.

**Shakti vs. Rocket / BOOM (the Berkeley/Chipyard ecosystem).** Rocket is
a comparable in-order application-class core, and BOOM is a
speculative out-of-order superscalar core — both are written in Chisel
(a Scala-embedded hardware DSL), not (System)Verilog/BSV directly. That's
a materially different toolchain and learning curve, and BOOM in
particular is a research-grade core whose complexity (out-of-order issue,
reorder buffers, speculative execution) would make "add one custom
instruction and trace it by hand" a much bigger undertaking than what
we've just done. For a project where the deliverable is *understanding and
extending* a core within a semester, C-Class's more traditional in-order
pipeline is a better match for how much can actually be verified by
reading a trace.

**Shakti vs. CVA6 (Ariane) / VexRiscv.** CVA6 is a similarly capable
Linux-capable in-order core (used heavily in the OpenHW Group ecosystem)
and would arguably have been an equally valid choice on pure architecture
grounds. VexRiscv (SpinalHDL) is lighter-weight and FPGA-friendly but,
like PicoRV32, less feature-complete as a full SoC. Neither has the same
institutional backing in the Indian RISC-V ecosystem that Shakti does —
Shakti is part of a government-backed indigenous processor initiative
(the same C2S/RISE ecosystem referenced in Shakti's own SDK
documentation), which is likely part of why it was the recommended
baseline for this project specifically, alongside the practical fact that
it has an active academic support structure, a maintained GitLab repo with
CI, and its own SDK.

**Bottom line:** Shakti C-Class was chosen not because it's the fastest or
most feature-rich open RISC-V core available, but because it hits a sweet
spot for this project — realistic enough (caches, MMU, AXI fabric, Linux
capability) to be a credible SoC-level base, simple enough (in-order,
single-issue, traditional staged pipeline) to actually study and extend
within the project timeline, backed by tooling and documentation aimed at
exactly this kind of academic use, and within the ecosystem our guide
pointed us toward.

---

## 3. Limitations for the video anomaly detection project specifically

This is the part worth being honest about before committing further design
time. Several of these we've now hit firsthand; others are inherent to the
core's design.

**No vector/SIMD extension.** Shakti C-Class, as configured, does not
implement the RISC-V Vector extension (RVV). Video/CNN-style workloads
(convolutions, matrix multiplies, batched pixel operations) are exactly
the kind of data-parallel work RVV was designed to accelerate — cores like
Ara2 or BOOM+Ocelot exist specifically to add that capability. Without it,
any parallelism in our anomaly-detection pipeline has to be built entirely
as custom scalar instructions (like `ADDP1`, just more complex), executed
one at a time, or offloaded to an external accelerator. This is the single
biggest architectural gap between "what Shakti gives us for free" and
"what a real edge-AI chip usually has."

**Single-issue, in-order pipeline.** Only one instruction executes per
cycle, in program order, with no speculative or out-of-order execution.
For compute-heavy inference workloads this caps throughput well below
what a superscalar or vector core could achieve at the same clock speed —
Shakti's own listed performance (around 1.68 DMIPS/MHz) is representative
of a controller-class core, not an inference accelerator.

**FPU uses a software-style implementation, not hardware-optimized
HardFloat.** Confirmed from our build (`hardfloat: False` in
`core64.yaml`): floating-point operations run through Shakti's own
`bsv_float` logic rather than the industry-standard Berkeley HardFloat
library most comparable RISC-V cores use. If the anomaly detection model
needs floating-point math (most do, unless quantized to int8), this is a
real, specific throughput bottleneck worth benchmarking early, not a vague
"probably slower" concern.

**Small caches relative to real workloads.** 16KB I-Cache / 16KB D-Cache
(4-way), no L2 at all in our build (confirmed — `core64.yaml` has no L2
section). Sized for typical embedded control code, not for holding video
frame buffers or intermediate feature maps. Depending on model and frame
size, we may see significant cache-miss overhead that a simple test
program like `add.S` would never surface.

**Physical memory capped at 4GB regardless of 64-bit addressing.**
Confirmed from our build: `physical_addr_sz: 32` means only 32 bits of
real physical address space exist, even though the ISA and virtual
addressing are both 64-bit. Not a near-term blocker, but worth remembering
before assuming "64-bit" implies unlimited addressable memory for large
frame buffers or datasets.

**No built-in camera/video/DMA peripheral.** The base SoC gives us UART,
CLINT, BootROM, BRAM, and an AXI4 fabric — not a camera interface, image
DMA engine, or video pipeline. Any camera capture path would need a custom
AXI peripheral added to the fabric (a nontrivial SoC-integration task
separate from the CPU-core work we've done so far).

**Toolchain maturity friction (experienced firsthand).** Getting from a
fresh clone to a working simulation required several manual fixes:
missing/incompatible `elf2hex` implementations, a `dtc` dependency not
mentioned until we hit the error, `gcc-riscv64-unknown-elf` needing manual
install, and skipping `spike` integration entirely because building it was
a significant side-project on its own (see `SHAKTI-SETUP-LOG.md` sections
1-8 for the full list). None of this is a fundamental architecture
problem, but it's a real time cost against a project deadline, and it
suggests the tooling isn't as "batteries-included" as, say, a
vendor-supported commercial core would be.

**Manual RTL editing for every new instruction.** As we just experienced,
adding one instruction meant hand-editing four BSV files and manually
re-deriving the hex encoding for testing (`gcc` has no idea our
instruction exists). There's no scripted "define an instruction, get a
toolchain that knows about it" workflow the way RVV gets first-class LLVM/
GCC support. Every additional instruction we add for the actual anomaly-
detection extension will cost roughly this same amount of manual,
error-prone work (as we saw with our own patch-script mishaps this
session) — worth budgeting time for.

**Smaller ecosystem/community than Rocket/BOOM/CVA6.** Fewer public
discussions, tutorials, and third-party debugging writeups exist for
Shakti compared to the Berkeley/OpenHW ecosystems, which can mean more
time spent debugging tooling issues from first principles (as we did) with
less to search for online.

**No characterized power/area numbers for this exact use case.** Shakti
has published DMIPS/MHz and tapeout data for its general controller-class
use cases, but we found no edge-AI-specific power/performance
characterization — meaning any power-budget claims for a real deployed
anomaly-detection device would need to be measured by us, not assumed from
existing literature.

### Net assessment

None of these limitations are disqualifying — they're exactly the kind of
constraints a custom-extension project is supposed to work around, and
"add the missing capability yourself" is the whole point of the exercise
we just completed with `ADDP1`. But they do mean the realistic path
forward is a custom scalar (or hand-built pseudo-vector) extension
targeting the specific bottleneck operation in the anomaly-detection
pipeline, not an assumption that Shakti already has adequate AI/vector
throughput out of the box.

---

## Sources

- [SHAKTI (microprocessor) — Wikipedia](https://en.wikipedia.org/wiki/SHAKTI_(microprocessor))
- [SHAKTI: An Open-Source Processor Ecosystem — ACCS](https://acc.digital/shakti-an-open-source-processor-ecosystem/4/)
- [Shakti Processor — official site](https://shakti.org.in/)
- [Shakti SDK User Manual — C2S Grand Challenge](https://c2s.gov.in/Shakti/Shakti%20SDK%20Manual.pdf)
- [Building the SHAKTI Microprocessor — Communications of the ACM](https://cacm.acm.org/research/building-the-shakti-microprocessor/)
- [A Comparative Survey of Open-Source Application-Class RISC-V Processor Implementations — ACM](https://dl.acm.org/doi/10.1145/3457388.3458657)
- [Deep Learning on RISC-V Platforms at the Edge — ACM Computing Surveys](https://dl.acm.org/doi/10.1145/3772277)
- [A Soft RISC-V Vector Processor for Edge-AI — IEEE](https://ieeexplore.ieee.org/document/9885953)
- [The RISC-V Vector Extensions for AI — Jon Peddie Research](https://www.jonpeddie.com/news/the-risc-v-vector-extensions-for-ai/)
- [shakti/cores/c-class — GitLab](https://gitlab.com/shaktiproject/cores/c-class)
- "C-Class Core: A walkthrough" — Neel Gala, SHAKTI Group, RISE Lab, IIT
  Madras (Shakti Week 2019 presentation, `C-Class-shaktiweek2019.pdf`).
  Official source for the 5-stage branding, per-stage behavioral details
  (Decode/Execute/Memory/Write-Back bullet points above), confirmation of
  GSHARE + BTB + RAS, and BSV/tapeout background. Primary-source material
  from the actual core developers, not third-party documentation.

Note: this document, plus our real build's config files
(`sample_config/c64/core64.yaml`, `sample_config/c64/rv64i_isa.yaml`,
`makefile.inc`), are the ground truth for architecture claims about *our
specific build*. Where general Shakti documentation and our verified build
disagree (e.g. RAS depth, MMU presence, FPU implementation), trust the
verified build numbers in this document.
