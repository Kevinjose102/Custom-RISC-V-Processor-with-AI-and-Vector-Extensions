---
name: riscv-rtl-development
description: >
  RTL development and verification guidance for the project's multi-cycle,
  non-pipelined RISC-V RV32IMACF_Zicsr CPU. Use this skill when modifying,
  reviewing, debugging, linting, synthesizing, or extending SystemVerilog RTL,
  especially CPU control, datapath, memory handshakes, compressed instructions,
  atomics, CSRs, floating point, timing/Fmax, and hardware debugging.
---

# RISC-V RTL Development Skill

## 1. Project Overview

This project implements a multi-cycle, non-pipelined RISC-V CPU in SystemVerilog with Rust-based verification.

### Architecture

- ISA: RV32IMACF_Zicsr
- Total supported instructions: 118
- Execution model: multi-cycle, non-pipelined
- Control: 12-state FSM
- Memory: variable-latency ready/valid handshaking
- Verification: Rust-based verification plus RTL simulation
- Debug communication: MMIO FIFO at `0x40000000`
- Datapath: flip-flop-based staging registers for FPGA-safe multi-cycle operation

### ISA Breakdown

- RV32I: 40 instructions
- M extension: 8 instructions
- A extension: 11 instructions
- C extension: 27 instructions
- F extension: 26 instructions
- Zicsr: 6 instructions

---

## 2. Module Hierarchy

The main CPU hierarchy is:

```text
top (CPU)
├── fetch_buffer       # RV32C fetch buffer and compressed-instruction alignment
├── decompress         # RV32C instruction decompressor, combinational
├── decoder            # Instruction decoder
├── alu                # RV32I + M ALU operations
│   └── div_unit       # Hardware division unit
├── regfile            # Integer register file
├── csr_file           # Control and Status Registers
├── branch_unit        # Dedicated branch comparison logic
├── mem_interface      # Instruction/data memory interface logic
└── writeback_mux      # Result selection for register writeback
```

When changing RTL, understand both the local module behavior and the control/dataflow relationship with the rest of the hierarchy.

---

## 3. Multi-Cycle Architecture

The CPU uses a 12-state finite state machine.

| State | Encoding | Purpose |
|---|---:|---|
| `S_BOOT` | `0x0` | After reset, wait for boot signal before first fetch |
| `S_FETCH` | `0x1` | Request instruction and wait for `imem_ready` |
| `S_DECODE` | `0x2` | Decode instruction and read registers |
| `S_EXECUTE` | `0x3` | Execute ALU operation |
| `S_MEM_ADDR` | `0x4` | Calculate memory address |
| `S_MEM_READ` | `0x5` | Request data and wait for `dmem_ready` |
| `S_MEM_WRITE` | `0x6` | Perform memory write and wait for `dmem_ready` |
| `S_WRITEBACK` | `0x7` | Write result to destination register |
| `S_BRANCH` | `0x8` | Evaluate branch and update PC |
| `S_CSR` | `0x9` | Execute CSR operation |
| `S_HALT` | `0xA` | ECALL/EBREAK halt state |
| `S_ATOMIC_RMW` | `0xB` | Atomic read-modify-write operations |

### Cycle Counts

Base cycles exclude additional variable memory latency.

| Instruction class | Base cycles | State sequence |
|---|---:|---|
| R-type | 4 | FETCH → DECODE → EXECUTE → WRITEBACK |
| I-type arithmetic | 4 | FETCH → DECODE → EXECUTE → WRITEBACK |
| Load | 5 | FETCH → DECODE → MEM_ADDR → MEM_READ → WRITEBACK |
| Store | 4 | FETCH → DECODE → MEM_ADDR → MEM_WRITE |
| Branch | 3 | FETCH → DECODE → BRANCH |
| JAL/JALR | 4 | FETCH → DECODE → EXECUTE → WRITEBACK |
| LUI/AUIPC | 4 | FETCH → DECODE → EXECUTE → WRITEBACK |
| M extension | 4 | FETCH → DECODE → EXECUTE → WRITEBACK |
| FENCE | 2 | FETCH → DECODE |
| ECALL/EBREAK | 3 | FETCH → DECODE → HALT |
| CSR | 4 | FETCH → DECODE → CSR → WRITEBACK |

