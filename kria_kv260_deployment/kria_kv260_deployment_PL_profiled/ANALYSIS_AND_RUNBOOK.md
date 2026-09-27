# KV260 PL Deployment Analysis and Fix Runbook

## Executive finding

The uploaded package contains a valid KV260 bitstream/HWH pair and a SqueezeNet+TCN host stack, but the original host software cannot perform genuine end-to-end SqueezeNet convolution inference from PL as written.

The immediate crash is deterministic: in `squeezenet_int8_inference.py`, the PYNQ/hardware branch of `conv_accelerator()` reads the output BRAM into `arr1` but never reconstructs it and never returns a tensor. Python therefore returns `None`; `forward_spatial()` passes that into `maxpool2d_int8()`, which fails at `x.shape`.

A second independent incompatibility appears after fixing the missing return: the original automatic tiler generates `tile_num=25` for the 55x55 Fire layers. The synthesized HWH for `CCU_0` explicitly contains only `tile_num_1=1`, `tile_num_4=4`, `tile_num_16=16`, and `tile_num_64=64`, plus a `tile_num_not_right` output. The original Python never checks that status bit.

The fixed host script in this package addresses both issues and adds bounded PL/CDMA handshaking and first-layer PL-vs-reference validation.

## What is actually in the ZIP

The package contains the KV260 bitstream (`MobNet_kria_0.bit`), hardware handoff (`MobNet_kria_0.hwh`), SqueezeNet/TCN INT8 NPZ, CLI and notebook host code, and two test videos. It does **not** contain the Vivado project, RTL sources, IP source files, synthesis reports, implementation reports, timing reports, or testbenches. Therefore the PL can be deployed and exercised, but the RTL cannot be repaired/resynthesized from this ZIP alone.

The bitstream identifies `MobNet_Engine_wrapper`, Vivado 2024.2, target `xck26-sfvc784-2LV-c` (the K26 device used by KV260). The HWH contains 128 multiplier lanes and 1024-bit input/output/kernel BRAM datapaths.

## HWH-confirmed memory map

| Function | Address range | Notes |
|---|---:|---|
| ControlSig_0 | `0xA0000000-0xA000FFFF` | AXI-Lite control/status |
| axi_cdma_0 | `0xA0010000-0xA001FFFF` | AXI CDMA, 32-bit addresses, 1024-bit M_AXI |
| Input feature-map BRAM | `0xE0000000-0xE001FFFF` | 1024 x 1024-bit words |
| Output feature-map BRAM | `0xE2000000-0xE201FFFF` | 1024 x 1024-bit words |
| Kernel/bias BRAM | `0xE4000000-0xE401FFFF` | 1024 x 1024-bit words |

The Python constants in the uploaded script agree with this map.

## Original software defects

1. **Fatal missing return/reconstruction in hardware mode.** `arr1` is read from PL and then discarded; `convoluted_image` remains `None`.
2. **The notebook hides the hardware defect.** It performs the PL transaction, discards `arr1`, then always recomputes the convolution on the CPU NumPy path and returns that CPU tensor. A successful notebook result is therefore not proof that SqueezeNet convolution results came from PL.
3. **Illegal 25-tile geometry.** The original 55x55 tiling chooses a 5x5 grid (`tile_num=25`), but this synthesized CCU supports only 1, 4, 16, and 64.
4. **Boundary tiles used `np.empty`.** Partial boundary tiles could contain uninitialized bytes outside the copied region. The fixed script zero-fills them.
5. **Unbounded polling.** CDMA and accelerator loops had no timeout, so a PL/controller error could hang Python indefinitely.
6. **Handshake race.** While `channel_is_incomplete` remained high, the original loop could increment the feature-map batch index and resend again before PL deasserted the request. The fixed version holds `then_complete_it` until the request is consumed.
7. **`tile_num_not_right` was ignored.** The fixed version raises a specific error if the CCU asserts it.
8. **32-bit CDMA addressing was not checked.** The fixed version rejects CMA buffers above 4 GiB because this synthesized CDMA has a 32-bit address width.
9. **The software fallback used `np.round`.** The fixed reference uses integer Q1.15 multiply + `2^14` rounding bias + arithmetic shift, which matches the hardware requantizer more closely.

