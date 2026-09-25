# Custom Instruction Log — FDOT2.S and PFMA.S on Shakti C-Class

This is a record of everything done to design, build, debug and measure custom
floating-point instructions for the MobileNetV2 + GRU workload. It is written
so that someone new to Shakti/BSV can follow it.

---

## 1. The goal in one paragraph

We profiled a MobileNetV2 + GRU model and found that **1×1 (pointwise)
convolution** does most of the work: **267.9 M multiply-accumulates (MACs)**
out of the model's total. Each of those MACs is an FP32 operation:
`acc = acc + input × weight`. Shakti already has `FMADD.S` (one
multiply-add per instruction), so simply adding "another FMADD" would be
pointless. The goal was to design a custom instruction that does **more
useful work per instruction** and then prove, with cycle counts from the real
processor, that it makes the workload faster.

---

## 2. Environment (for reference)

| Item | Value |
|---|---|
| Processor | Shakti C-Class, RV64IMAFDC, in-order, single-issue |
| Hardware language | Bluespec SystemVerilog (BSV), compiler `bsc 2026.01` |
| Simulator | Verilator 5.032 (turns the hardware into a program called `bin/out`) |
| Compiler | `riscv64-unknown-elf-gcc 14.2.0` |
| FPU in use | `src/fpu/hardfloat/fpu_hardfloat.bsv` (because `hardfloat` is defined in `makefile.inc`) |
| FP register width | `flen=64` → one FP register holds **two** FP32 values |
| Data cache | 16 KB (64 sets × 4 ways × 64-byte lines) |

Build and run commands used throughout:

```bash
cd ~/projects/c-class
make generate_verilog > build.log 2>&1 && make link_verilator >> build.log 2>&1
grep -E "^Error" -A6 build.log | head        # only real errors
cd bin; timeout 20 ./out +rtldump            # run the simulated chip
```

`rtl.dump` gets one line per completed instruction, showing the registers and
memory it changed. Every result in this log was read from that file.

---

## 3. How a floating-point instruction flows through Shakti

We traced `FMADD.S` through the pipeline before changing anything:

```
decoder.bsv         decides: "this is a FLOAT instruction", reads fs1, fs2, fs3
      │
stage2.bsv          reads the three FP registers
      │             (for R4 instructions, op3 = the VALUE of fs3, not instruction bits)
stage3.bsv          rule rl_fbox → packs operands into Input_Packet → sends to FPU
      │             waits while fpu_ready is low
fpu_hardfloat.bsv   rule start → picks the unit by `opcode` → spfma.request(...)
      │             rule output_spfma ← result comes back from the FMA pipeline
stage4.bsv          rule rl_capture_float → forwards result
      │
stage5.bsv          writes the result into the FP register file
```

Important facts discovered along the way:

1. `fpu_ready = !(rg_multicycle_op || ff_input.notEmpty)`. **The FPU accepts only
   one operation at a time.** A new FP instruction waits until the previous one
   finishes. This turned out to be the key performance fact.
2. The FPU chooses what to do using a 4-bit `opcode`, which comes from the
   decoder's `fn` field. That field is reliable.
3. The FPU's `funct7` field comes from `op3.data`. For R4 instructions
   (FMADD, FDOT2, PFMA), `op3.data` is the **value in register fs3**, not the
   instruction bits, so `funct7` cannot be used to identify R4 instructions.
4. Before a single-precision operation, the FPU checks that each operand is
   **NaN-boxed** (upper 32 bits all ones). If not, it replaces the operand with
   NaN. Packed values (two floats in one register) are never NaN-boxed, so the
   custom instructions must read the **raw** operands from `input_packet`.

---

## 4. Design 1: FDOT2.S (packed dot product)

### What it does

```
FDOT2.S fd, fs1, fs2, fs3
fs1 = [a1 | a0]   (two FP32 values, loaded with one fld)
fs2 = [b1 | b0]
fd  = a1·b1 + (a0·b0 + fs3)
```

It reuses the existing FP32 FMA unit twice in a row (step 1: `a0·b0 + c`,
step 2: `a1·b1 + partial`). The rounding is exactly the same as two
`fmadd.s` instructions in a row, so the results are **bit-identical** to the
normal code.

### Encoding

- Opcode **custom-2** (`0x5B`, `1011011`), R4 layout, fmt bits `[26:25] = 00`.
- Written in assembly/C as: `.insn r4 0x5B, 0, 0, fd, fs1, fs2, fs3`.
- Example word: `0x202081db` = `FDOT2.S f3, f1, f2, f4`.

