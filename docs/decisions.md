# Decision Log

Last updated: August 13, 2026
Purpose: a running record of significant decisions made on this project,
with the reasoning behind each — so nobody has to re-derive "why did we do
it this way" later, and so a lost chat doesn't mean lost reasoning.

Format: newest decisions at the bottom (chronological), each with what was
decided, why, and what alternatives were considered/rejected.

---

## 1. Core selection: Shakti C-Class over PicoRV32

**Decision:** Use Shakti C-Class as the baseline processor, not PicoRV32
(the other option presented by the project guide).

**Why:** PicoRV32 is a minimal multicycle RV32I core with no caches, no
virtual memory, and no privileged-mode support — it can't boot an RTOS or
Linux and doesn't have much of a pipeline to actually study or extend.
C-Class is a 6-stage in-order, Linux-capable core with real caches, a
working MMU, branch prediction, and an AXI4 system bus — a much closer
analog to a real edge-AI SoC, and complex enough to be worth studying
without being so complex (like an out-of-order superscalar core) that a
semester-length project couldn't reasonably extend and verify it by hand.

**Alternatives considered:** Rocket/BOOM (Chisel-based, different
toolchain/ecosystem; BOOM's out-of-order complexity would make manual
trace-based verification much harder), CVA6 (roughly comparable to
C-Class technically, but less tied to the Indian/C2S academic ecosystem
this project sits in), VexRiscv (lighter-weight, less feature-complete,
similar limitation to PicoRV32 for this project's purposes).

**Full writeup:** `SHAKTI-ARCHITECTURE-AND-RATIONALE.md`, section 2.

---

## 2. Skip building `bsc` from source; use the prebuilt release binary

**Decision:** Use the prebuilt `bsc-2026.01-ubuntu-22.04` release binary
from GitHub instead of building the Bluespec compiler from source.

**Why:** Building from source requires GHC 9.6.7, cabal, several Haskell
libraries, and a full LaTeX toolchain — a slow, heavyweight side-project
with no benefit for our purposes. The prebuilt binary works identically
for our needs and was confirmed working on this WSL Ubuntu 22.04-compatible
environment.

---

## 3. Clone and build entirely inside WSL, never from Windows `cmd`

**Decision:** All repo operations (`git clone`, builds) happen from inside
WSL/Ubuntu, never from Windows `cmd`/PowerShell.

**Why:** Cloning from Windows converts line endings to CRLF
(`core.autocrlf=true` is Windows Git's default), which silently breaks
shell/Tcl scripts and — as we discovered the hard way — even `.bsv` source
files (caused a `bsc` parse error deep in `common_bsv/Logger.bsv` that took
a second, broader `dos2unix` pass to fully fix). Also set
`git config --global core.autocrlf input` globally to prevent recurrence.

---

## 4. Move the whole repo to WSL's native filesystem (`~/projects/c-class`), not `/mnt/d/...`

**Decision:** After initially working from the D: drive (mounted at
`/mnt/d/kevin stuff/Brave_Downloads/mainproject/c-class` inside WSL), moved
the entire repo to `~/projects/c-class` on WSL's native ext4 filesystem.

**Why:** `make link_verilator` hard-refuses to build in any path containing
spaces (`"kevin stuff"` has one) — not a quoting issue, GNU Make itself
errors out (`Unsupported: GNU Make cannot build in directories containing
spaces`). Moving to native WSL filesystem also has the side benefit of
significantly faster builds than working across the `/mnt/d/` 9P
filesystem boundary. **Consequence: all real build work happens in
`~/projects/c-class`. The D: copy is stale for build purposes** — it's
kept only as a reference/backup and for docs.

---

## 5. Use `riscv-fesvr`'s `elf2hex`, not SiFive's `elf2hex`

**Decision:** Built and used the Berkeley-style `elf2hex` from the
(archived) `riscv-fesvr` project, not SiFive's `elf2hex`.

**Why:** Both tools share the exact same name but have completely
different, incompatible CLI syntax. SiFive's uses flag-based arguments;
Shakti's build scripts expect the older positional-argument style
(`elf2hex <width> <depth> <elf_file> [base]`), which only the
`riscv-fesvr` version provides. Had to patch two files
(`dtm.cc`, `device.h`) for missing `#include`s to get it compiling on
modern GCC.

**Gotcha discovered later:** this `elf2hex` writes to **stdout**, not to a
filename argument — it does not accept a 5th positional "output file"
argument the way we initially assumed. Must redirect: `elf2hex 8 4194304
<elf> <base> > code.mem`.

---

## 6. Skip installing `spike`; verify correctness by manual trace inspection instead

**Decision:** Did not install `spike` (or Shakti's `mod-spike` fork), and
therefore `make test`'s automated pass/fail signature comparison doesn't
work. Instead, compiled test programs manually and verified correctness by
reading `bin/out +rtldump`'s raw instruction trace (`rtl.dump`) by hand,
using the RISC-V `tohost` PASS-signaling convention (a write of `1` to a
known address) as the ground-truth check.

**Why:** Building `spike` looked like a significant side-project on its
own, and for verifying a small number of specific instructions (the ADD
baseline, then our custom instruction), manual trace inspection is
actually more informative anyway — it shows exactly what the hardware did,
not just pass/fail. **Trade-off accepted:** this doesn't scale to running
a large automated regression suite; revisit if/when the project needs to
verify many instructions at once.

---

## 7. Custom instruction proof-of-concept: `ADDP1` (`rd = rs1 + rs2 + 1`) using `custom-1` opcode

**Decision:** Before attempting a "real" useful instruction for the
anomaly-detection extension, built a deliberately trivial proof-of-concept
instruction — `rd = rs1 + rs2 + 1` — to prove the entire
encode→decode→execute→writeback pipeline could be safely extended.

**Why `rd = rs1 + rs2 + 1` specifically:** chosen to be trivially
verifiable by hand (unlike a real workload instruction, whose correctness
would be harder to eyeball), while being deliberately different from plain
`ADD` so a passing test unambiguously proves the *new* hardware path fired
— not that it silently fell through to existing `ADD` behavior.

**Why opcode `custom-1` (`0101011`):** RISC-V reserves four opcode slots
for custom use (`custom-0`, `custom-1`, `custom-2`/rv128, `custom-3`/rv128).
Checked C-Class's actual decoder logic (not just the spec) and found
`custom-1` cleanly unclaimed — no existing wildcard pattern in the decoder
swallows it. `custom-0` and `custom-2`, by contrast, fall inside existing
wildcard buckets (`LOAD_op='000??'` and `FN_op='101??'` respectively) and
would need extra handling to avoid misclassifying existing instructions.

**Why `FNADDP1 = 9` for the ALU function-select code:** the existing 4-bit
`fn` code space (0-15) had exactly one unused value — `9` — found by
listing every `FN*` constant already defined in `decoder.defines`. Not a
meaningful number, just the one free slot.

**Confirmed working:** `git diff --stat` showed exactly 2 insertions each
across `src/decoder.defines`, `src/decoder.bsv`, `src/base_alu.bsv` (6
total, nothing else touched) — verifying the change really was purely
additive. Trace confirmed `x3 = 0x3` (not `0x2`, which plain `ADD` would
give) after executing `ADDP1 x3, x1, x2` with `x1=x2=1`.

**Explicitly not the real deliverable** — see `context.md` "Not yet done"
for what comes next.

---

## 8. Architecture documentation: verify against real build config, not generic docs

**Decision:** After writing an initial architecture/rationale doc based on
Shakti's general public documentation, went back and corrected it against
the actual resolved config our build uses (`core64.yaml`, `rv64i_isa.yaml`,
`makefile.inc`).

**Why:** Generic docs turned out to be wrong or imprecise in several
places for our specific build — e.g. public docs describe a 6-entry return
address stack, ours is configured for 8; public docs are vague about
whether the MMU is "optional," ours has it fully active (Sv39, U/S/M
privilege modes); the FPU's exact implementation detail (`hardfloat:
False`, meaning software-style `bsv_float`, not the Berkeley HardFloat
library) isn't mentioned in generic docs at all. Decided that any
architecture claims made about *our* build should cite the real config
files, not general Shakti marketing/documentation.

**Full corrected writeup:** `SHAKTI-ARCHITECTURE-AND-RATIONALE.md`.

---

## 9. Windows/WSL environment: moved WSL distro from C: to D: drive

**Decision:** Moved the entire WSL2 Ubuntu distro from the default C:
location to `D:\WSL\Ubuntu`.

**Why:** C: was running low on space as build tooling accumulated. Used
`wsl --export`/`--unregister`/`--import` (the `--manage --move` shortcut
hit a broken state on the first attempt due to a stale partial target
folder, recovered via export/import from a `.tar` backup).

---

## 10. Claude Desktop app data relocation: junction, not reinstall

**Decision:** Used an NTFS junction
(`C:\Users\kevin\AppData\Local\Packages\Claude_pzs8sxrjxfjjc` →
`D:\ClaudePackage\Claude_pzs8sxrjxfjjc`) to move Claude Desktop's ~10GB
sandbox VM bundle off the C: drive, rather than uninstalling/reinstalling.

**Why:** Confirmed reinstalling an MSIX/Store-packaged app doesn't
reliably relocate its `AppData\Local\Packages` data even if you pick a
different install drive — that data is tied to package identity, not
install location. The Windows-native "Move" option (Settings → Apps →
Installed apps → Move) also failed with error `0x80073CF6` (Store
package-mover flakiness). The junction approach works at the filesystem
level regardless of Store/MSIX quirks.

**Complication hit and resolved:** After creating the junction, Claude
briefly created a *new*, separate data folder directly on C: instead of
using the junction, causing one chat (inside this project) to appear
missing. Diagnosed by comparing timestamps between the C: and D: copies
and confirming (via `Get-Item ... | Format-List LinkType`) that C: was NOT
actually a junction at that point. Fixed by renaming the stray newer C:
folder to `..._NEW` (preserving it, not deleting), then re-creating the
junction properly. Chat/project data was fully recovered — nothing was
lost. **The `_NEW` backup folder must not be deleted** until stability is
confirmed over several days of normal use.

---

## Open decisions still needed

- **What is the real target instruction for the anomaly-detection
  extension?** `ADDP1` was a proof-of-concept only. Candidates raised in
  discussion but not yet decided: multiply-accumulate (convolution),
  SIMD/vector-style batched pixel op, saturating arithmetic, a
  threshold/compare op. Needs a design conversation grounded in the actual
  anomaly-detection algorithm's bottleneck operation — not yet had.
- **Whether/how to address the missing vector extension.** Identified as
  the single biggest architectural gap for this workload. No decision yet
  on whether to hand-build a minimal pseudo-vector mechanism or accept
  scalar-only custom instructions.
- **Whether to eventually install `spike`** for automated test regression,
  once the instruction set being tested grows beyond what's practical to
  verify by manual trace inspection.