## Fixed tiling plan

The fixed tiler restricts square grids to the legal CCU geometries. It chooses the smallest legal grid whose receptive-field tile is no larger than 32x32, and it crops reconstructed boundary outputs.

| Network region | Original problematic behavior | Fixed PL geometry |
|---|---|---|
| First 224x224 conv | 8x8 grid | 8x8 grid (`tile_num=64`) |
| 55x55 Fire 3/4 | 5x5 grid (`25`, illegal) | 2x2 grid (`tile_num=4`) |
| 27x27 Fire 6/7 | 1x1 | 1x1 (`tile_num=1`) |
| 13x13 Fire 9-12 | 1x1 | 1x1 (`tile_num=1`) |

The maximum packed feature-map, kernel, and output read depths remain below the 1024-word buffers in the HWH.

## Output reconstruction used by the fix

The host packer and HWH Fmap router both organize the 128 lanes as contiguous groups of `tile_num` lanes per output kernel. Within a group, the lane offset is `tile_id`. The output BRAM has one 128-byte word per local output-pixel index. The fixed script therefore maps:

`lane = local_kernel * tile_num + tile_id`

and reshapes each lane's `T*T` values to the tile's local `T x T` output before copying it to the global NCHW tensor. Boundary regions beyond the true output size are cropped.

This mapping is strongly supported by the packer and the HWH Fmap router constants, but the uploaded ZIP has no RTL/testbench source that would allow offline bit-exact proof. For that reason, the fixed script includes `--validate-layer0` so the KV260 itself can validate the mapping against an integer CPU reference before a full video run.

## Recommended KV260 execution sequence

The CLI does not open a GUI window, so `xhost`, `DISPLAY`, and `XAUTHORITY` are not required for this script.

First copy/extract this fixed directory onto the board, then run:

```bash
cd ~/Downloads/kria_kv260_deployment_PL_fixed

sudo rm -f /usr/local/share/pynq-venv/lib/python3.10/site-packages/pynq/pl_server/global_pl_state.json

sudo -E env \
  XILINX_XRT=/usr \
  PATH=/usr/local/share/pynq-venv/bin:$PATH \
  /usr/local/share/pynq-venv/bin/python3 \
  squeezenet_int8_inference.py --print-plan
```

Then validate only the first hardware convolution:

```bash
sudo -E env \
  XILINX_XRT=/usr \
  PATH=/usr/local/share/pynq-venv/bin:$PATH \
  KV260_VERBOSE=1 \
  /usr/local/share/pynq-venv/bin/python3 \
  squeezenet_int8_inference.py --validate-layer0 test_videos/anomaly_sample.mp4
```

A healthy first stage should report a PL tensor with shape `(1, 64, 111, 111)` and then `[VALIDATE PASS]`. Do not proceed to full inference if validation reports mismatches; the script saves `diagnostics_layer0_pl.npy` and `diagnostics_layer0_ref.npy`. Set `KV260_DUMP_RAW=1` to additionally save raw `[T*T,128]` BRAM reads for lane-layout diagnosis.

After layer-0 validation passes, run the full video:

```bash
sudo -E env \
  XILINX_XRT=/usr \
  PATH=/usr/local/share/pynq-venv/bin:$PATH \
  KV260_VERBOSE=1 \
  /usr/local/share/pynq-venv/bin/python3 \
  squeezenet_int8_inference.py test_videos/anomaly_sample.mp4
```

Then repeat with `test_videos/normal_sample.mp4`.

## What “PL inference” means in this package