Memory latency adds cycles. For example, with three cycles of instruction-memory latency and three cycles of data-memory latency, a load may take:

```text
5 base cycles + 3 FETCH wait cycles + 3 MEM_READ wait cycles = 11 cycles
```

Do not assume a fixed total instruction latency when memory is variable-latency.

---

## 4. Memory Interface

The CPU exposes external instruction and data memory interfaces.

### Instruction Memory

```text
imem_req    output   CPU requests instruction fetch
imem_ready  input    Memory has valid instruction data
imem_addr   output   Instruction address
imem_data   input    Instruction data
```

### Data Memory

```text
dmem_req    output   CPU requests memory operation
dmem_ready  input    Memory operation complete
dmem_addr   output   Data address
dmem_wdata  output   Write data
dmem_rdata  input    Read data
dmem_we     output   Write enable
dmem_re     output   Read enable
dmem_size   output   Byte/halfword/word operation size
```

### Handshake Rules

- Treat `*_ready` as the external completion/availability signal.
- Do not assume memory responds in one cycle.
- Keep required request/address/data/control information stable for as long as the protocol requires.
- Use explicit staging registers when values must survive across cycles.
- Do not introduce unnecessary combinational dependency through handshake paths.
- `*_ready` paths are an explicit exception to the general preference for registered signals when registration would require major architectural changes.

---

## 5. Instruction Set Support

### RV32I Base

Arithmetic:

```text
ADD, ADDI, SUB
```

Logic:

```text
AND, ANDI, OR, ORI, XOR, XORI
```

Shifts:

```text
SLL, SLLI, SRL, SRLI, SRA, SRAI
```

Comparison:

```text
SLT, SLTI, SLTU, SLTIU
```

Branches:

```text
BEQ, BNE, BLT, BGE, BLTU, BGEU
```

Memory:

```text
LW, LH, LB, LHU, LBU
SW, SH, SB
```

Upper immediate:

```text
LUI, AUIPC
```

Jumps:

```text
JAL, JALR
```

Memory ordering/system:

```text
FENCE, ECALL, EBREAK
```

### M Extension

Multiplication:

```text
MUL, MULH, MULHSU, MULHU
```

Division:

```text
DIV, DIVU
```

Remainder:

```text
REM, REMU
```

### A Extension

Load-reserved/store-conditional:

```text
LR.W, SC.W
```

Atomic memory operations:

```text
AMOSWAP.W
AMOADD.W
AMOXOR.W
AMOAND.W
AMOOR.W
```

Atomic min/max:

```text
AMOMIN.W
AMOMAX.W
AMOMINU.W
AMOMAXU.W
```

Atomic operations use `S_ATOMIC_RMW` and must preserve the required read-modify-write semantics.

### C Extension

Compressed instructions:

```text
C.ADDI4SPN, C.LW, C.SW

C.NOP, C.ADDI, C.JAL, C.LI, C.ADDI16SP, C.LUI
C.SRLI, C.SRAI, C.ANDI
C.SUB, C.XOR, C.OR, C.AND
C.J, C.BEQZ, C.BNEZ

C.SLLI, C.LWSP, C.JR, C.MV, C.EBREAK
C.JALR, C.ADD, C.SWSP
```

Compressed instructions are 16-bit rather than 32-bit and should be handled transparently with normal instructions.

The fetch buffer is responsible for compressed-instruction alignment and mixed 16/32-bit instruction fetching.

Do not modify compressed instruction behavior without checking:

- instruction alignment
- PC increment behavior
- boundary cases where a 32-bit instruction crosses a fetch boundary
- decompression correctness
- interaction between fetch buffering and memory latency

### F Extension

Single-precision floating-point support:

Arithmetic:

```text
FADD.S, FSUB.S, FMUL.S, FDIV.S, FSQRT.S
```

Fused multiply-add:

```text
FMADD.S, FMSUB.S, FNMSUB.S, FNMADD.S
```

Min/max:

```text
FMIN.S, FMAX.S
```

Sign injection:

```text
FSGNJ.S, FSGNJN.S, FSGNJX.S
```

Comparisons:

```text
FEQ.S, FLT.S, FLE.S
```

