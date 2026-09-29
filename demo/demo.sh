#!/bin/bash
# One-command demo: build a benchmark, run it on the modified Shakti C-Class,
# and print baseline vs custom-instruction cycle counts.
#
# Usage (from anywhere):   bash demo.sh relu      (fast, PRELU6)
#                          bash demo.sh conv0     (first conv, PFMA)
#                          bash demo.sh dw        (depthwise, PFMA)
#                          bash demo.sh bench     (pointwise, PFMA - slow)
#
# Needs the already-built simulator in ~/projects/c-class/bin/out (no rebuild).

K=${1:-relu}
CC=~/projects/c-class
cd "$CC" || exit 1
[ -f "bench/$K.c" ] || { echo "bench/$K.c not found"; exit 1; }

echo "=== [1/3] Compiling bench/$K.c with RISC-V GCC ==="
riscv64-unknown-elf-gcc -march=rv64imafdc -mabi=lp64 -O2 -mno-relax -ffreestanding -static -mcmodel=medany \
  -nostdlib -nostartfiles -I verification/riscv-tests/env/p -I verification/riscv-tests/isa/macros/scalar \
  -T verification/riscv-tests/env/p/link.ld bench/bench_wrap.S "bench/$K.c" -o bin/bench.elf 2>/dev/null \
  || { echo "compile failed"; exit 1; }
elf2hex 8 4194304 bin/bench.elf 2147483648 > bin/code.mem

N=$(riscv64-unknown-elf-objdump -d bin/bench.elf | grep -ciE '\.insn|0x5b|unknown')
echo "    custom-2 (0x5B) instructions in the program: $N"

echo "=== [2/3] Running on the modified Shakti C-Class (Verilator) ==="
cd bin
START=$(date +%s)
rm -f rtl.dump
./out +rtldump > /dev/null 2>&1 &
PID=$!
# The simulator keeps running after the program ends, so stop it as soon as
# the program writes its pass/fail code to tohost (0x80001000).
for i in $(seq 1 900); do
  sleep 1
  grep -qE "mem 0x0*80001000 +0x" rtl.dump 2>/dev/null && break
done
sleep 1; kill $PID 2>/dev/null; wait $PID 2>/dev/null
echo "    simulation took $(( $(date +%s) - START )) s"

echo "=== [3/3] Results (read from the chip's mcycle / minstret counters) ==="
python3 - "$K" <<'EOF'
import re, subprocess, sys
kernel = sys.argv[1]
stores = {}
pat = re.compile(r'mem 0x([0-9a-fA-F]+)\s+0x([0-9a-fA-F]+)')
with open('rtl.dump') as f:
    for line in f:
        if 'mem 0x' in line:
            m = pat.search(line)
            if m:
                stores[int(m.group(1), 16)] = int(m.group(2), 16)

addr = size = None
for line in subprocess.run(['riscv64-unknown-elf-nm', '-S', 'bench.elf'],
                           capture_output=True, text=True).stdout.splitlines():
    p = line.split()
    if len(p) == 4 and p[3] == 'results':
        addr, size = int(p[0], 16), int(p[1], 16)
if addr is None:
    sys.exit("results[] not found in bench.elf")

vals = [stores.get(addr + 8 * i) for i in range(size // 8)]
print(f"\n  Kernel: {kernel}    raw results[] = {vals}")
if any(v is None for v in vals) or not vals or not vals[0]:
    sys.exit("  some results missing in rtl.dump (did the run finish?)")

# relu/dw/conv0 store cycles only: [baseline, custom, ...]
# bench stores pairs: [base cycles, base instr, custom cycles, custom instr]
pairs = (kernel == 'bench' and len(vals) % 2 == 0)
runs = [(vals[i], vals[i + 1]) for i in range(0, len(vals), 2)] if pairs \
       else [(v, None) for v in vals]
names = ['Normal RISC-V code'] + ['With custom instruction'] * (len(runs) - 1)
if len(runs) == 3:
    names[1:] = ['Custom (kernel only)', 'Custom (incl. data copy)']
base_c = runs[0][0]
print(f"  {'Version':28s} {'Cycles':>12s} {'Instructions':>14s} {'Speedup':>9s}")
print("  " + "-" * 66)
for n, (c, i) in zip(names, runs):
    ins = f"{i:14,d}" if i is not None else f"{'-':>14s}"
    print(f"  {n:28s} {c:12,d} {ins} {base_c / c:8.2f}x")

tohost = stores.get(0x80001000)
ok = tohost == 1
print(f"\n  Outputs identical (bit-exact): {'YES' if ok else 'NO'}   "
      f"tohost = {tohost} -> {'PASS' if ok else 'FAIL'}\n")
EOF
