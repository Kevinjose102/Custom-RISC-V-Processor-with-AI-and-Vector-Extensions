---
name: design-microarch
description: "Use when processing RTL modules at the microarchitecture level - including FIFO, state machines, counters, arbiters, decoders, or any Verilog/SystemVerilog hardware design. Load this skill immediately upon identifying RTL design tasks, before diving into brainstorming，planning or implementation."
---

# RTL Microarchitecture Design Guide

## Overview

This skill provides microarchitecture design guidance for RTL modules. It covers design principles, naming conventions, interface design, module partitioning, and architectural decisions that should be established **before** writing code.

**Core principle**: Good microarchitecture decisions made early prevent costly refactoring later.

## When to Use

Load this skill when:
- User requests RTL design ("design a FIFO", "create a state machine", "build a counter")
- Starting brainstorming phase for any Verilog/SystemVerilog task
- Discussing module interfaces, partitioning, or architecture
- Evaluating different design approaches

**Do NOT wait until coding phase.** Microarchitecture decisions shape the entire design process.

## Core Design Principles

### 1. Interface-First Design

Define interfaces before implementation:

```
Module Interface Template:
- Clock and reset naming (clk, rst_n)
- Data signals: prefix-based naming (in_vld, in_rdy, in_data)
- Control signals: clear semantic names
- Parameter naming: ALL_CAPS with explicit types
```

### 2. Module Partitioning

Split modules by:
- **Functionality**: Each module has one clear purpose
- **Timing**: Separate combinatorial and sequential logic
- **Reusability**: Generic modules vs application-specific modules

### 3. Naming Conventions

**Signal naming**:
- Active-low suffix: `_n` (rst_n)
- Valid/ready pairs: `xxx_vld`, `xxx_rdy`, `xxx_data`
- Vector prefix: `v_` for independent signals of same type
- Consistent prefix for related signals

**Module naming**:
- Descriptive and unique: `sc_bus_arbiter` not `arbiter`
- One module = one file
- File name = module name

**Parameter naming**:
- ALL_CAPS: `DATA_WIDTH`, `FIFO_DEPTH`
- Explicit type: `parameter integer unsigned DATA_WIDTH = 8`

### 4. Clock Domain Crossing

For async designs:
- Identify all clock domains upfront
- Plan synchronizers (2-stage for control, FIFO/Handshake for data)
- Use gray code counters for pointers

### 5. Reset Strategy

- Define reset type per module (async vs sync)
- Synchronous release always
- Reset value should be documented

## Quick Reference

| Design Aspect | Key Considerations |
|--------------|-------------------|
| **Interface** | Define before implementation, use consistent prefixes |
| **Partitioning** | Single responsibility, separate timing domains |
| **Naming** | Meaningful, consistent, prefix-based for buses |
| **Parameters** | Type-explicit, ALL_CAPS, synthesizable defaults |
| **Clock Domains** | Identify early, plan CDC structures |
| **Reset** | Document type, synchronous release |

## Design Decision Checklist

Before coding, answer:

- [ ] What are the interfaces (inputs/outputs/parameters)?
- [ ] Is this single or multiple clock domains?
- [ ] What's the reset strategy?
- [ ] How should the module be partitioned?
- [ ] What naming conventions apply?
- [ ] Are there reusable sub-modules?
- [ ] What's the parameterization strategy?

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| **Inconsistent naming** | Debugging nightmare | Define naming convention upfront |
| **Late partitioning** | Rewrites, bugs | Partition during design phase |
| **No interface spec** | Integration failures | Define all interfaces first |
| **Ignoring CDC** | Metastability, data corruption | Identify clock domains early |
| **Hard-coded values** | Non-reusable modules | Parameterize from start |

## Architectural Patterns

### FIFO Pattern
```
Interfaces:
- Write side: wr_clk, wr_rst_n, wr_en, wr_data, full
- Read side: rd_clk, rd_rst_n, rd_en, rd_data, empty
Key decisions: Depth, width, clock domains, full/empty logic
```

### State Machine Pattern
```
Interfaces:
- Control inputs, status outputs
- State-specific data paths
Key decisions: Encoding (one-hot/binary), state partitioning, FSM type (Moore/Mealy)
```

### Arbiter Pattern
```
Interfaces:
- Request/Grant pairs per master
- Shared resource interface
Key decisions: Arbitration policy, priority scheme, fairness
```

## Integration with Other Skills

- **rtl-coding-style**: This skill focuses on microarchitecture; rtl-coding-style focuses on coding style
- **verification-env**: Consider verification needs during microarchitecture design
- **verification-testplan**: Microarchitecture decisions affect testability

## Real-World Impact

**Good microarchitecture**:
- Clean interfaces → easy integration
- Consistent naming → faster debugging
- Clear partitioning → maintainable code
- Early CDC planning → reliable operation

**Poor microarchitecture**:
- Interface changes late in project → schedule slips
- Inconsistent naming → 2-3x debugging time
- Monolithic modules → hard to test, verify, reuse
- Unplanned CDC → field failures
