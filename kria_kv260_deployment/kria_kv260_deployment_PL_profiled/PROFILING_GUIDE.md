# KV260 SqueezeNet+TCN complete profiling guide

## Run

For a clean timing run, first do one normal untimed inference as a warm-up. Then run:

```bash
cd ~/Downloads/kria_kv260_deployment_PL_fixed

sudo -E env \
  XILINX_XRT=/usr \
  PATH=/usr/local/share/pynq-venv/bin:$PATH \
  KV260_VERBOSE=0 \
  /usr/local/share/pynq-venv/bin/python3 \
  squeezenet_int8_inference.py \
  --profile \
  test_videos/anomaly_sample.mp4
```

Or simply:

```bash
./profile_kv260.sh test_videos/anomaly_sample.mp4
```

Do not set `KV260_DUMP_RAW=1` during benchmarking because `.npy` file I/O is intentionally diagnostic overhead.

## What is timed

### Video / end-to-end
- video open + metadata query;
- random seek + decode for each sampled source frame;
- SqueezeNet spatial latency for every sampled frame;
- complete TCN/classifier/softmax latency;
- complete video inference wall time;
- mean, p50, p95, min and max sampled-frame latency;
- effective sampled-frame FPS and spatial-backbone-only FPS.

### CPU/PS spatial work
- resize + BGR→RGB + normalization + NCHW conversion;
- FP32→INT8 input quantization;
- max-pooling;
- Fire branch concatenation;
- final INT8→FP32 dequantization;
- global average pooling.

### Each PL convolution
- tile extraction/layout;
- 128-lane feature-map packing;
- AXI-Lite layer configuration;
- kernel NumPy→CMA staging;
- kernel CMA→BRAM CDMA;
- initial feature-map NumPy→CMA staging;
- initial feature-map CMA→BRAM CDMA;
- in-run feature-map refill staging and CDMA;
- START/DONE controller-run wall time;
- estimated PL compute/controller wait after subtracting in-run refill service;
- output BRAM→CMA CDMA;
- CMA invalidate/view creation;
- 128-lane output reconstruction and boundary cropping;
- complete host+PL convolution call.

The report also aggregates all of the above per SqueezeNet layer across all sampled frames.

### CDMA bandwidth
For kernel H2B, initial fmap H2B, refill fmap H2B and output B2H, the profiler records:
- total transferred bytes;
- number of transfers;
- total transfer time;
- effective MiB/s.

CMA staging copies are kept separate so the CDMA result is not polluted by NumPy→CMA copy time.

### TCN temporal head
- sequence stack/transpose;
- stage-1 INT8 weight dequantization;
- Conv1d 512→256;
- BatchNorm + ReLU;
- stage-2 INT8 weight dequantization;
- Conv1d 256→128;
- BatchNorm + ReLU;
- temporal mean pooling;
- classifier weight dequantization;
- linear classifier;
- softmax + argmax;
- complete temporal-head latency.

## Output files

`--profile` writes:

- `kv260_profile.json` — complete structured result;
- `kv260_profile.csv` — aggregate and per-layer metrics (`seconds`, `milliseconds`, `count`, `bytes`, `MiB_per_s`);
- `kv260_profile_frames.csv` — one row per sampled frame including decode/spatial/total latency and per-frame deltas for packing, staging, CDMA, PL wait, reconstruction and CPU spatial operations.

Custom paths:

```bash
python3 squeezenet_int8_inference.py VIDEO.mp4 --profile \
  --profile-json run1.json \
  --profile-csv run1_metrics.csv \
  --profile-frames-csv run1_frames.csv
```

## Important hardware-timing limitation

The supplied bitstream exposes no dedicated RTL performance counter or accelerator cycle counter. `pl_run_wall` is the host-observed START→DONE transaction and includes refill servicing. `pl_compute_handshake_est` subtracts measured in-run fmap-refill staging+CDMA service, but still includes AXI-Lite polling and software/handshake latency. It is therefore an excellent system-level bottleneck metric, but not a pure cycle-accurate measurement of the convolution RTL. Exact core-only cycles require adding counters to the PL and rebuilding the bitstream.

## Recommended measurement discipline

Use the same bitstream, clocks, video, sampling policy, and system load for comparisons. Warm up once before recording results. Prefer `KV260_VERBOSE=0`. Record board temperature/clock state separately if you are comparing long runs or optimization revisions.


## PYNQ stale-cache recovery

`profile_kv260.sh` now removes PYNQ's `global_pl_state.json` before launch and passes the bitstream by absolute path. This prevents a copied/renamed deployment directory from failing because PYNQ cached the previous bitstream pathname. The Python overlay loader also catches an initial metadata-parse failure, removes the cache, and retries once.