With the fixed script, all SqueezeNet `Conv2d` operations are intended to execute in the programmable logic and their actual output BRAM data is returned to the network. Max-pooling, Fire-module concatenation, global average pooling, TCN Conv1d/BatchNorm/ReLU, classifier, and softmax still execute on the Cortex-A53/NumPy side. This is therefore a PS+PL co-design, not a fully-PL SqueezeNet+TCN pipeline.

## Validation status

The fixed Python compiles successfully and its host/software path has been executed locally: first-layer output has shape `(1,64,111,111)`, and a complete SqueezeNet spatial forward pass returns a finite 512-element feature vector. The hardware-specific path cannot be executed in this analysis environment because it does not contain a KV260/PYNQ FPGA device. Hardware correctness must therefore be established with `--validate-layer0` on your board before treating full-video predictions as valid.

## Complete profiling mode

The corrected runtime now has a low-overhead `time.perf_counter_ns()` profiler covering the complete PS/PL path. Run the final measurement with verbose per-layer printing disabled:

```bash
sudo -E env \
  XILINX_XRT=/usr \
  PATH=/usr/local/share/pynq-venv/bin:$PATH \
  KV260_VERBOSE=0 \
  /usr/local/share/pynq-venv/bin/python3 \
  squeezenet_int8_inference.py \
  --profile \
  test_videos/anomaly_sample.mp4
```

The terminal report contains seven groups: startup/initialization; end-to-end video and per-frame latency; top-level stage attribution; CPU spatial operations; detailed PL convolution path; CDMA traffic/effective bandwidth; TCN/classifier/softmax; and a per-convolution-layer aggregate table.

Three files are written by default:

- `kv260_profile.json`: complete structured metrics, per-layer counters/times, frame records, video metadata, and prediction;
- `kv260_profile.csv`: aggregate and per-layer metrics including seconds, milliseconds, counts, bytes, and effective MiB/s;
- `kv260_profile_frames.csv`: sampled-frame index, original source-frame index, decode status, decode/spatial/total latency, plus per-frame deltas for preprocessing, quantization, packing, CMA staging, each CDMA direction, PL run/estimated compute wait, output reconstruction, pooling, concatenation, dequantization, and GAP.

For transfer profiling, host staging and CDMA are deliberately separated. `kernel_cma_stage` / `fmap_cma_stage_*` measure NumPy-to-CMA copies; `cdma_*` measures CDMA register programming, transfer completion polling, and the actual CMA↔BRAM transaction. Output BRAM→CMA CDMA is likewise separated from CMA cache invalidation/view creation and final 128-lane output reconstruction.

`pl_run_wall` is the observed wall time inside the START/DONE transaction and includes any in-run feature-map refill service. `pl_compute_handshake_est` subtracts the measured refill staging+CDMA service from that wall time. It is the best available software-side estimate with the supplied bitstream, but it is **not** a pure RTL cycle count because AXI-Lite polling/handshake latency remains. Exact accelerator-core cycles require adding PL performance counters and resynthesizing.

For stable comparisons, run one untimed warm-up inference first, then run the profiled command under the same clock, thermal, and system-load conditions. Do not use `KV260_DUMP_RAW=1` during benchmarking because file I/O intentionally adds diagnostic overhead.

## Hardware validation observed on KV260

The supplied terminal context confirms that `--validate-layer0` passed bit-exactly on the board: 0 mismatches across 788,544 outputs for `features.0`. The subsequent full anomaly-video run successfully traversed all 25 convolution calls per sampled frame through the SqueezeNet backbone and returned an anomaly prediction. Profiling should therefore be run on this corrected path rather than on the original CPU-masked notebook.


## PYNQ stale-cache recovery

`profile_kv260.sh` now removes PYNQ's `global_pl_state.json` before launch and passes the bitstream by absolute path. This prevents a copied/renamed deployment directory from failing because PYNQ cached the previous bitstream pathname. The Python overlay loader also catches an initial metadata-parse failure, removes the cache, and retries once.
