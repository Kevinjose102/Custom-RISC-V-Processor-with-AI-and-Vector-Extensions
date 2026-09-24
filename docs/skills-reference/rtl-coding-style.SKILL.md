---
name: rtl-coding-style
description: "RTL coding style guide for writing clean, maintainable Verilog/SystemVerilog. Use this skill whenever the user writes RTL code, asks for code review of hardware designs, wants coding style advice for Verilog/SystemVerilog, or when generating RTL — apply these rules automatically. Triggers include: 'RTL style', 'coding style', 'code review RTL', 'SystemVerilog style', 'Verilog convention', 'naming convention RTL', 'RTL best practice', module definition, signal naming, or any RTL code generation task."
---

# RTL Coding Style Guide

Apply these rules whenever writing, reviewing, or generating Verilog/SystemVerilog RTL code.

## 1. Indentation and Alignment

### Indentation
- **All indents must use 4 spaces.** Never use tabs.
- **Each sub code block must be indented one level.** For example, IO ports are indented inside `module`, logic is indented inside `always`, etc.
- By convention, `begin` stays on the same line; `end` gets a new line but is NOT indented; code between `begin`/`end` IS indented.

```systemverilog
module pipe (
    input           clk     ,
    input           rst_n   ,
    input           din0    ,
    output logic    dout0
);
    always_ff @(posedge clk or negedge rst_n) begin
        if(~rst_n) begin
            dout0 <= 1'b0;
        end
        else begin
            dout0 <= din0;
        end
    end
endmodule
```

### Alignment
Align variable names, operators, and keywords across lines with similar functions:

```systemverilog
assign res0  = din0  + din1    ;
assign res32 = din45 + din235  ;

input               out_ready   ,
output logic        out_valid   ,
output logic [31:0] out_payload ,
```

## 2. Variable Definition and Naming

- **Explicitly declare types** — do not rely on language inference.
  ```systemverilog
  // Good
  output logic            valid,
  output logic [31:0]     payload,
  parameter integer unsigned WIDTH = 32
  ```

- **Use the same prefix for related signals** (bus-like signals forming a function or protocol).
  ```systemverilog
  logic           in_vld  ;
  logic           in_rdy  ;
  logic [31:0]    in_data ;
  ```

- **Prefix vectors with `v_`** — a vector = group of independent signals of the same type.
  ```systemverilog
  logic [31:0] in_v_en    ;  // 32 independent enables → vector
  logic [31:0] in_data    ;  // 32 bits form ONE data → not a vector
  ```

- Use **meaningful names** and **appropriate abbreviations**.

## 3. Filelist Rules

1. **Keep the same prefix** for all files in an IP. The prefix should be a unique abbreviation.
   ```
   sc_bus_arbiter.sv
   sc_bus_decoder.sv
   sc_bus_buffer.sv
   ```

2. **Centralize macro definitions** in a define file at the start, with matching undefine file at the end:
   ```
   sc_bus_define.sv
   sc_bus_arbiter.sv
   sc_bus_decoder.sv
   sc_bus_buffer.sv
   sc_bus_undefine.sv
   ```

## 4. Module

- **Module name and file name must be the same.** One module per file.
- **File suffix must match syntax** — use `.sv` for SystemVerilog.
- **Module definition template:**

```systemverilog
module sc_cmn_vr_dec
    import scc_param_pkg::*;   // 1. imported package
#(
    parameter integer unsigned A = 1  // 2. parameters
)(
    input         clk    ,   // 3. IO
    output logic  data
);
    // 4. RTL code
endmodule
```

Keep brackets on separate lines for uniformity.

## 5. Parameter

```systemverilog
parameter integer unsigned    EXAMPLE1 = 1,
parameter logic [31:0]        EXAMPLE2 = 32'b0
```

- **Explicitly declare the data type.**
- **Use ALL CAPS** for parameter names.
- **One parameter per line.**
- **Check synthesizability** when using parameters for circuit assignment.

## 6. Data-type Parameter

Use `parameter type` to pass types to modules — this is **synthesizable**.

```systemverilog
module reg_slice #(
    parameter PLD_TYPE = logic
)(
    output logic    out_vld ,
    input  logic    out_rdy ,
    output PLD_TYPE out_pld ,
    input  logic    in_vld  ,
    output logic    in_rdy  ,
    input  PLD_TYPE in_pld
);
    assign out_vld = in_vld;
    assign in_rdy  = out_rdy;
    assign out_pld = in_pld;
endmodule
```

This allows one module to handle different payload types without modification.

## 7. Generate if/for