Conversions:

```text
FCVT.W.S, FCVT.WU.S
FCVT.S.W, FCVT.S.WU
```

Load/store:

```text
FLW, FSW
```

Move/classify:

```text
FMV.X.W, FMV.W.X, FCLASS.S
```

FP architecture requirements:

- 32 floating-point registers `f0`–`f31`
- IEEE 754-2008 compliant behavior
- FCSR support
- Rounding modes
- Exception flags

The default FPGA build currently keeps `ENABLE_F_EXT=0`. Always check the current build configuration and resource/timing reports before assuming the FP implementation is enabled in the target FPGA configuration.

### Zicsr

CSR instructions:

```text
CSRRW, CSRRS, CSRRC
CSRRWI, CSRRSI, CSRRCI
```

CSR behavior must preserve architectural read/write semantics, including immediate-vs-register source forms and read-only/unsupported CSR behavior defined by the project.

---

## 6. Key Architectural Decisions

Preserve these decisions unless an explicit architectural change is being made.

### Multi-Cycle Execution

Instructions use multiple FSM states rather than a single large combinational datapath.

Benefits:

- lower combinational depth
- easier variable-latency memory support
- simpler control
- improved FPGA timing closure

### FSM-Based Control

The FSM explicitly represents architectural phases such as fetch, decode, execute, memory, writeback, branch, CSR, atomic RMW, and halt.

### Variable-Latency Memory

Memory completion is controlled through ready/valid-style handshaking rather than fixed latency assumptions.

### External Memory Ports

Instruction and data memories are external and are managed by the testbench or surrounding system.

### x0 Enforcement

Integer register `x0` is physically hardwired to zero.

Do not rely only on software convention. Hardware must enforce:

```text
x0 == 0
```

Reads of x0 must return zero and writes to x0 must have no architectural effect.

### Dedicated Branch Unit

Branch comparisons are handled by `branch_unit`, not by overloading the ALU.

This keeps branch control explicit and can reduce datapath/control complexity.

### CSR Support

CSR functionality is implemented explicitly through `csr_file` and the CSR FSM path.

### Debug FIFO

A memory-mapped FIFO exists at:

```text
0x40000000
```

It provides host communication through a packet protocol.

Do not casually change this address or protocol behavior.

### Staging Registers

Use flip-flop-based staging registers for values that need to persist between FSM states.

Avoid inferred latches.

---

## 7. Coding Conventions

### Signal Naming

Use snake_case.

Examples:

```text
imem_req
imem_ready
dmem_addr
alu_result
rs1_data
rs2_data
instr_complete
```

Prefix signals according to purpose where practical:

```text
imem_
dmem_
alu_
csr_
branch_
```

Keep standard RISC-V naming for architectural fields:

```text
rs1
rs2
rd
funct3
funct7
opcode
```

### SystemVerilog Style

Use SystemVerilog constructs appropriately:

```systemverilog
always_ff @(posedge clk)
always_comb
logic
typedef enum
```

Prefer explicit combinational assignments and explicit sequential state updates.

Avoid accidental inferred latches.

---

## 8. Reset Conventions

Use synchronous resets only in project RTL modules.

Default internal convention:

```systemverilog
always_ff @(posedge clk) begin
    if (rst) begin
        ...
    end else begin
        ...
    end
end
```

Rules:

- Internal RTL reset ports should normally be active-high and named `rst`.
- Do not introduce active-low internal resets without a strong reason.
- External board/device signals may arrive active-low; convert them to the internal active-high convention near the boundary.
- Do not unnecessarily reset payload-only registers.
- If a payload register has a separate `valid`, `pending`, or similar control bit, reset the control bit rather than the payload.
- Capture/refresh the payload when asserting the corresponding valid/pending bit.
- Downstream logic must ignore payload data whenever its control bit is inactive.

This reduces reset fanout and FPGA routing congestion without changing functional behavior.

---

## 9. Timing and Fmax Priority

Maximizing achievable Fmax and timing margin is a repository priority.

Target frequency:

```text
50 MHz
```

Prefer:

- registered intermediate values
- shorter combinational cones
- explicit multi-cycle staging
- register → logic → register datapath boundaries
- smaller mux/compare/control cones