### The decoder trick ("remap")

Adding a brand-new opcode would have needed changes in about five decoder
functions. Instead, at the very top of `fn_decode`, the custom-2 word is
rewritten into an **internal** form: the FMADD opcode with fmt = `10`
(half precision, which this core does not implement, so the pattern is otherwise
unused). After that, all the existing FMADD decoding (read fs1/fs2/fs3,
write fd, FLOAT type, scoreboard) works unchanged. The decoder then sets
`fn = 0110`, so the FPU can tell it apart from a real FMADD.

---

## 5. Problems hit while building FDOT2, and how each was fixed

| # | Symptom | Cause | Fix |
|---|---|---|---|
| 1 | BSC error: `Rule RL_output_spfma uses methods that conflict in parallel` | One rule both read `spfma.response` and called `spfma.request` | Split step 2 into its own rule `rl_fdot_step2`; the partial result is saved in a register (costs 1 extra cycle) |
| 2 | Test ended with `tohost = 0x539` and `mcause = 2` (illegal instruction) | **Stale build.** The decoder Verilog was older than the edited `decoder.bsv`, so the simulator still ran the old decoder | Deleted `build/hw/intermediate/decoder.*` and `build/hw/verilog/*fn_decode*`, rebuilt |
| 3 | Result was `0x7fc00000` (NaN) | The FPU's NaN-boxing check replaced the packed operands with NaN | Read raw operands `input_packet.operand1/2` for FDOT2 |
| 4 | Still NaN | FDOT2 was detected with `f7[1:0] == 10`, but for R4 instructions `f7` is bits of fs3's **value**, so the check was false and FDOT2 ran as a plain FMADD | Gave FDOT2 its own FPU opcode: decoder sets `fn = 0110`, FPU checks `opcode == 4'b0110` |
| 5 | Benchmark started at the wrong address; `_start` not found | `bench_wrap.S` was saved empty (nano paste failed) | Wrote the file with `cat > file << 'EOF'` instead |

**Lesson:** always check the date/time of `bin/out` after a rebuild, and
use `;` rather than `&&` after `timeout ... ./out` (timeout returns an error
code, which makes `&&` skip the next command).

### FDOT2 correctness test

`fdot2_test.S` loads `[2.0 | 1.5]`, `[4.0 | 3.0]` and `0.5`, then runs FDOT2.

Expected: `1.5×3 + 0.5 + 2×4 = 13.0 = 0x41500000`.

```
core 0: ... (0x202081db) f3  0xffffffff41500000   ← FDOT2 result
core 0: ... (0xe0018553) x10 0x0000000041500000   ← fmv.x.w read it back
```

✅ **Pass.**

---

## 6. First benchmark and the key insight

Kernel shaped like `features.2.conv.0.0` (16→96 channels, 64 pixels,
98,304 MACs). Both versions compute the same outputs, checked bit for bit.

| | Instructions | Cycles | Cycles/MAC |
|---|---|---|---|
| Baseline (`fmadd.s`) | 633,290 | 1,151,086 | 11.7 |
| FDOT2.S | 338,373 | 1,071,453 | 10.9 |

**Instructions went down 1.87×, but cycles only 1.07×.**

**Why:** the FPU handles one operation at a time, and each FMA takes about
10 cycles. FDOT2 still does two FMAs one after the other, so the FMA wait
time is unchanged. FDOT2 only removed load and loop instructions, which
weren't the bottleneck.

**Conclusion:** the kernel is limited by **FMA throughput**, not by instruction
count. To go faster, the hardware must do **two FMAs at the same time**.

---

## 7. Design 2: PFMA.S (2-lane packed FMA)

### What it does

```
PFMA.S fd, fs1, fs2, fs3
fs1 = [x1 | x0]   two neighbouring pixels of one input channel (one fld)
fs2 = w           one weight (flw), shared by both lanes
fs3 = [c1 | c0]   two accumulators
fd  = [ fma(x1, w, c1) | fma(x0, w, c0) ]   ← computed in PARALLEL
```

- PyTorch stores images as NCHW, so neighbouring pixels of a channel sit next
  to each other in memory. One 64-bit `fld` loads a pair, with no data
  reshuffling needed.
- Each lane is exactly one `fmadd.s`, so results are **bit-identical** to the
  normal code.
- Hardware cost: **one extra FP32 FMA unit** (`spfma2`).

### Encoding

- custom-2, R4 layout, fmt = `10` → `.insn r4 0x5B, 0, 2, fd, fs1, fs2, fs3`.
- Bit 25 stays 0 for both FDOT2 and PFMA, so the core treats both as single
  precision.
- The decoder sets `fn = 0111` for PFMA and `fn = 0110` for FDOT2.

---

## 8. Final code changes (all files)

### `src/decoder.defines` (added at the end)

```bsv
// FDOT2.S : custom-2 (0x5B), R4 layout, fmt=00
`define FDOT2_INSTR      'b?????00??????????????????1011011
// internal form after remap: FMADD opcode with fmt=10 (unused, no Zfh)
`define FDOT2_INT_INSTR  'b?????10??????????????????1000011
```

### `src/decoder.bsv`

Top of `fn_decode` (the parameter was renamed from `inst` to `inst_in`):

```bsv
function DecodeOut fn_decode(Bit#(32) inst_in, CSRtoDecode csrs ... );
    Bit#(32) inst = inst_in;
    if (inst_in[6:0] == 'b1011011 && inst_in[25] == 1'b0)       // FDOT2 / PFMA (custom-2)
      inst = {inst_in[31:27], 2'b10, inst_in[24:7], 7'b1000011}; // -> internal FMADD fmt=10
```

Under `Bit#(4) fn = fn_decode_fn(inst, csrs);`:

```bsv
    if (inst_in[6:0] == 'b1011011 && inst_in[25] == 1'b0)
      fn = (inst_in[26] == 1) ? 4'b0111 : 4'b0110;              // PFMA=0111, FDOT2=0110
```

In `fn_decode_insttype`, under the `FUSED_INSTR` line:

```bsv
      `FDOT2_INT_INSTR : if( valid_rounding && csrs.csr_misa[5]==1 && fs !=0) return FLOAT; else return TRAP;
```

### `src/fpu/hardfloat/fpu_hardfloat.bsv`

New unit and registers:

```bsv
    let spfma2 <- mkspfma_instance;               // PFMA lane 1

    Reg#(Bool)     rg_fdot        <- mkReg(False); // FDOT2 step 1 in flight
    Reg#(Bool)     rg_pfma        <- mkReg(False); // PFMA in flight
    Reg#(Bool)     rg_fdot_issue2 <- mkReg(False);
    Reg#(Bit#(32)) rg_fdot_part   <- mkReg(0);
    Reg#(Bit#(32)) rg_fdot_a1     <- mkReg(0);
    Reg#(Bit#(32)) rg_fdot_b1     <- mkReg(0);
    Reg#(Bit#(3))  rg_fdot_rm     <- mkReg(0);
    Reg#(Bit#(5))  rg_fdot_flag   <- mkReg(0);
```

In `rule start`, the FMA branch:

```bsv
else if(opcode == `FMADD || opcode == `FMSUB || opcode == `FNMSUB || opcode == `FNMADD
        || opcode == 4'b0110 || opcode == 4'b0111) begin
    if(opcode == 4'b0111) begin                     // PFMA.S: two lanes in parallel
      Bit#(64) r1 = input_packet.operand1;
      Bit#(64) r2 = input_packet.operand2;
      Bit#(64) r3 = input_packet.operand3;
      spfma.request (2'b00, r1[31:0],  r2[31:0], r3[31:0],  f3);
      spfma2.request(2'b00, r1[63:32], r2[31:0], r3[63:32], f3);
      rg_pfma <= True;
    end
    else if(opcode == 4'b0110) begin                // FDOT2.S step 1
      Bit#(64) raw1 = input_packet.operand1;
      Bit#(64) raw2 = input_packet.operand2;
      spfma.request(2'b00, raw1[31:0], raw2[31:0], op3[31:0], f3);
      rg_fdot    <= True;
      rg_fdot_a1 <= raw1[63:32];
      rg_fdot_b1 <= raw2[63:32];
      rg_fdot_rm <= f3;
    end
    else if(issp)
      spfma.request(opcode[1:0], truncate(op1), truncate(op2), truncate(op3), f3);
    `ifdef dpfpu
    else
      dpfma.request(opcode[1:0], op1, op2, op3, f3);
    `endif
    rg_multicycle_op <= True;
end
```

Output rule plus the FDOT2 step-2 rule:

```bsv
rule output_spfma(spfma.resp_valid);
  let res  = spfma.response;
  let flag = tpl_2(res);
  if (rg_fdot) begin                        // FDOT2 step 1 done: save partial
    rg_fdot        <= False;
    rg_fdot_part   <= tpl_1(res)[31:0];
    rg_fdot_flag   <= flag;
    rg_fdot_issue2 <= True;
  end
  else begin
    Bit#(ELEN) out;
  `ifdef dpfpu
    out = {'1, tpl_1(res)[31:0]};
  `else
    out = zeroExtend(tpl_1(res));
  `endif
    Bit#(5) fl = flag | rg_fdot_flag;
    if (rg_pfma) begin                      // PFMA: pack both lanes
      let q = spfma2.response;
      out = {tpl_1(q)[31:0], tpl_1(res)[31:0]};
      fl  = fl | tpl_2(q);
      rg_pfma <= False;
    end
    tx_fbox_out.u.enq(XBoxOutput{valid: True, data: out, fflags: fl});
    rg_fdot_flag     <= 0;
    rg_multicycle_op <= False;
  end
endrule

rule rl_fdot_step2(rg_fdot_issue2);         // FDOT2 step 2: a1*b1 + partial
  spfma.request(2'b00, rg_fdot_a1, rg_fdot_b1, rg_fdot_part, rg_fdot_rm);
  rg_fdot_issue2 <= False;
endrule
```

No changes were needed in stage 2–5: the existing FLOAT path, scoreboard,
forwarding and writeback carry the new instructions as they are.

**Harmless compile warnings** (expected): `start` more urgent than
`rl_fdot_step2`, and `output_spfma` more urgent than `rl_fdot_step2`. They can
never be ready in the same cycle, because `rg_multicycle_op` stays True during
an FDOT2, which blocks new FP instructions.

### Problem hit while adding PFMA

| Symptom | Cause | Fix |
|---|---|---|
| `tohost = 0x539`, `mcause = 2` right at the PFMA instruction | The decoder lines still checked `inst_in[26:25] == 00`, which matches FDOT2 only | Changed both checks to `inst_in[25] == 0` (applied with `sed`); the FPU edits were applied with a small Python script |

---

## 9. Verification

| Test | What it checks | Result |
|---|---|---|
| `fdot2_test.S` | FDOT2 gives 13.0 | ✅ `0x41500000` |
| `rv64uf/fmadd.S` (official riscv-tests), after FDOT2 | Normal FMADD.S not broken | ✅ `tohost = 1` |
| `rv64uf/fmadd.S`, after PFMA | Normal FMADD.S still not broken | ✅ `tohost = 1` |
| `bench.c` | Baseline vs FDOT2 vs PFMA outputs are **bit-identical** on all outputs, all layers | ✅ `tohost = 1` |

How to read `tohost` (address `0x80001000` in `rtl.dump`):
`1` = pass, any other odd number = a failing test case, `0x539` = unexpected trap.

---

## 10. Results

### 10.1 Single layer (16→96, 64 pixels, 98,304 MACs)

| | Cycles | Instructions | Cycles/MAC | Speedup |
|---|---|---|---|---|
| Baseline | 1,173,255 | 639,755 | 11.9 | 1.00× |
| FDOT2.S | 1,034,125 | 338,505 | 10.5 | 1.13× |
| **PFMA.S** | **702,787** | **320,362** | **7.1** | **1.67×** |

### 10.2 Five real layer shapes

Each layer used its real input-channel count K and a sample of 16 output
channels × 8 pixels (K × 128 MACs).

| Layer | K | Baseline cyc/MAC | PFMA cyc/MAC | Speedup | Instructions |
|---|---|---|---|---|---|
| features.2.conv.0.0 (16→96) | 16 | 11.83 | 6.97 | **1.70×** | 1.97× fewer |
| features.3.conv.2 (144→24) | 144 | 11.11 | 6.58 | **1.69×** | 2.00× fewer |
| features.12.conv.0.0 (96→576) | 96 | 11.13 | 6.57 | **1.69×** | 1.99× fewer |
| features.17.conv.2 (960→320) | 960 | 13.85 | 9.27 | **1.49×** | 2.00× fewer |
| features.18.0 (320→1280) | 320 | 13.75 | 9.18 | **1.50×** | 2.00× fewer |

**Why the large layers gain less:** with K = 320 or 960, the inputs plus
weights (about 30–90 KB) don't fit in the 16 KB data cache. Both versions then
spend about 2.5 extra cycles per MAC waiting for memory. PFMA speeds up the
arithmetic but not memory, so the relative gain is smaller.

### 10.3 Estimate for all 34 pointwise layers of MobileNetV2

MAC counts come from the profiling (they sum to exactly 267,939,840).
Layers are grouped by K: small (K ≤ 192) use the small-K averages
(11.36 / 6.71 cyc/MAC); large (K ≥ 320) use the large-K averages
(13.80 / 9.23 cyc/MAC).

| | Small-K layers | Large-K layers | **Total** |
|---|---|---|---|
| MACs | 169.9 M | 98.0 M | **267.9 M** |
| Baseline cycles | 1,930 M | 1,353 M | **≈ 3.28 billion** |
| PFMA cycles | 1,140 M | 904 M | **≈ 2.04 billion** |

**Estimated pointwise speedup ≈ 1.6× (about 38% fewer cycles).**

### 10.4 Caveats (be honest about these in the report)

1. Each layer was measured on a sample (16 outputs × 8 pixels) with its real K,
   then scaled by MAC count. The inner loop is the same for every output, so the
   cycles per MAC carry over, but real layers have far more pixels and their
   cache behaviour may differ.
2. Only **pointwise** layers are accelerated. Depthwise convolution, the first
   convolution and the GRU are not yet, so the whole-model speedup will be
   lower than 1.6× (Amdahl's law).
3. The input data was pseudo-random. FMA timing doesn't depend on the values,
   so this doesn't affect cycle counts.

---

## 11. How to reproduce

```bash
cd ~/projects/c-class
# 1. build the processor
make generate_verilog > build.log 2>&1 && make link_verilator >> build.log 2>&1
grep -E "^Error" -A6 build.log | head
ls -l --time-style=+%H:%M bin/out                        # must be fresh

# 2. build and run the benchmark
riscv64-unknown-elf-gcc -march=rv64imafdc -mabi=lp64 -O2 -mno-relax -ffreestanding -static -mcmodel=medany \
  -nostdlib -nostartfiles -I verification/riscv-tests/env/p -I verification/riscv-tests/isa/macros/scalar \
  -T verification/riscv-tests/env/p/link.ld bench/bench_wrap.S bench/bench.c -o bin/bench.elf
elf2hex 8 4194304 bin/bench.elf 2147483648 > bin/code.mem
cd bin; timeout 600 ./out +rtldump
grep -m1 "mem 0x0000000080001000" rtl.dump              # 0x...01 = all outputs match
```

`bench_wrap.S` switches to machine mode (so `mcycle`/`minstret` can be read),
enables the FPU, sets up a 16 KB stack, calls `bench_main()` and reports
pass or fail through `tohost`. `bench.c` runs the baseline and PFMA
kernels, stores the cycle and instruction counts in `results[]`, and compares
the outputs bit for bit.

Backups of the working files are in `~/fdot2_backup/` and `~/pfma_backup/`.

---

## 12. Next steps

1. **GRU:** its matrix-vector products are the same multiply-accumulate pattern,
   so PFMA can speed them up too. This completes the "MobileNetV2 + GRU" story.
2. **Software tuning:** loop unrolling to cut the remaining loop overhead per FMA.
3. **Report:** profiling → bottleneck → FDOT2 → insight (FMA throughput) →
   PFMA → measured 1.5–1.7× per layer, ≈1.6× on all pointwise layers.

---

## 13. Glossary

| Term | Meaning |
|---|---|
| MAC | One multiply-accumulate: `acc = acc + a × b` |
| FMA / FMADD.S | Fused multiply-add: does a MAC with a single rounding |
| Pointwise (1×1) conv | Each output pixel is a dot product across input channels |
| K | Number of input channels = length of each dot product |
| Packed | Two FP32 values stored side by side in one 64-bit register |
| NaN-boxing | RISC-V rule: a 32-bit float in a 64-bit register must have all-ones in the upper half |
| R4 format | Instruction layout with three source registers (fs1, fs2, fs3) plus fd |
| custom-2 | Opcode `0x5B`, reserved by RISC-V for custom extensions |
| `tohost` | Memory word the test writes its pass/fail code into |
| `mcause` | Register holding the reason for a trap (2 = illegal instruction) |
| Regression test | Re-running an existing test to prove that new changes didn't break it |
| Bit-identical | Results match exactly, every bit, not just "close enough" |