- **generate-if**: Select desired function via parameter.
- **generate-for**: Batch instantiation of modules with regularity.

Rules:
1. Loop variable must be declared with `genvar`.
2. Each `begin-end` block must have a **unique label**.
3. `generate-if` can be replaced by `generate-case`.

```systemverilog
genvar i;
generate for(i=0; i<4; i=i+1) begin:GPU_AW_RS
    reg_slice #(.FUNC_MODE(4'b0001), .PLD_TYPE(slv_aw_pack))
    u_rs_gpu_aw(
        .clk    (clk                ),
        .rst_n  (rst_n              ),
        .s_vld  (v_gpu_aw_vld   [i] ),
        .s_rdy  (v_gpu_aw_rdy   [i] ),
        .s_pld  (v_gpu_aw_pld   [i] ),
        .m_vld  (v_gpu_aw_vld_rs[i] ),
        .m_rdy  (v_gpu_aw_rdy_rs[i] ),
        .m_pld  (v_gpu_aw_pld_rs[i] )
    );
end
endgenerate
```

## 8. Structure (struct)

Use `typedef struct packed` to group related signals. Benefits: shorter code, better readability, lower maintenance.

```systemverilog
typedef struct packed {
    logic [AXI_AW_ID_WIDTH-1:0]   id    ;
    logic [AXI_AW_ADDR_WIDTH-1:0] addr  ;
    logic [AXI_AW_LEN_WIDTH-1:0]  len   ;
    logic [1:0]                   burst ;
    logic [3:0]                   qos   ;
} axi_aw_pack;
```

- Structs can be nested.
- Access fields: `aw_pld.qos`
- Assign as a whole: `aw_pld_new = aw_pld;`
- Reset: `aw_pld_buffer <= {$bits(axi_aw_pack){1'b0}};`

## 9. Macro

**Do not use macros unless absolutely necessary!**

- Prefer `parameter` / `localparam` for constants.
- Use a dedicated package file, imported before module IO definition.
- If macros are unavoidable: centralize defines at filelist start, undefines at end.
- Uncancelled macros **will** pollute other IPs.

## 10. Combinational Logic

- **`assign`** — for simple or symmetric logic:
  ```systemverilog
  assign handshake_done = req_vld && req_rdy;
  
  assign fix_arb = high_qos_req_en ? high_qos_req_pld  :
                   mid_qos_req_en  ? mid_qos_req_pld   :
                   low_qos_req_en  ? low_qos_req_pld   :
                                     {PLD_WIDTH{1'b0}} ;
  ```

- **`always_comb`** — for complex logic. Use `always_comb` instead of `always @(*)`.

Both produce the same synthesis result. `always_comb` can express all combinational logic with better readability.

## 11. Sequential Logic

Use **`always_ff`** for sequential logic. **Only use nonblocking assignments (`<=`).**

```systemverilog
// Asynchronous reset
always_ff @(posedge clk or negedge rst_n) begin
    if(~rst_n)
        data_d <= {DATA_WIDTH{1'b0}} ;
    else if(data_en)
        data_d <= data ;
end
```

- **Omit the last `else`** to enable automatic clock gating inference.
- **Synchronous reset**: omit `negedge rst_n` from sensitivity list.
- **No reset** on data path is acceptable for high-speed/low-area designs.

## 12. Clock and Reset

### Clock
- Name: `clk` (add functional suffix for multiple clocks: `clk_slc`, `clk_dmc`)
- Dynamic frequency switching must use dedicated glitch-free circuits (common IP).
- Never use `&` or `|` directly on clock signals — causes glitches.

### Reset
- Name: `rst_n` (low-active, add suffix for multiple resets: `rst_n_slc`, `rst_n_dmc`)
- Can be asynchronous or synchronous trigger.
- **Reset must follow the synchronous release principle.**

## Quick Checklist

| Rule | Check |
|------|-------|
| 4-space indentation, no tabs | ☐ |
| Aligned operators/names across similar lines | ☐ |
| Explicit type declarations | ☐ |
| Same prefix for related signals | ☐ |
| `v_` prefix for vector signals | ☐ |
| Module name == file name | ☐ |
| `.sv` suffix for SystemVerilog | ☐ |
| ALLCAPS parameters with explicit types | ☐ |
| `genvar` for generate loops, unique labels | ☐ |
| No macros (use parameters/packages instead) | ☐ |
| `always_comb` not `always @(*)` | ☐ |
| `always_ff` with nonblocking `<=` only | ☐ |
| Omit last else in `always_ff` for clock gating | ☐ |
| Synchronous reset release | ☐ |