When a large arithmetic, mux, comparison, or control operation would create a timing-critical path, prefer breaking it into multiple FSM stages if that does not violate the architecture.

Do not optimize solely for minimum cycle count if the resulting design has substantially worse timing closure.

### Registered Signal Preference

Prefer registered signals wherever practical.

Exception:

- handshake return signals such as `*_ready` may remain combinational when registering them would require major architectural changes.

If an unregistered path is retained for architectural reasons, document the timing trade-off.

---

## 10. Mandatory `default_nettype` Guards

Every `.sv` file must begin with:

```systemverilog
`default_nettype none
```

and end with:

```systemverilog
`default_nettype wire
```

Required structure:

```systemverilog
`default_nettype none

// File contents

`default_nettype wire
```

Purpose:

- prevents accidental implicit net declarations
- turns undeclared signals into compile errors
- catches typo-related one-bit wire creation

The closing directive is mandatory so the guard does not affect later files/includes.

All existing project RTL follows this convention. Every newly created RTL file under `rtl/` must follow it.

---

## 11. Linting

Before committing SystemVerilog changes, lint RTL files with Verilator.

Current project command:

```bash
find rtl/common -name '*.sv' -exec verilator --lint-only --Wno-MULTITOP {} +
```

All modified SystemVerilog should pass linting before commit.

Treat new warnings seriously. Do not blindly suppress warnings unless there is a documented reason.

---

## 12. FPGA Synthesis Verification

Whenever SystemVerilog is modified, verify that the design still synthesizes to the FPGA target.

Run:

```bash
(cd rtl/fpga && make)
```

CI automatically performs FPGA synthesis verification on SystemVerilog changes.

Default target:

```text
ecp5_icepi_zero
```

Toolchain:

```text
Yosys
nextpnr-ecp5
```

### Current Constraints

Target frequency:

```text
50 MHz
```

Resource limit:

```text
24,288 LUT4-class combinational cells
```

The default open-source target currently uses:

```text
ENABLE_F_EXT=0
```

Always inspect the latest synthesis reports rather than relying on historical resource or timing numbers.

A change is not complete merely because simulation passes. RTL modifications should also preserve FPGA synthesis viability.

---

## 13. Hardware Debugging Philosophy

### Critical Rule

Never rely heavily on abstract reasoning about what hardware signals "should" be doing.

Hardware debugging must be evidence-driven.

Treat hardware debugging like experimental science:

```text
Observe → Measure → Form hypothesis → Instrument → Verify → Fix
```

### Required Debugging Approach

When behavior is unexpected:

1. Add `$display()` instrumentation.
2. Print actual FSM state transitions.
3. Print important signal values cycle-by-cycle.
4. Observe handshake behavior.
5. Compare expected vs actual values.
6. Form a hypothesis only after collecting evidence.
7. Add targeted instrumentation to verify the hypothesis.
8. Fix the root cause.
9. Re-run simulation and synthesis checks.

### Example Instrumentation

```systemverilog
always_ff @(posedge clk) begin
    if (state == S_FETCH) begin
        $display(
            "FETCH: pc=%h instr=%h imem_ready=%b",
            pc,
            imem_data,
            imem_ready
        );
    end

    if (state == S_EXECUTE) begin
        $display(
            "EXECUTE: alu_op=%h rs1_data=%h rs2_data=%h result=%h",
            alu_op,
            rs1_data,
            rs2_data,
            alu_result
        );
    end
end
```

For FSM debugging, instrument transitions directly:

```systemverilog
always_ff @(posedge clk) begin
    if (state != next_state) begin
        $display(
            "STATE: %h -> %h",
            state,
            next_state
        );
    end
end
```

Use additional instrumentation for:

- PC changes
- instruction capture
- decode fields
- register reads/writes
- memory requests
- memory completion
- atomic operations
- CSR accesses
- writeback
- `instr_complete`

### What Not To Do

Do not:

- assume signal values without observing them
- predict FSM transitions without checking them
- guess memory timing
- infer handshake behavior from intuition alone
- reason through a complicated failure without concrete waveform/log evidence

---

## 14. Debugging Checklist

When an instruction fails:

### Fetch

Check:

