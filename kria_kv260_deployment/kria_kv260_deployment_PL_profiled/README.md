# SqueezeNet 1.1 + TCN INT8 — KV260 PL-fixed deployment

This directory is a corrected deployment package for the supplied `MobNet_kria_0.bit/.hwh` KV260 accelerator.

The original package had two blocking host/software defects:

- the hardware branch read PL output into `arr1` but never reconstructed or returned it, causing the reported `NoneType.shape` exception;
- the host tiler generated `tile_num=25` for the 55×55 SqueezeNet stages, while the synthesized CCU in the HWH supports only `1, 4, 16, 64`.

The corrected `squeezenet_int8_inference.py` reconstructs real output-BRAM data, uses only legal tilings, checks the CCU invalid-tile status, bounds PL/CDMA polling with timeouts, and hardens the feature-map handshake. The original Python is retained as `squeezenet_int8_inference_original.py`.

Read **`ANALYSIS_AND_RUNBOOK.md`** before running full inference.

## Recommended bring-up

```bash
cd ~/Downloads/kria_kv260_deployment_PL_fixed

sudo rm -f /usr/local/share/pynq-venv/lib/python3.10/site-packages/pynq/pl_server/global_pl_state.json

sudo -E env XILINX_XRT=/usr PATH=/usr/local/share/pynq-venv/bin:$PATH \
  /usr/local/share/pynq-venv/bin/python3 \
  squeezenet_int8_inference.py --print-plan

sudo -E env XILINX_XRT=/usr PATH=/usr/local/share/pynq-venv/bin:$PATH KV260_VERBOSE=1 \
  /usr/local/share/pynq-venv/bin/python3 \
  squeezenet_int8_inference.py --validate-layer0 test_videos/anomaly_sample.mp4
```

Only after `[VALIDATE PASS]`, run:

```bash
sudo -E env XILINX_XRT=/usr PATH=/usr/local/share/pynq-venv/bin:$PATH KV260_VERBOSE=1 \
  /usr/local/share/pynq-venv/bin/python3 \
  squeezenet_int8_inference.py test_videos/anomaly_sample.mp4
```

The CLI does not display GUI windows, so `xhost`, `DISPLAY`, and `XAUTHORITY` are unnecessary.

## Notebook

`squeezenet_anomaly_detection_kria.ipynb` now imports the corrected PL implementation. The uploaded notebook is retained as `squeezenet_anomaly_detection_kria_original_CPU_masked.ipynb` because its hardware path discarded PL output and then recomputed convolutions on the CPU.

## Scope

SqueezeNet **Conv2d** layers are intended to execute in PL. MaxPool, concatenation, GAP, TCN, classifier, and softmax remain PS/NumPy operations. This is a PS+PL pipeline rather than a fully-PL network.

## Complete profiling

Use `--profile` on a full video run. For timing runs, keep `KV260_VERBOSE=0` so terminal I/O does not perturb scheduling unnecessarily:

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

The profiler reports and exports:

- overlay programming, CMA-buffer allocation, NPZ loading, model setup, and static kernel/bias packing;
- video open/metadata, random seek/decode, total video wall time, per-sampled-frame latency, mean/p50/p95/min/max, effective FPS, and per-frame stage deltas (packing/CDMA/PL/reconstruction/CPU ops);
- preprocessing and input quantization;
- per-convolution tiling and 128-lane feature-map packing;
- NumPy-to-CMA staging separately from AXI-CDMA transfer time;
- kernel CMA→BRAM, initial/refill feature-map CMA→BRAM, and output BRAM→CMA bytes, transfer counts, transfer time, and effective MiB/s;
- AXI-Lite configuration;
- PL controller/run wall time and an estimated compute/controller wait with in-run fmap-refill service time removed;
- output CMA invalidation/view and NCHW output reconstruction/cropping;
- max-pooling, Fire concatenation, final dequantization, and GAP;
- TCN stage-1 and stage-2 weight dequantization, Conv1d, BatchNorm+ReLU, temporal mean pooling, classifier preparation/linear operation, and softmax;
- aggregate per-layer timing for all 25 SqueezeNet hardware convolution calls;
- machine-readable `kv260_profile.json`, `kv260_profile.csv`, and `kv260_profile_frames.csv`.

You can override output paths using `--profile-json`, `--profile-csv`, and `--profile-frames-csv`.

The existing bitstream has no RTL cycle counter/performance-counter interface. Therefore `PL compute/controller wait excl. refill CDMA` is a host-observed timing estimate: it still includes AXI-Lite polling/handshake latency. Exact core-only cycle counts require adding hardware counters to the RTL and rebuilding the bitstream.


## PYNQ stale-cache recovery

`profile_kv260.sh` now removes PYNQ's `global_pl_state.json` before launch and passes the bitstream by absolute path. This prevents a copied/renamed deployment directory from failing because PYNQ cached the previous bitstream pathname. The Python overlay loader also catches an initial metadata-parse failure, removes the cache, and retries once.
