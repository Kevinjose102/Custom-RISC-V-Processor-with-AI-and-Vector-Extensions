# Shakti C-Class Setup Log

Last updated: August 12, 2026 (custom instruction milestone added)
Machine: kevin's laptop (Windows 11 + WSL2 Ubuntu)

This log records the exact steps taken to get the Shakti C-Class RISC-V core
building/simulating locally. Use it to replicate the setup on another
machine, or to pick up where this session left off. Update this file as the
setup progresses further (Verilator install, first successful simulation,
first instruction trace, etc).

---

## 0. Why WSL

C-Class build tooling (`make`, Bluespec compiler, Verilator, Python config
tools) assumes a Linux environment. Windows `cmd`/PowerShell cannot run it
directly. We use WSL2 with Ubuntu.

Install WSL2 (from PowerShell, admin):
```
wsl --install
```

## 1. Clone the repo

Repo: https://gitlab.com/shaktiproject/cores/c-class

```
git clone https://gitlab.com/shaktiproject/cores/c-class.git --recursive
```

**Important:** clone this from *inside WSL/Ubuntu*, not from Windows `cmd`.
Cloning from Windows `cmd` causes Git to convert line endings to CRLF
(`core.autocrlf=true` is Windows Git's default), which silently breaks shell
scripts and Tcl scripts inside the repo (their `#!/usr/bin/env ...` shebang
lines fail with errors like `env: $'bluetcl\r': No such file or directory`).

If you already cloned from Windows and hit shebang errors, fix with:
```
sudo apt install dos2unix -y
find . -type f \( -name "*.sh" -o -name "*.tcl" -o -name "*.py" -o -name "Makefile" -o -name "*.mk" -o -name "*.inc" \) ! -path "./.git/*" -exec dos2unix {} \;
git config --global core.autocrlf input   # prevents recurrence on future clones
```

Note: the repo does **not** use `make patch` (that's from an older/different
version of the docs). The actual current build flow is documented at
https://c-class.readthedocs.io/en/latest/simulating.html and is different
from what a plain `cat README.md` suggests — see below.

## 2. Move WSL off the C: drive (optional but recommended)

WSL's virtual disk defaults to installing on C:, and can grow large as you
install build tooling. If C: is low on space, move the whole distro to D:.

Check WSL version first:
```
wsl --version
```

If it supports `--manage` (WSL >= ~2.4):
```
wsl --shutdown
wsl --manage Ubuntu --move D:\WSL\Ubuntu
```

If `--manage` isn't available, fall back to export/unregister/import:
```
wsl --shutdown
wsl --export Ubuntu D:\WSL\ubuntu-backup.tar
wsl --unregister Ubuntu
wsl --import Ubuntu D:\WSL\Ubuntu D:\WSL\ubuntu-backup.tar --version 2
```
Delete the `.tar` backup afterwards once you've confirmed the distro works
(`wsl -d Ubuntu`, then check `~` and any mounted project files are intact).

**Gotcha hit during this setup:** running `--manage --move` to a target
folder that already had a stale/partial folder in it left the distro in a
broken state (registered but pointing at a vhdx file that didn't exist).
Recovered using the export/import method above, using a `.tar` backup that
had been created from an earlier partial attempt. If `wsl -d Ubuntu` fails
with a "cannot attach disk" / path-not-found error, this is likely why —
unregister and re-import from the last good `.tar`.

## 3. Python environment (venv)

Ubuntu (25.x+ / this WSL image) blocks system-wide `pip install` (PEP 668,
"externally-managed-environment"). Use a virtual environment instead of
`--break-system-packages`:

```
sudo apt install python3-venv python3-full -y
python3 -m venv ~/shakti-venv
source ~/shakti-venv/bin/activate
```

**You must run `source ~/shakti-venv/bin/activate` in every new terminal**
before running any of the Shakti Python tools (`soc_config`, `repomanager`).

Install repo's declared Python dependencies:
```
pip install -r requirements.txt
```
(installs `Cerberus`, `ruamel.yaml`, `pytz`, `GitPython`, `aapg`, and
`soc_config` itself, pinned to `3.0.1`, from
`git+https://gitlab.com/shaktiproject/cores/soc_config.git@3.0.1`)

`repomanager` is a **separate** package, not listed in `requirements.txt`.
Install it explicitly:
```
pip install repomanager
```
This installs PyPI package `repomanager` (v2.0.4 at time of writing), which
matches the "clean/update/patch GitLab repos via YAML config" description
used in the Shakti docs.

## 4. Bluespec Compiler (bsc)

Building `bsc` from source (via https://github.com/B-Lang-org/bsc) requires
GHC 9.6.7, cabal, several Haskell libraries, and a large LaTeX toolchain —
slow and heavyweight. **Skip building from source.** Use the prebuilt
release binary instead:

```
cd ~
wget https://github.com/B-Lang-org/bsc/releases/download/2026.01/bsc-2026.01-ubuntu-22.04.tar.gz
tar -xzf bsc-2026.01-ubuntu-22.04.tar.gz
export PATH=$HOME/bsc-2026.01-ubuntu-22.04/bin:$PATH
echo 'export PATH=$HOME/bsc-2026.01-ubuntu-22.04/bin:$PATH' >> ~/.bashrc
bsc -v   # should print: Bluespec Compiler, version 2026.01 (build 9bd39e6f)
```

Note the extracted folder is named `bsc-2026.01-ubuntu-22.04`, not
`bsc-2026.01` — the release tarball name includes the OS/version suffix.

Confirmed working on this WSL Ubuntu 22.04-compatible environment.

## 5. Generate the build config (`soc_config` + `repomanager`)

Every new terminal, first:
```
cd "/path/to/c-class"
source ~/shakti-venv/bin/activate
export PATH=$HOME/bsc-2026.01-ubuntu-22.04/bin:$PATH
```

Pull dependent BSV library repos:
```
repomanager --yaml "$PWD/test_soc/c64_c32/c64_deps.yaml" --clean
repomanager --yaml "$PWD/test_soc/c64_c32/c64_deps.yaml" --update --patch
```
Note: the docs reference a combined `-cup` flag; the installed PyPI
`repomanager` version instead requires the separate flags `--update
--patch`.

Generate `makefile.inc` and the RTL config for the 64-bit core:
```
soc_config -ispec sample_config/c64/rv64i_isa.yaml \
           -customspec sample_config/c64/rv64i_custom.yaml \
           -cspec sample_config/c64/core64.yaml \
           -gspec sample_config/c64/csr_grouping64.yaml \
           -dspec sample_config/c64/rv64i_debug.yaml \
           --verbose info
```

**Status: CONFIRMED WORKING (Aug 12, 2026).** `soc_config` completes cleanly
end to end for the `c64` (RV64) config — generates `makefile.inc`,
`depends.mk`, the dependency graph, boot code, and benchmarks, then kicks
off `make`. No errors.

**Second CRLF bug found and fixed:** the first dos2unix pass (step 1) only
covered `.sh/.tcl/.py/Makefile/.mk/.inc` files and missed `.bsv` source
files. Since the repo was originally cloned from Windows `cmd`, the `.bsv`
files also had CRLF line endings, which made `bsc`'s lexer choke on string
literals inside them (error: `Bad string escape char` in
`common_bsv/Logger.bsv`). Fixed by re-running dos2unix, this time also
covering `*.bsv *.v *.sv *.yaml *.inc`:
```
find . -type f \( -name "*.bsv" -o -name "*.v" -o -name "*.sv" -o -name "*.yaml" -o -name "*.inc" \) ! -path "./.git/*" -exec dos2unix {} \;
```
**Lesson for next clone:** run dos2unix broadly across the *entire* repo
(all text files, not just scripts) immediately after cloning, or better,
avoid the problem entirely by never cloning from Windows `cmd` in the first
place (clone from inside WSL only).

Also installed along the way as part of `soc_config`'s own dependency setup
(pulled automatically via pip, not something you need to do manually):
`riscv_config` 3.8.0, `csrbox` 1.12.0.

## 6. Next steps

- [x] Confirm `soc_config` completes cleanly after the dos2unix fix — DONE
- [x] Install Verilator — DONE (`sudo apt install verilator -y`, installed
      v5.032, well above the >=4.004 requirement)
- [x] `make generate_verilog` — **DONE (Aug 12, 2026), full success.**
      `bsc` compiled the entire C-Class RTL end to end: all pipeline stages
      (stage0-stage5), register file, decoder, scoreboard, bypass, base ALU,
      branch predictor (gshare), icache/dcache + TLBs + page table walker,
      FPU (single/double precision, all operations), mbox (mul/div), CSR box,
      AXI4/AXI4-Lite fabrics, UART, CLINT, bootrom, BRAM, JTAG DTM, RISC-V
      debug module (debug spec 0.13), and the top-level TbSoc testbench.
      Output: `Compilation finished`, no errors. Only warnings (expected —
      standard BSV scheduling/multi-reset-domain notices, not bugs; see note
      below).
- [x] `make link_verilator` — **DONE (Aug 12, 2026).** `bin/out` exists.
      **C-Class is now built and runnable in simulation on this machine.**
- [x] Get a test program compiled and run through `bin/out` — **DONE
      (Aug 12, 2026). The official RISC-V `add` test (rv64ui) from
      `verification/riscv-tests/isa/rv64ui/add.S` was compiled, converted
      to `code.mem`, and executed on the built core.**
- [x] Trace ADD instruction through the now-working core — **DONE.**
      `./out +rtldump` produces `rtl.dump`, a full instruction-level trace:
      `<privilege> <pc> <instruction hex> <register/mem updated> <value>`
      per line. Confirmed: core boots from bootrom at `0x1000`, jumps to
      `0x80000000`, runs the test's register-clearing/setup code, executes
      the test body, and correctly writes `0x00000001` to address
      `0x80001000` (the standard riscv-tests `tohost` address — a write of
      `1` there is the PASS signal). Core then spins at that PC forever,
      which is expected/correct: nothing is watching `tohost` since we ran
      `bin/out` standalone without attaching `spike`/`fesvr` as a host.
      **Conclusion: the C-Class core correctly fetches, decodes, executes,
      and writes back the ADD instruction (and its full test dependencies)
      — the baseline is functionally verified for this instruction.**

### How to reproduce the ADD trace
```
cd ~/projects/c-class
riscv64-unknown-elf-gcc -march=rv64imafdc -mabi=lp64 -static -mcmodel=medany \
  -fvisibility=hidden -nostdlib -nostartfiles \
  -I verification/riscv-tests/env/p \
  -I verification/riscv-tests/isa/macros/scalar \
  -T verification/riscv-tests/env/p/link.ld \
  verification/riscv-tests/isa/rv64ui/add.S -o bin/add.elf
cd bin
elf2hex 8 4194304 add.elf 2147483648 > code.mem
timeout 15 ./out +rtldump   # +rtldump requires trace_dump:true in core config (already default here)
head -50 rtl.dump   # boot + setup instructions
tail -50 rtl.dump   # should show the tohost=1 pass loop, or new PCs if still running
```
To trace a different instruction/test, swap `rv64ui/add.S` for any other
file under `verification/riscv-tests/isa/rv64ui/` (e.g. `sub.S`, `and.S`,
`beq.S`, etc.) — same recipe applies.

### IMPORTANT: working directory changed — repo now lives in WSL native fs

`make link_verilator` (which calls Verilator's own generated Makefile) hard
**refuses** to build in any path containing spaces
(`/mnt/d/kevin stuff/Brave_Downloads/...` has a space in "kevin stuff") —
this is not a quoting issue, GNU Make just errors out:
`Unsupported: GNU Make cannot build in directories containing spaces`.

Fix applied: copied the whole repo (including the already-generated
`build/hw/verilog/` from the successful `make generate_verilog` run, so
that step didn't need to be redone) to WSL's native filesystem:
```
mkdir -p ~/projects
cp -r "/mnt/d/kevin stuff/Brave_Downloads/mainproject/c-class" ~/projects/c-class
cd ~/projects/c-class
```
**All work from here on happens in `~/projects/c-class`, not the D: drive
copy.** The D: copy is now stale for build purposes (still fine as a
reference/backup, but don't build there). This is also just better practice
for WSL generally — native `~/...` paths compile much faster than `/mnt/d/...`
paths.

Every new terminal, remember to re-run before doing anything:
```
cd ~/projects/c-class
source ~/shakti-venv/bin/activate
export PATH=$HOME/bsc-2026.01-ubuntu-22.04/bin:$PATH
```
- [ ] Get `elf2hex` / riscv-gcc toolchain to compile a test program
- [ ] Run a simple program (e.g. `add.elf`) through the verilated `out`
      binary — this is "the core running on our system"
- [ ] Once running: trace the `ADD` instruction through
      fetch → decode → operand read → execute → writeback, documenting
      exact BSV module/file names (this is the actual deliverable for the
      current project phase — see PROJECT MASTER CONTEXT doc)

## 7. Note on the compile warnings

The `make generate_verilog` run produced a very large number of `Warning:`
lines (hundreds). These are normal for a design of this size and are **not**
errors — the build finished with `Compilation finished` and zero `[ERROR]`
lines. Categories seen, for reference (don't need to act on these now):

- `(G0010)` "Rule X was treated as more urgent than rule Y" — scheduling
  conflict resolution notices, mostly in the AXI4 fabric's many
  auto-generated crossbar rules (expected with a 7-master/7-slave fabric).
- `(G0043)` "Multiple reset signals influence rule X" — expected wherever the
  debug module (separate reset domain) connects to the core/SoC.
- `(T0054)` "Field not defined" — a handful of these appeared (e.g. `fflags`,
  `mtval2`, `atomic_op`, `id`, `sb_id`, `inp_denormal`) in stage2/stage3/
  stage4/dcache/tlb code, tied to the specific ISA config selected
  (rv64i_isa.yaml + rv64i_custom.yaml). Worth understanding later when
  tracing instruction flow through those stages, but did not block the
  build.
- `(G0117)` "Rule X shadows the effects of rule Y" — expected same-cycle rule
  interaction notices.
- `(G0020)`/`(G0023)`/`(G0046)` — misc: `$display` in interface methods,
  empty rule bodies removed, reset info lost at module boundary. All benign
  for simulation.

None of these need fixing to proceed to simulation.

## 8. Test toolchain gotchas (elf2hex, spike)

Getting `make test` working required several more pieces, each with its own
snag:

- **`riscv64-unknown-elf-gcc`**: installed via
  `sudo apt install gcc-riscv64-unknown-elf` — worked cleanly, no issues.
- **`elf2hex`**: there are TWO different tools with this exact name and
  incompatible CLI syntax. SiFive's `elf2hex` (`pip`-free, installs via its
  own `configure`/`make`) uses flag-based args and does NOT match what
  Shakti's scripts expect. The correct tool is the older Berkeley
  `elf2hex` from the (archived) `riscv-fesvr` project, which takes plain
  positional args: `elf2hex <width> <depth> <elf> <base>`. Built from
  source:
  ```
  git clone https://github.com/riscvarchive/riscv-fesvr.git ~/riscv-fesvr-src
  cd ~/riscv-fesvr-src && mkdir build && cd build
  ../configure --prefix=/usr/local
  make          # hits missing-include errors on modern GCC, see below
  sudo make install
  ```
  Had to patch two files for modern GCC compatibility (this ~2018 codebase
  relied on transitive includes that newer GCC no longer provides):
  ```
  sed -i '7a #include <stdexcept>' ~/riscv-fesvr-src/fesvr/dtm.cc
  sed -i '8a #include <cstdint>'   ~/riscv-fesvr-src/fesvr/device.h
  ```
  After install, `elf2hex` links against `libfesvr.so` in `/usr/local/lib`,
  which isn't on the loader path by default — needed:
  ```
  export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
  ```
  (add this to `~/.bashrc` if doing this regularly)
- **`dtc` (device tree compiler)**: needed for `make generate_boot_files`.
  `sudo apt install device-tree-compiler` worked fine (didn't need the
  docs' from-source 1.4.7 build).
- **`spike`**: needed only for `make test`'s automated pass/fail comparison
  (it runs the same program on a reference ISA simulator and diffs
  signatures). We did NOT install this — instead bypassed the automated
  test harness entirely and ran the compiled test directly through
  `bin/out` with `+rtldump`, reading the instruction trace by hand to
  confirm correctness (see section 7 above). Installing `spike`
  (Shakti's `mod-spike` fork) remains a TODO for anyone who wants the
  automated PASSED/FAILED test runner (`make test`, `make regress`)
  working end-to-end.

## 9. Custom instruction: `ADDP1` (rd = rs1 + rs2 + 1)

**Status: CONFIRMED WORKING (Aug 12, 2026).** As the next phase of the
project (adding our own ISA extension), we added a proof-of-concept
3-register R-type instruction, `rd = rs1 + rs2 + 1`, deliberately different
from plain `ADD` so its result is unambiguous in a trace.

### Encoding

Used the RISC-V-reserved `custom-1` opcode space (`0101011`), which is
completely unclaimed by C-Class's decoder (unlike `custom-0`/`custom-2`,
which fall inside existing wildcard opcode buckets and would need extra
handling). Standard R-type layout, arbitrary fixed `funct3`/`funct7`:

```
funct7 = 0000000, rs2, rs1, funct3 = 000, rd, opcode = 0101011
```

Example: `ADDP1 x3, x1, x2` (i.e. `x3 = x1 + x2 + 1`) encodes to
`0x002081ab` (compare to plain `add x3,x1,x2` = `0x002081b3` — only the
opcode byte differs, confirming the encoding math).

### Why these files, and nothing else

Traced how `ADD` is handled through `src/decoder.bsv` and
`src/base_alu.bsv`, and confirmed the following BSV functions all default to
plain-integer-register behavior for any opcode they don't explicitly
recognize — so `fn_decode_rs1type`, `fn_decode_rs2`, `fn_decode_rs2type`,
`fn_decode_rdtype` needed **no changes**. Our new opcode is automatically
treated as a normal 3-register integer instruction.

Only 4 additive edits were needed (nothing existing modified):

1. **`src/decoder.defines`** — added a new ALU function-select constant
   (`FNADDP1 = 9`, the one unused value in the existing 4-bit fn-select
   space) and the new instruction's bit pattern:
   ```
   `define FNADDP1 9   //'b1001
   `define ADDP1_INSTR   'b0000000??????????000?????0101011
   ```
2. **`src/decoder.bsv`, `fn_decode_insttype`** — one new case, classifying
   the instruction as `ALU`:
   ```
   `ADDP1_INSTR           :return ALU;
   ```
3. **`src/decoder.bsv`, `fn_decode_fn`** — one new case, mapping the
   instruction to the new ALU function code:
   ```
   `ADDP1_INSTR: return `FNADDP1;
   ```
4. **`src/base_alu.bsv`, `fn_base_alu`** — one new signal and one new case,
   computing the actual result:
   ```
   let lv_addp1 = fn_add(op1pc?pc:op1, op2, 0) + 1;
   ...
   `FNADDP1: lv_addp1;
   ```

Verified via `git diff --stat`: exactly 2 insertions per file, 6 total,
nothing else touched.

### Rebuild + test

```
cd ~/projects/c-class
make generate_verilog   # bsc recompiles with the new BSV — confirms no syntax errors
make link_verilator     # relinks bin/out with the new instruction
```

Hand-encoded the test since `riscv64-unknown-elf-gcc` has no idea what this
opcode means (used `.word` with the raw hex from above):
```
cat > addp1_test.S << 'EOF'
#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  li x1, 1
  li x2, 1
  .word 0x002081ab   # ADDP1 x3, x1, x2  -> x3 should become 1+1+1 = 3

  RVTEST_PASS

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN
  TEST_DATA
RVTEST_DATA_END
EOF

riscv64-unknown-elf-gcc -march=rv64imafdc -mabi=lp64 -static -mcmodel=medany \
  -fvisibility=hidden -nostdlib -nostartfiles \
  -I verification/riscv-tests/env/p \
  -I verification/riscv-tests/isa/macros/scalar \
  -T verification/riscv-tests/env/p/link.ld \
  addp1_test.S -o bin/addp1_test.elf

elf2hex 8 4194304 bin/addp1_test.elf 2147483648 > bin/code.mem
cd bin
timeout 20 ./out +rtldump
grep -n "002081ab" rtl.dump
```

**Result:**
```
core   0: 0 0x0000000080000138 (0x002081ab) x3 0x0000000000000003
```
`x3` became `0x3`, not `0x2` (plain ADD) — confirms the new opcode decodes
correctly, dispatches to the new ALU function, and computes the intended
result. **Custom ISA extension proven working end-to-end**: encoding →
decode → ALU → register writeback.

### Debugging notes / regression scare (false alarm, but instructive)

While bringing this up we hit a scary moment where `rtl.dump` came back
completely empty (0 bytes) even for the known-good `add.S` test on the
freshly-linked binary — looked like our BSV edits had broken the core
generally. Root cause turned out to be unrelated to the RTL changes at all:
**`bin/out` must be run from inside the `bin/` directory**, because
`boot.LSB`/`boot.MSB`/`code.mem` are referenced via relative paths. Running
`bin/out` from the repo root silently produces a warning
(`$readmem file not found`) and the sim never executes real instructions,
leaving `rtl.dump` empty. Always `cd bin` before running `./out`.

Also re-hit the `elf2hex` argument gotcha in a new form: the correct
Berkeley-style `elf2hex` takes only 4 positional args and writes hex to
**stdout** — it does NOT accept a 5th "output filename" argument. Must
redirect explicitly:
```
elf2hex 8 4194304 <elf> 2147483648 > code.mem      # correct
elf2hex 8 4194304 <elf> 2147483648 code.mem        # WRONG — "Usage:" error
```

And: killing a running `bin/out +rtldump` early with Ctrl+C (SIGINT) leaves
`rtl.dump` empty/truncated — the trace buffer only flushes reliably on
normal exit or `timeout`'s SIGTERM. Let `timeout N ./out +rtldump` run its
full duration without interrupting.

### What's next

`ADDP1` was deliberately a toy instruction — its only job was to prove the
full pipeline (opcode → decode → ALU → writeback → verified via trace) works
end to end on our own build of the core. That's now done. Two threads to
pick up from here:

1. **Harden the proof-of-concept itself (optional polish).** Only one input
   case has been tested (`1+1+1=3`). Worth adding a few more `.word` cases
   to `addp1_test.S` to check zero operands, negative numbers (two's
   complement), and overflow/wraparound at the `xlen` boundary — confirms
   the `fn_add(op1, op2, 0) + 1` reuse trick holds up outside the trivial
   case.
2. **Move from proof-of-concept to the real project instruction (main
   priority).** The actual deliverable is a custom instruction that's
   useful for the edge video anomaly detection workload — e.g. a
   multiply-accumulate for convolution, a SIMD/vector op for batched pixel
   processing, a saturating-arithmetic op, or a threshold/compare op —
   not `rd = rs1 + rs2 + 1`. Once we (or the team) decide what that
   operation actually is, the same 7-step recipe documented above applies
   directly, though a more complex instruction (e.g. multi-cycle
   multiply-accumulate, or one needing new state/registers) would touch
   more than just `base_alu.bsv` — likely a different pipeline stage
   entirely. This needs a design discussion (with the guide/team) on what
   the real target operation should be before writing more RTL.

## 10. Waveform tracing (GTKWave) — enabled Aug 15, 2026

Until now the only verification output was the text trace (`rtl.dump`).
Waveform-level (VCD) dumping is now enabled too, giving a second,
independent way to inspect what the hardware actually did cycle by cycle.

### What was already there vs. what we changed

The Verilator testbench at `test_soc/c64_c32/sim_main.cpp` **already had
full VCD support written in** (lines ~34-44 and ~69) — it includes
`verilated_vcd_c.h`, checks for a `+trace` runtime flag, and calls
`tfp->dump(main_time)` each step. Nothing had to be written from scratch.

It was inert because the design was never *compiled* with tracing
instrumentation. That's a Verilator compile-time flag, and it was missing.

**The one change made:** added `--trace` to `VERILATOR_FLAGS` in
`makefile.inc` (line 22). That's it — one flag.

### Full workflow

```bash
# 1. after adding --trace to VERILATOR_FLAGS in makefile.inc:
cd ~/projects/c-class
make link_verilator

# 2. the VCD is written to logs/ relative to the run directory
cd bin && mkdir -p logs

# 3. run with BOTH flags: +trace (waveform) and +rtldump (text trace)
timeout 20 ./out +trace +rtldump
# prints: "Enabling waves into logs/vlt_dump.vcd..."

# 4. view it (install once: sudo apt install -y gtkwave)
gtkwave logs/vlt_dump.vcd
```

Confirm it compiled in by checking the g++ output during
`make link_verilator` for `-DVM_TRACE=1` and `-DVM_TRACE_VCD=1`.

### Navigating the waveform to the ALU

The signal hierarchy is large and BSV-generated names are cryptic. The
path to the base-ALU output found by hand:

```
TOP > mkTbSoc > soc > ccore_0 > riscv > ff_baseout
```

`ccore_0` is the CPU core instance (the `dmem`/`imem`/`*_xactor_*`
siblings are AXI bus plumbing, not the core logic). `riscv` inside it
holds the pipeline. `ff_baseout` is the FIFO carrying base-ALU results.

Useful signals inside `ff_baseout`:

| Signal | Meaning |
|---|---|
| `CLK` | clock — the ruler, always toggling |
| `ENQ` | pulses high for 1 cycle when a new ALU result is written |
| `D_IN[79:0]` | the data written (result + metadata; wider than `xlen`) |
| `DEQ` / `D_OUT[79:0]` | same data being read out downstream |
| `CLR` | reset — flat 0 means the core is running normally |

Also worth looking at: `ff_commitlog`, which likely carries the same
retirement data that feeds the text `rtl.dump`.

**Method:** select `ENQ`, click Append, then use the next-edge (`>`)
toolbar buttons to jump straight to the next transition instead of
scrolling. Search the full time range first (`From: 1 ps`,
`To: 1096095 ps`), then narrow `From`/`To` around the cursor timestamp
once you've found an event. Right-click `D_IN` to switch the display
format to hex.

### Known limitation: can't pinpoint a specific instruction yet

Correlating a waveform timestamp back to a *specific* instruction is not
currently solved. The clock period is known —
`sim_main.cpp` increments `main_time` by 1 per step and toggles every 5,
and `tfp->dump(main_time)` writes that raw value into the VCD, so
**1 clock cycle = 10 ps in the waveform**. But `rtl.dump` is a
per-instruction-*commit* log in spike format
(`core 0: <priv> 0x<pc> (0x<insn>) <reg> <value>`) with **no cycle
number field** — the `3` in each line is the privilege level (machine
mode), not a cycle count. With a multi-cycle pipeline there's no fixed
lines-to-cycles ratio, so there's no clean formula to jump from an
`rtl.dump` line to a VCD timestamp.

Verified so far: GTKWave loads our build's VCD, the hierarchy is
browsable down to the real ALU-output FIFO, and genuine `ENQ`/`DEQ`
commit events are visible (one captured around ~5405 ps). That's enough
to claim waveform-level verification is available and working. Matching
an exact `ADDP1` cycle is open.

### Other verification methods considered (not yet implemented)

- **Reference-model comparison** — script the expected result in Python,
  run several operand pairs through the core, diff automatically instead
  of reading traces by eye. Most useful next step.
- **Directed edge-case tests** — `op1 < op2` in every lane, all-equal
  bytes, boundary values (0x00/0xFF).
- **`spike` cross-check** — the industry-standard golden-model diff.
  Still not installed (see section 8); a known gap, not a claim we can
  make.

## Key gotchas for whoever picks this up

1. Always run commands from inside WSL Ubuntu, never Windows `cmd`/PowerShell,
   for anything repo/build related.
2. Always `source ~/shakti-venv/bin/activate` first in a new terminal.
3. Always have `bsc` on PATH (`export PATH=$HOME/bsc-2026.01-ubuntu-22.04/bin:$PATH`,
   or just open a new terminal since it's in `.bashrc` now).
4. If you hit weird "file not found" errors on `.sh`/`.tcl`/`.py` scripts
   with a `\r` in the error message, it's a CRLF line-ending problem — run
   `dos2unix` on the affected file(s).
5. Don't blindly copy commands from the official docs' `-cup` flag or
   `make patch` step — this repo's actual current tooling differs slightly
   (see steps 1 and 5 above).
6. **Always run `bin/out` from inside the `bin/` directory**, never from the
   repo root — it looks up `boot.LSB`/`boot.MSB`/`code.mem` via relative
   paths and will silently fail to execute anything otherwise (empty
   `rtl.dump`, no clear error).
7. **`elf2hex` writes to stdout — always redirect with `>`**, it does not
   take an output filename as a positional argument.
8. **Never Ctrl+C a running `bin/out +rtldump`** — use `timeout N` and let
   it complete; killing it early leaves `rtl.dump` empty.
9. **Waveforms need both a compile-time and a runtime flag**: `--trace` in
   `VERILATOR_FLAGS` (rebuild required) *and* `+trace` when running
   `./out`. Either one alone produces no VCD. Also `mkdir -p logs` first —
   the testbench writes to `logs/vlt_dump.vcd` and won't create the dir.