```text
pc
imem_req
imem_addr
imem_ready
imem_data
```

Confirm that the instruction being decoded is actually the instruction expected at that PC.

### Decode

Check:

```text
opcode
funct3
funct7
rs1
rs2
rd
immediate
decoded instruction type
```

For compressed instructions also check:

```text
16-bit instruction
quadrant
decompressed 32-bit instruction
PC increment
fetch-buffer state
```

### Execute

Check:

```text
alu_op
rs1_data
rs2_data
immediate
alu_result
branch condition
```

### Memory

Check:

```text
dmem_req
dmem_ready
dmem_addr
dmem_wdata
dmem_rdata
dmem_we
dmem_re
dmem_size
```

Verify that the request remains valid for the required duration and that the FSM does not advance before completion.

### Writeback

Check:

```text
rd
write_enable
write_data
```

Verify that writes to x0 have no effect.

### Completion

Check:

```text
instr_complete
```

It should be high for exactly one cycle when the instruction completes.

---

## 15. Development Workflow

For any RTL change, follow this sequence:

```text
1. Understand the existing architecture
2. Identify affected FSM states/modules
3. Identify state-retained values
4. Make the smallest architectural change necessary
5. Preserve naming/reset/default_nettype conventions
6. Add staging registers when values must cross cycles
7. Add debug instrumentation if behavior is uncertain
8. Run RTL lint
9. Run simulation/Rust verification
10. Run FPGA synthesis
11. Inspect timing/resource reports
12. Remove temporary debug instrumentation if no longer needed
13. Re-run verification
14. Commit only after all checks pass
```

Do not make broad speculative rewrites when a localized change can solve the issue.

---

## 16. Important Invariants

The following invariants should remain true unless the architecture is intentionally changed:

```text
x0 always reads as zero
Writes to x0 have no effect
Memory operations wait for dmem_ready
Instruction fetches wait for imem_ready
instr_complete is a one-cycle completion pulse
No unintended latches are inferred
Every .sv file has default_nettype guards
Internal resets are synchronous and active-high
FSM state transitions are deterministic
Payload registers are valid only when their associated control bit says so
Compressed and standard instructions can be mixed
Atomic operations preserve read-modify-write semantics
CSR operations follow Zicsr semantics
FP behavior follows the project's supported F-extension configuration
RTL remains synthesizable for the default FPGA target
Timing remains compatible with the 50 MHz target
```

---

## 17. Change Review Checklist

Before considering an RTL change complete, verify:

### Functional correctness

- [ ] Instruction semantics are correct.
- [ ] PC behavior is correct.
- [ ] Register read/write behavior is correct.
- [ ] x0 remains hardwired to zero.
- [ ] Memory handshake behavior is correct.
- [ ] Variable latency is handled correctly.
- [ ] `instr_complete` remains a one-cycle pulse.
- [ ] Relevant FSM transitions are correct.
- [ ] State-retained data is stored in staging registers.
- [ ] CSR/atomic/FP behavior is preserved where applicable.
- [ ] Compressed instruction alignment remains correct.

### RTL quality

- [ ] No unintended latches.
- [ ] Correct `always_ff`/`always_comb` usage.
- [ ] Snake_case naming.
- [ ] `default_nettype none` at file start.
- [ ] `default_nettype wire` at file end.
- [ ] Reset conventions are followed.
- [ ] Payload-only registers are not unnecessarily reset.
- [ ] No accidental combinational timing-critical paths were introduced.

### Verification

- [ ] Verilator lint passes.
- [ ] Rust verification passes.
- [ ] Relevant simulations pass.
- [ ] Debug instrumentation was added when behavior was uncertain.
- [ ] FPGA synthesis passes.
- [ ] Resource usage remains within limits.
- [ ] Timing remains compatible with 50 MHz.

---

## 18. Working Principle

The most important development principle for this project is:

> Do not guess what the hardware is doing. Instrument it, observe it, and then reason from the evidence.

When implementing or debugging RTL, prioritize:

```text
Correctness
→ Observable behavior
→ Timing closure
→ Resource efficiency
→ Architectural simplicity
```

Preserve the existing multi-cycle architecture and interfaces unless a change explicitly requires architectural modification.
