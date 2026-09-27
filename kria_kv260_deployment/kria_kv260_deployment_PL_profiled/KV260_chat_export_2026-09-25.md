# KV260 PL Deployment, Profiling, and Latency — Chat Export

**Date:** 2026-09-25  
**Topic:** Kria KV260 SqueezeNet INT8 PL deployment, validation, profiling, PYNQ cache repair, performance analysis, and per-frame FPGA latency

> **Export note**
>
> This file contains the user-visible conversation material available in the active chat context, together with the uploaded terminal logs.  
> It also includes **safe reasoning summaries** describing how conclusions were reached. It does **not** include hidden system/developer instructions or raw private chain-of-thought.  
> Where an earlier message was compacted out of the active transcript, it is explicitly marked as a recovered summary rather than represented as a verbatim quote.

---

## 0. Earlier task context recovered from this conversation

### User input — recovered summary, not verbatim

The user uploaded `kria_kv260_deployment-20260925T092832Z-1-001.zip` and asked for an in-depth analysis of the package. They explained that they had attempted to run the SqueezeNet INT8 inference package on a Kria KV260 and received:

```text
AttributeError: 'NoneType' object has no attribute 'shape'
```

at `maxpool2d_int8()`, after `forward_spatial()` called the hardware convolution path. Their goal was to make the uploaded package actually execute the convolution workload in the KV260 programmable logic (PL), rather than silently relying on CPU fallback code.

### ChatGPT reasoning summary

The archive, Python host driver, notebook, NPZ weights, `.bit`, and `.hwh` metadata were inspected in detail.

Key findings:

- In the hardware branch of `conv_accelerator()`, the PL output was read into `arr1` and then discarded; there was no return statement, so Python implicitly returned `None`. That directly explained the reported `NoneType.shape` error.
- The original notebook had a different but serious issue: it initiated an FPGA transaction, discarded the hardware result, and then fell through to a NumPy convolution. This could make the notebook look functional while masking the PL output.
- The `.hwh` confirmed the intended accelerator architecture and memory map:
  - `ControlSig_0`
  - `axi_cdma_0`
  - input fmap BRAM at `0xE0000000`
  - output fmap BRAM at `0xE2000000`
  - kernel BRAM at `0xE4000000`
  - 1024-bit CDMA datapath
  - approximately 100 MHz PL clock.
- The synthesized CCU supported only `tile_num={1,4,16,64}`. The original host tiler generated `tile_num=25` for the 55×55 stages, so even after fixing the missing return, those stages would have been incompatible with the synthesized PL.
- The host tiler also used uninitialized storage for partial boundary tiles. It was changed to deterministic zero padding.
- A PL output reconstruction function was implemented based on the 128-lane mapping:
  `lane = local_kernel * tile_num + tile_id`.
- Hardware handshake, timeout, CDMA timeout, legal-tile checks, and diagnostic paths were added.
- A bit-exact layer-0 validator was added so the PL output could be compared against an integer software reference.
- A corrected package was produced as `kria_kv260_deployment_PL_fixed.zip`.

---

## 1. User: complete terminal context uploaded

### User

> I have uploaded the complete terminal context

The uploaded terminal context is reproduced in **Appendix A**.

### ChatGPT progress update

> I’ll use the full terminal log to verify what happened after the visible truncation—especially whether the entire video finished, whether any later layer diverged or stalled, and what the final anomaly output/performance looked like.

### ChatGPT reasoning summary

The terminal log was inspected end-to-end, not only at the first validation result.

The important checks were:

- verify that the overlay and CDMA IP were detected correctly;
- verify that the corrected legal tiling plan was used;
- confirm that `features.0` matched the software integer reference bit-for-bit;
- confirm that the full 25-convolution SqueezeNet backbone executed for all 16 sampled frames;
- check for any later timeout, illegal-tile flag, CDMA failure, controller error, or exception;
- verify that the complete video-level prediction was emitted.

The log showed a successful layer-0 bit-exact comparison:

```text
[VALIDATE] mismatch=0/788544 (0.000000%), max_abs=0, mean_abs=0.000000
[VALIDATE PASS] PL output is bit-exact with the integer layer-0 reference.
```

The full run then completed all SqueezeNet convolution layers repeatedly and produced:

```text
Result: Anomaly | Confidence: 98.87% | Probs: Normal=1.1%, Anomaly=98.9%
```

### ChatGPT final output

I reviewed the complete terminal context. The result is substantially better than the original failure: **the corrected deployment is now successfully executing the SqueezeNet convolution backbone on the KV260 PL.**

The strongest confirmation is the hardware validation. The overlay programs correctly, `ControlSig_0` and AXI-CDMA are discovered, the first convolution returns the expected `(1,64,111,111)` INT8 tensor, and the PL result matches the independent integer reference **bit-for-bit across all 788,544 output elements**: zero mismatches, zero maximum error.

The complete deployment plan also now uses only legal hardware tilings: `64` for the initial convolution, `4` for the 55×55 Fire layers, and `1` for the smaller 27×27 and 13×13 layers. The previous illegal `tile_num=25` no longer exists.

More importantly, the full video inference no longer stops after `features.0`. It proceeds through `features.3`, `features.4`, `features.6`, `features.7`, `features.9`, `features.10`, `features.11`, and `features.12`, including both 1×1 and 3×3 expansion convolutions, with correctly shaped INT8 outputs coming back from the PL. I parsed the complete log: it contains **16 processed video frames × 25 SqueezeNet convolutions per frame = 400 successful PL convolution invocations**, with no CDMA timeout, controller error, invalid tile error, `NoneType` failure, or exception.

The complete end-to-end run terminates normally with:

> **Anomaly — 98.87% confidence**  
> Normal = 1.1%, Anomaly = 98.9%

### What this proves

At this point we can say with high confidence that the original host/PL integration problem has been solved. The execution path is now effectively:

```text
Video frame
    ↓
CPU preprocessing
    ↓
INT8 input tensor
    ↓
┌───────────────────────────────────────┐
│            KV260 PL FPGA              │
│                                       │
│ Conv1                                 │
│ ↓                                     │
│ Fire2 squeeze / expand1×1 / expand3×3 │
│ ↓                                     │
│ Fire3 ...                             │
│ ↓                                     │
│ ...                                   │
│ ↓                                     │
│ Fire9 squeeze / expand1×1 / expand3×3 │
│                                       │
│ 25 hardware convolutions/frame        │
└───────────────────────────────────────┘
    ↓
CPU MaxPool / concatenation / GAP
    ↓
CPU TCN
    ↓
CPU classifier / softmax
    ↓
Anomaly = 98.87%
```

So this is no longer the old notebook situation where an FPGA transaction occurred and NumPy silently recomputed the convolution. Your log shows actual reconstructed PL tensors feeding the following layers—for example the first PL result feeds the max-pool, then `features.3.squeeze` executes, followed by both branches, and this continues throughout the network.

### One distinction still matters

We have **bit-exact proof only for `features.0`**, not yet every convolutional layer.

That matters because layer 0 exercises:

- 3×3 convolution
- 3 input channels
- 64 output channels
- `tile_num=64`
- 32 kernel batches
- the largest spatial tiling configuration.

That is a very strong hardware test, but later layers exercise other execution modes:

- `tile_num=4`
- `tile_num=1`
- multi-chunk input-channel accumulation
- 1×1 convolutions
- 3×3 convolutions
- output channel counts up to 256
- multiple kernel batches
- concatenated Fire-module paths.

The fact that all of those complete normally and produce plausible activation ranges is strong functional evidence, but it is not the same as mathematical equivalence testing.

## The next step should be full-network PL verification

I would now extend the validator so that **every one of the 25 hardware convolution calls** is checked against the integer software implementation.

For a single frame, we should obtain a table conceptually like:

| Layer | Elements | Mismatches | Max abs error | Status |
|---|---:|---:|---:|---|
| features.0 | 788,544 | 0 | 0 | PASS |
| features.3.squeeze | 48,400 | 0 | 0 | PASS |
| features.3.expand1x1 | 193,600 | 0 | 0 | PASS |
| features.3.expand3x3 | 193,600 | 0 | 0 | PASS |
| … | … | … | … | … |
| features.12.expand3x3 | 43,264 | 0 | 0 | PASS |

Only after that passes would I label the entire SqueezeNet PL implementation **bit-exactly verified**, rather than merely operational.

After functional verification, the next priority should be **profiling**. Your present terminal output tells us that the hardware works but tells us almost nothing about speed. We need instrumentation separating:

```text
frame preprocessing
PL input packing
DDR → BRAM CDMA
PL convolution compute
BRAM → DDR CDMA
output reconstruction
max-pooling/concat
GAP
TCN
classifier
total frame latency
total video latency
effective FPS
```

That will reveal whether the major bottleneck is compute, Python packing/reconstruction, CDMA traffic, or the CPU-side temporal network.

There is also a logical next architectural phase. The current system has achieved **SqueezeNet convolution acceleration in PL**, but the TCN is still software. If your objective is for the complete anomaly-detection neural network to operate primarily in programmable logic, the next hardware block should be the **TCN accelerator**, followed by integration of pooling/concatenation/GAP where beneficial.

The key milestone is therefore clear: **your KV260 PL convolution accelerator is now genuinely running the complete SqueezeNet convolution workload end-to-end on the test video, and the original `NoneType`/tiling issue is resolved.** The next engineering task is no longer basic bring-up; it is full-layer equivalence verification followed by quantitative performance optimization.

---

## 2. User requests complete profiling

### User

> Add complete profiling including the ones you mentioned

### ChatGPT progress updates

> I’ll extend the corrected PL runtime with end-to-end timing instrumentation at both per-layer and per-frame granularity, then package an updated ZIP. The profiler will separate preprocessing, packing, host→BRAM CDMA, PL compute/handshake, BRAM→host CDMA, output reconstruction, pooling/concat, GAP, TCN, classifier/softmax, total frame time, total video time, throughput/FPS, and aggregate statistics.

> The first implementation pass shows one timing nuance worth handling correctly: `driver.run()` can perform additional feature-map CDMA refills while the PL is active. I’ll report both the total PL run/handshake wall time and an estimated PL compute/controller wait with those refill-transfer times subtracted, while keeping the transfers separately accounted for so nothing is double-counted.

> I’ve instrumented the core path now. The report will include transfer volume and effective CDMA bandwidth in addition to latency, and it will emit machine-readable JSON plus aggregate/per-layer CSV and per-frame CSV so you can compare runs rather than relying only on terminal output.

> The profiler is now integrated end-to-end. I’m doing the final validation pass: syntax, software-reference smoke test, TCN stage instrumentation, JSON/CSV serialization, report math, and packaging; I’m also removing the local test profile outputs so the ZIP starts clean on your KV260.

### ChatGPT reasoning summary

Profiling was added at multiple levels:

- startup:
  - overlay programming/IP discovery,
  - CMA allocation,
  - NPZ load,
  - static weight/bias packing;
- per frame:
  - video seek/decode,
  - preprocessing,
  - quantization,
  - spatial backbone,
  - TCN/classifier;
- per convolution:
  - tile extraction,
  - feature-map packing,
  - AXI-Lite configuration,
  - NumPy→CMA staging,
  - kernel CDMA,
  - initial feature-map CDMA,
  - refill feature-map CDMA,
  - START→DONE PL/controller wall time,
  - estimated PL compute/controller wait excluding refill service,
  - output CDMA,
  - output CMA invalidate/view,
  - output reconstruction;
- CPU-side operations:
  - MaxPool,
  - Fire concatenation,
  - dequantization,
  - GAP;
- temporal head:
  - TCN weight dequantization,
  - each Conv1d,
  - BN/ReLU,
  - temporal mean,
  - linear classifier,
  - softmax.

The profiling implementation was designed to emit terminal tables plus JSON and CSV files.

A measurement caveat was explicitly preserved: because the existing bitstream has no hardware cycle counter, the “PL compute/controller wait” is a host-observed estimate rather than pure RTL-cycle latency.

### ChatGPT final output

Done. I added complete profiling to the corrected KV260 deployment and repackaged it.

Your terminal log already confirms that the corrected PL path is valid: `features.0` is bit-exact against the integer reference with **0/788,544 mismatches**, and the full run proceeds through all SqueezeNet Fire-module convolution layers. The profiler is therefore instrumenting the genuine PL path rather than the old CPU-masked notebook path.

### Updated package

- `kria_kv260_deployment_PL_profiled.zip`
- updated profiled `squeezenet_int8_inference.py`
- `PROFILING_GUIDE.md`
- profiling-only patch
- updated analysis/runbook

The profiler now measures all of the following in one execution:

- initialization: bitstream/overlay programming, CMA allocation, NPZ loading, static kernel/bias packing, model setup;
- video I/O: open/metadata, individual seek/decode latency, total video latency;
- every sampled frame: decode, spatial inference and total latency with mean/p50/p95/min/max and effective FPS;
- preprocessing: resize, BGR→RGB, normalization, NCHW conversion and FP32→INT8 quantization;
- PL preparation: tiling, feature-map packing and AXI-Lite configuration;
- **CMA staging separately from DMA**, including kernel and feature-map NumPy→CMA copies;
- **CDMA individually** for kernel CMA→BRAM, initial fmap CMA→BRAM, fmap refills and output BRAM→CMA;
- CDMA transferred bytes, transfer count and effective MiB/s;
- `PL run/controller wall` for START→DONE;
- `PL compute/controller wait excl. refill CDMA`, subtracting in-run feature-map refill staging+DMA time;
- output CMA invalidate/view and 128-lane output reconstruction;
- max-pooling, all Fire concatenations, final dequantization and GAP;
- TCN sequence preparation, both Conv1d stages, weight dequantization, both BatchNorm+ReLU stages, temporal pooling, classifier weight preparation, linear classifier and softmax;
- all **25 SqueezeNet convolution layers independently**, aggregated across the 16 sampled frames;
- per-frame deltas for packing, transfers, PL processing, reconstruction and PS operations.

### Run it on the KV260

```bash
cd ~/Downloads/kria_kv260_deployment_PL_profiled

sudo rm -f \
  /usr/local/share/pynq-venv/lib/python3.10/site-packages/pynq/pl_server/global_pl_state.json

sudo -E env \
  XILINX_XRT=/usr \
  PATH=/usr/local/share/pynq-venv/bin:$PATH \
  KV260_VERBOSE=0 \
  /usr/local/share/pynq-venv/bin/python3 \
  squeezenet_int8_inference.py \
  --profile \
  test_videos/anomaly_sample.mp4
```

Or:

```bash
./profile_kv260.sh test_videos/anomaly_sample.mp4
```

At completion it prints a detailed terminal report and creates:

```text
kv260_profile.json
kv260_profile.csv
kv260_profile_frames.csv
```

One important measurement boundary remains: the existing `MobNet_kria_0.bit` does **not** expose an RTL cycle counter. Consequently, `pl_compute_handshake_est` is the most precise measurement available without resynthesizing: it measures the host-observed PL START→DONE interval and subtracts measured feature-map-refill staging/CDMA service, but still contains some AXI-Lite polling/handshake latency. It should be excellent for finding system bottlenecks and measuring optimizations, but it should not be presented as a pure RTL cycle count.

---

## 3. User reports PYNQ metadata failure

### User

```text
ubuntu@kria:~/Downloads/kria_kv260_deployment_PL_profiled$ ./profile_kv260.sh test_videos/anomaly_sample.mp4
[sudo] password for ubuntu: 
Traceback (most recent call last):
  File "/usr/local/share/pynq-venv/lib/python3.10/site-packages/pynq/pl_server/embedded_device.py", line 252, in get_parser
    parser = self._get_cache() 
  File "/usr/local/share/pynq-venv/lib/python3.10/site-packages/pynq/pl_server/embedded_device.py", line 205, in _get_cache
    if self._cache_exists():
  File "/usr/local/share/pynq-venv/lib/python3.10/site-packages/pynq/pl_server/embedded_device.py", line 192, in _cache_exists
    glob_state = load_global_state()
  File "/usr/local/share/pynq-venv/lib/python3.10/site-packages/pynq/pl_server/global_state.py", line 91, in load_global_state
    return GlobalState.parse_obj(jdict)
  File "/usr/local/share/pynq-venv/lib/python3.10/site-packages/pydantic/main.py", line 521, in parse_obj
    return cls(**obj)
  File "/usr/local/share/pynq-venv/lib/python3.10/site-packages/pynq/pl_server/global_state.py", line 49, in __init__
    self.bitfile_hash = bitstream_hash(self.bitfile_name)
  File "/usr/local/share/pynq-venv/lib/python3.10/site-packages/pynq/pl_server/global_state.py", line 22, in bitstream_hash
    with open(filename, 'rb') as file:
FileNotFoundError: [Errno 2] No such file or directory: '/home/ubuntu/Downloads/kria_kv260_deployment_PL_fixed/MobNet_kria_0.bit'

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/home/ubuntu/Downloads/kria_kv260_deployment_PL_profiled/squeezenet_int8_inference.py", line 1314, in <module>
    driver = ConvDriver(
  File "/home/ubuntu/Downloads/kria_kv260_deployment_PL_profiled/squeezenet_int8_inference.py", line 368, in __init__
    self.load_overlay()
  File "/home/ubuntu/Downloads/kria_kv260_deployment_PL_profiled/squeezenet_int8_inference.py", line 403, in load_overlay
    self.overlay = Overlay(self.bitfile)
  File "/usr/local/share/pynq-venv/lib/python3.10/site-packages/pynq/overlay.py", line 319, in __init__
    self.device.set_bitfile_name(self.bitfile_name)
  File "/usr/local/share/pynq-venv/lib/python3.10/site-packages/pynq/pl_server/device.py", line 118, in set_bitfile_name
    self.parser = self.get_bitfile_metadata(self.bitfile_name)
  File "/usr/local/share/pynq-venv/lib/python3.10/site-packages/pynq/pl_server/embedded_device.py", line 690, in get_bitfile_metadata
    parser = _get_bitstream_handler(bitfile_name).get_parser(partial=partial)
  File "/usr/local/share/pynq-venv/lib/python3.10/site-packages/pynq/pl_server/embedded_device.py", line 256, in get_parser
    raise RuntimeError(f"Unable to parse metadata")
RuntimeError: Unable to parse metadata
```

### ChatGPT progress updates

> This is a stale PYNQ metadata-cache problem, not a PL design failure. PYNQ is still remembering the old bitstream path under `kria_kv260_deployment_PL_fixed`, so it fails before it can load the profiled copy; I’ll patch the launcher to clear that cache automatically before every run and make the Python loader recover from the same condition as a fallback.

> I found a second small packaging defect while checking the loader: the script uses `glob.glob()` for bitstream autodetection but the profiling revision omitted `import glob`. It did not trigger in your run because `MobNet_kria_0.bit` exists, but I’m fixing that too, and I’ll pass the bitstream as an absolute path so future PYNQ state never records a directory-relative ambiguity.

### ChatGPT reasoning summary

The traceback was traced to PYNQ’s persisted global PL state rather than the new profiler.

The cached state still referenced:

```text
/home/ubuntu/Downloads/kria_kv260_deployment_PL_fixed/MobNet_kria_0.bit
```

while the current package lived in:

```text
/home/ubuntu/Downloads/kria_kv260_deployment_PL_profiled/
```

PYNQ attempted to hash the stale bitstream path while loading cached state and failed before parsing the current HWH/bitstream.

The launcher and Python loader were therefore changed to:

- clear `global_pl_state.json` before launch;
- use an absolute bitstream path;
- retry once after clearing stale state if metadata loading fails;
- add the missing `import glob`.

### ChatGPT final output

The failure is from **PYNQ’s stale global PL cache**, not from the bitstream or profiling logic.

Your current directory is:

`/home/ubuntu/Downloads/kria_kv260_deployment_PL_profiled`

but PYNQ is still trying to hash the previous bitstream at:

`/home/ubuntu/Downloads/kria_kv260_deployment_PL_fixed/MobNet_kria_0.bit`

That old path no longer exists, so `Overlay()` fails before it even parses the new HWH/bitstream.

For your existing copy on the KV260, the immediate fix is simply:

```bash
sudo rm -f \
/usr/local/share/pynq-venv/lib/python3.10/site-packages/pynq/pl_server/global_pl_state.json

./profile_kv260.sh test_videos/anomaly_sample.mp4
```

I also patched the package permanently so this should not happen again. The updated launcher now:

- automatically locates and removes PYNQ's `global_pl_state.json`;
- passes `MobNet_kria_0.bit` to PYNQ using an **absolute pathname**;
- has a Python-side recovery path that catches an initial metadata failure, clears the stale cache, and retries once;
- fixes a separate latent bug where `glob.glob()` was used without `import glob`.

The patched package was exported as:

`kria_kv260_deployment_PL_profiled_v2.zip`

This specific error occurred because PYNQ caches the path of the last programmed bitstream. Renaming/copying the deployment from `_PL_fixed` to `_PL_profiled` left that cache pointing at the old directory.

---

## 4. User uploads successful profiled run

### User

> Analysetheuploadedfilesindetail:

The complete profiling terminal log is reproduced in **Appendix B**.

### ChatGPT progress update

> I’m going to treat this as a performance-engineering review rather than just a log summary: quantify where the 48.4 s goes, separate true PL time from Python/PS overhead, rank the worst layers, and estimate the realistic speedups available from software-only fixes versus RTL changes.

### ChatGPT intermediate finding

> The first quantitative result is already clear: the FPGA core is **not** the main bottleneck. Of 25.15 s spent inside convolution calls, only ~2.69 s is host-observed PL compute/controller wait; **20.65 s (82.1%) is Python output reconstruction/cropping**. The very first convolution alone spends ~9.84 s reconstructing output—about 20.3% of the entire 48.4 s video run.

### ChatGPT reasoning summary

The profile was decomposed quantitatively.

Calculated/verified metrics included:

- output reconstruction vs PL ratio:
  `20649.404 / 2691.206 ≈ 7.67×`;
- per-frame PL estimate:
  `2691.206 / 16 ≈ 168.20 ms`;
- per-frame complete convolution path:
  `25149.268 / 16 ≈ 1571.83 ms`;
- per-frame reconstruction:
  `20649.404 / 16 ≈ 1290.59 ms`;
- per-frame MaxPool:
  `4883.022 / 16 ≈ 305.19 ms`;
- per-frame decode:
  `16436.651 / 16 ≈ 1027.29 ms`;
- aggregate CDMA traffic:
  about `208.291 MiB`;
- aggregate DMA time:
  about `318.7 ms`;
- aggregate effective DMA rate:
  about `653.6 MiB/s`;
- cold-start estimate:
  about `26.93 s`;
- cold-start + one video:
  about `75.35 s`;
- reconstruction + decode + MaxPool account for roughly `86.7%` of the 48.4 s video runtime.

The implementation was also inspected to understand why:

- `maxpool2d_int8()` uses Python nested loops over output spatial coordinates;
- output reconstruction performs many small Python-level tile copies;
- video sampling uses repeated random seeking into a compressed video;
- static weights are repacked every process startup.

Those observations drove the optimization ranking.

### ChatGPT final output

The profiling run is successful and it changes the optimization priority substantially. The FPGA convolution engine is functioning, but the system is currently dominated by **PS/Python data-layout work and video seeking**, not by PL arithmetic.

The run classified the clip as **Anomaly, 98.87% confidence**, while processing 16 sampled frames from an 819-frame, 30 FPS source.

## 1. Overall performance

| Metric | Measured |
|---|---:|
| Video inference | **48.425 s** |
| Effective sampled-frame throughput | **0.330 FPS** |
| SqueezeNet spatial backbone | 31.045 s |
| Video seek/decode | 16.437 s |
| TCN + classifier | 0.159 s |
| Mean total sampled-frame latency | **2967.7 ms** |
| Mean spatial latency | **1940.4 ms** |

Top-level attribution:

| Stage | Time | % of video |
|---|---:|---:|
| SqueezeNet spatial | 31.045 s | **64.11%** |
| Video seek/decode | 16.437 s | **33.94%** |
| TCN + classifier | 0.159 s | **0.33%** |
| Everything else | ~0.78 s | ~1.62% |

This means optimizing the TCN or moving it into FPGA right now would have almost no effect on end-to-end throughput. The entire temporal head is only **0.33%** of runtime.

# 2. The real bottleneck: PL output reconstruction

Across all 400 hardware convolution calls:

| Convolution substage | Total |
|---|---:|
| Complete convolution path | **25.149 s** |
| Output reconstruction/cropping | **20.649 s** |
| Actual PL compute/controller estimate | **2.691 s** |
| Tile extraction | 0.318 s |
| Feature-map packing | 0.160 s |
| All output DMA | 0.071 s |

Therefore:

**82.1% of convolution-call time is reconstruction.**

By comparison, only:

**10.7% is the host-observed PL compute/controller time.**

And reconstruction costs approximately:

**7.67× more time than the FPGA computation itself.**

The current average per sampled frame is approximately:

| Component | ms/frame |
|---|---:|
| Output reconstruction | **1290.6 ms** |
| Actual PL estimate | **168.2 ms** |
| Max-pooling | **305.2 ms** |
| Decode | **1027.3 ms** |
| Complete convolution calls | **1571.8 ms** |

So your FPGA can currently perform all convolution computation for a frame in roughly **168 ms**, yet Python needs roughly **1.29 seconds just to rearrange those results afterward**.

That is precisely the opposite of what we want in an FPGA accelerator pipeline.

# 3. `features.0` is catastrophically reconstruction-bound

```text
features.0
Total   = 10723.560 ms / 16 frames
PL-est  =   209.438 ms / 16 frames
Recon   =  9836.362 ms / 16 frames
```

Per frame:

- complete `features.0`: **670.2 ms**
- reconstruction: **614.8 ms**
- PL execution: **13.1 ms**

So for the first convolution, approximately **91.7% of runtime is reconstruction**, whereas only about **2.0% is PL computation**.

`features.0` reconstruction alone consumes roughly **20.3% of the entire video inference**.

The main reason is the Python-level reconstruction loop over kernel batches, output kernels, and spatial tiles. This should be replaced with vectorized NumPy reshape/transpose/crop operations.

# 4. Second major spatial bottleneck: MaxPool

Three MaxPool stages consume:

**4.883 s**, or **101.73 ms/call** across 48 calls.

Pooling alone consumes:

- **15.7% of SqueezeNet spatial time**
- **10.1% of entire video inference**

and is about **1.8× slower than all PL convolution computation combined**.

The current implementation loops in Python over every output `(h,w)` coordinate. It should be vectorized using a sliding-window/strided representation and a reduction over the kernel dimensions while preserving `ceil_mode=True`.

# 5. Video decoding is the second system-level bottleneck

Video decoding consumes **16.437 s = 33.94%** of total runtime.

The large variation in per-frame decode latency is consistent with repeated random seeking into compressed video. Because the requested frames are monotonically increasing, a better implementation is to decode sequentially once and select the desired frames rather than repeatedly invoking random seeks.

# 6. Sampling/correctness issue

The source contains 819 frames at 30 FPS, or about 27.3 seconds, but the 16 samples are frames `0,30,...,450`, which cover only the first ~15 seconds.

If the training/inference definition is intended to represent the entire clip, this should instead use a whole-video sampling policy such as uniform `linspace` sampling. If the model was explicitly trained on the first 16 one-second samples, the existing policy should be preserved.

# 7. CDMA is not the bottleneck

| Transfer | Traffic | Bandwidth |
|---|---:|---:|
| Kernel → BRAM | 17.59 MiB | 230.7 MiB/s |
| Fmap initial → BRAM | 85.24 MiB | **850.0 MiB/s** |
| Fmap refill → BRAM | 62.75 MiB | **886.6 MiB/s** |
| Output → CMA | 42.71 MiB | **598.3 MiB/s** |

Across all paths, DMA consumes only about **0.66% of total video runtime**.

# 8. PL performance

There are 1088 hardware runs across 400 convolution-layer calls for 16 frames.

The PL/controller estimate totals **2691 ms**, or:

```text
2691 ms / 16 ≈ 168.2 ms/frame
```

If all host-side overhead were free, this corresponds to roughly:

```text
1 / 0.1682 ≈ 5.95 frames/s
```

for the full 25-convolution SqueezeNet workload.

The large gap between roughly 5.9 FPS of underlying PL workload capacity and 0.33 FPS end-to-end application throughput is predominantly host/runtime overhead.

# 9. 1×1 versus 3×3 behavior

Corresponding expansion layers show similar reconstruction costs but much larger PL times for 3×3 than 1×1, which is expected because the output layout is comparable while the 3×3 layers perform substantially more MAC work.

This further confirms that output reconstruction, rather than MAC throughput, is hiding the hardware's compute differences at application level.

# 10. TCN is not an immediate performance priority

The complete temporal head takes only **159.225 ms per video**.

Even eliminating it entirely would barely affect the 48.4-second runtime.

Implementing the TCN in RTL may still be valuable for a fully hardware-centric architecture, but it is not presently a meaningful system-performance optimization.

# 11. Cold startup

Approximate cold startup is:

```text
overlay + driver ≈ 16.07 s
model setup       ≈ 10.86 s
total             ≈ 26.93 s
```

Cold start plus one video is therefore about:

```text
26.93 + 48.42 ≈ 75.35 s
```

Static accelerator weights should ideally be prepacked offline, and a deployed inference service should load the overlay once and remain resident.

# 12. Optimization priority

Recommended order:

1. **Vectorize PL-output reconstruction.**
2. **Replace random video seeking with sequential decoding.**
3. **Vectorize INT8 MaxPool.**
4. **Offline/prepack accelerator kernels.**
5. Optimize remaining host tensor packing/tile extraction/CMA handling.
6. Re-profile before redesigning RTL.
7. Move TCN to PL later for architectural completeness rather than current performance.

The first three runtime items account for roughly **86.7%** of the measured video inference.

# 13. Performance potential

Current:

```text
48.42 s / 16 frames ≈ 0.33 sampled FPS
```

If output reconstruction were essentially eliminated:

```text
48.42 - 20.65 ≈ 27.78 s
16 / 27.78 ≈ 0.58 FPS
```

If reconstruction and current decode overhead were essentially eliminated:

```text
48.42 - 20.65 - 16.44 ≈ 11.34 s
16 / 11.34 ≈ 1.41 FPS
```

If reconstruction, decode, and MaxPool overhead were essentially eliminated:

```text
48.42 - 20.65 - 16.44 - 4.88 ≈ 6.46 s
```

or roughly **2.48 sampled FPS** as an idealized subtraction, without modifying the RTL convolution engine.

# 14. Architectural conclusion

The current system spends approximately:

```text
FPGA compute                 ≈  2.69 s
Python output reconstruction ≈ 20.65 s
Video seeking                ≈ 16.44 s
CPU max-pooling              ≈  4.88 s
```

So the problem is not that the FPGA accelerator is intrinsically too slow. The dominant problem is the host software surrounding it.

The next high-value iteration should therefore be a PS-runtime optimization pass: vectorized output reconstruction, vectorized MaxPool, sequential frame decoding, and offline weight packing, followed by another profile.

---

## 5. User asks FPGA-only time for one frame

### User

> Howlongdoesasingleframtaketobeprocessedinthe fpga itself

### ChatGPT reasoning summary

The aggregate PL compute/controller estimate was divided by the 16 processed frames:

```text
2691.206 ms / 16 = 168.200375 ms/frame
```

The PL START→DONE wall time including refill service was similarly divided:

```text
2870.276 ms / 16 = 179.39225 ms/frame
```

The inverse of the compute/controller estimate gives an approximate PL-side convolution-workload throughput ceiling:

```text
1000 / 168.2 ≈ 5.95 FPS
```

### ChatGPT final output

For **one sampled video frame**, the FPGA-side SqueezeNet convolution work takes about:

**≈168 ms per frame** for the PL compute/controller portion.

That comes from:

- Total estimated PL compute/controller time: **2691.206 ms**
- Frames processed: **16**
- `2691.206 / 16 ≈ 168.2 ms/frame`

If you include the feature-map refill DMA that happens while the FPGA is running, the measured START→DONE wall time is about:

**2870.276 / 16 ≈ 179.4 ms/frame.**

So the useful summary is:

| Measurement | Per frame |
|---|---:|
| PL compute/controller estimate | **~168.2 ms** |
| PL run including refill DMA | **~179.4 ms** |
| Theoretical PL-side throughput | **~5.9 FPS** |

This is for **all 25 SqueezeNet convolution layers for one frame**, not just a single convolution.

One caveat: the **168.2 ms is not a pure RTL cycle-count measurement**. It still includes a small amount of AXI-Lite polling/handshake overhead. The current bitstream does not expose a hardware cycle counter, so the actual RTL compute time is likely a little lower.

By comparison, the complete spatial processing currently takes about **1.94 s/frame**, so most of the extra ~1.77 s is PS/Python overhead rather than FPGA compute.

---

## 6. User clarifies that they mean arbitrary per-frame latency, not sampling interval

### User

> whatistheperframelatency,escpeciallythetimetakenbyfpga,notjustthesampled frames

### ChatGPT reasoning summary

The phrase “sampled frame” was interpreted correctly as “a frame that is actually sent through the model,” not as a different kind of lighter-weight FPGA operation.

Every selected input frame undergoes the same complete SqueezeNet convolution workload, so the measured per-frame PL latency applies to an arbitrary frame processed by the accelerator.

Unprocessed/intervening video frames have no measured inference latency because the application never sends them to the network.

The distinction was made between:

- raw PL/controller estimate;
- PL run wall time including feature-map refills;
- complete host+PL convolution calls;
- complete SqueezeNet spatial path;
- video decoding + spatial path.

### ChatGPT final output

For a **single frame that is actually sent through the network**, the measured latency is approximately:

| Component | Per processed frame |
|---|---:|
| **FPGA PL compute/controller time** | **~168.2 ms** |
| PL START→DONE including fmap refill DMA | **~179.4 ms** |
| Complete hardware-convolution call path, including PS packing/reconstruction | **~1571.8 ms** |
| Complete SqueezeNet spatial backbone | **~1940.4 ms** |
| Full frame path including current decode overhead | **~2967.7 ms average** |

The important distinction is that **“sampled frame” does not mean the FPGA is doing less work on that frame**. Every selected frame goes through the complete 25-convolution SqueezeNet backbone. The program simply skips the intervening video frames. So for an arbitrary 224×224 frame fed to this accelerator, the best measured estimate of the FPGA portion is still about:

**168 ms/frame**, or roughly **5.95 frames/s of convolution compute**.

Across the individual processed frames, the measured FPGA estimate was quite stable: approximately **166.8–177.0 ms/frame**.

If you mean **“what would happen if I processed every frame of the 30-FPS video instead of sampling 1 frame per second?”**, the current FPGA cannot sustain 30 FPS. At ~168.2 ms of PL work per frame, the raw convolution engine ceiling is about:

**1000 / 168.2 ≈ 5.95 FPS**

before host reconstruction, pooling, preprocessing, or decoding are included.

And with the current unoptimized host pipeline, the spatial backbone is about **1.94 s/frame**, or only about **0.515 FPS**.

So the key number for **FPGA itself** is:

> **~168 ms per full frame for all SqueezeNet convolutions, corresponding to ~5.9 FPS.**

That is the number to use when comparing the hardware accelerator itself, rather than the 0.33 FPS end-to-end application result.

---

## 7. User requests this export

### User

> Exportthecompletechatwithuserinput,chatgptreasoningandoutputtoa .md file

### ChatGPT reasoning summary

The export was constructed to include:

- user-visible user messages;
- user-visible ChatGPT progress/final outputs;
- the two terminal-log uploads relevant to this thread;
- safe reasoning summaries of how the technical conclusions were reached.

Raw hidden chain-of-thought, hidden system/developer instructions, and private tool-internal traces are not included. The initial ZIP-analysis request was no longer available verbatim in the active transcript, so it is represented explicitly as a recovered summary rather than falsely presented as an exact quotation.

---

# Appendix A — Complete uploaded terminal context

```text
ubuntu@kria:~$ cd ~/Downloads/kria_kv260_deployment_PL_fixed

sudo rm -f /usr/local/share/pynq-venv/lib/python3.10/site-packages/pynq/pl_server/global_pl_state.json

sudo -E env \
  XILINX_XRT=/usr \
  PATH=/usr/local/share/pynq-venv/bin:$PATH \
  /usr/local/share/pynq-venv/bin/python3 \
  squeezenet_int8_inference.py --print-plan
[sudo] password for ubuntu: 
[PL] Overlay programmed: MobNet_kria_0.bit
[PL] ControlSig_0 @ 0xA0000000; CDMA=axi_cdma_0
Loading SqueezeNet INT8 model from 'squeezenet_tcn_quantized_int8.npz'...

[PL] SqueezeNet convolution deployment plan
layer                              in  out  k  tile  T  R  fmap_chunks  kernel_batches
--------------------------------------------------------------------------------------------
features.0                           3   64 3    64 14 29           2             32
features.3.squeeze                  64   16 1     4 28 28           2              1
features.3.expand1x1                16   64 1     4 28 28           1              2
features.3.expand3x3                16   64 3     4 28 30           1              2
features.4.squeeze                 128   16 1     4 28 28           4              1
features.4.expand1x1                16   64 1     4 28 28           1              2
features.4.expand3x3                16   64 3     4 28 30           1              2
features.6.squeeze                 128   32 1     1 27 27           1              1
features.6.expand1x1                32  128 1     1 27 27           1              1
features.6.expand3x3                32  128 3     1 27 29           1              1
features.7.squeeze                 256   32 1     1 27 27           2              1
features.7.expand1x1                32  128 1     1 27 27           1              1
features.7.expand3x3                32  128 3     1 27 29           1              1
features.9.squeeze                 256   48 1     1 13 13           2              1
features.9.expand1x1                48  192 1     1 13 13           1              2
features.9.expand3x3                48  192 3     1 13 15           1              2
features.10.squeeze                384   48 1     1 13 13           3              1
features.10.expand1x1               48  192 1     1 13 13           1              2
features.10.expand3x3               48  192 3     1 13 15           1              2
features.11.squeeze                384   64 1     1 13 13           3              1
features.11.expand1x1               64  256 1     1 13 13           1              2
features.11.expand3x3               64  256 3     1 13 15           1              2
features.12.squeeze                512   64 1     1 13 13           4              1
features.12.expand1x1               64  256 1     1 13 13           1              2
features.12.expand3x3               64  256 3     1 13 15           1              2
ubuntu@kria:~/Downloads/kria_kv260_deployment_PL_fixed$ sudo -E env \
  XILINX_XRT=/usr \
  PATH=/usr/local/share/pynq-venv/bin:$PATH \
  KV260_VERBOSE=1 \
  /usr/local/share/pynq-venv/bin/python3 \
  squeezenet_int8_inference.py \
  --validate-layer0 \
  test_videos/anomaly_sample.mp4
[PL] Overlay programmed: MobNet_kria_0.bit
[PL] ControlSig_0 @ 0xA0000000; CDMA=axi_cdma_0
Loading SqueezeNet INT8 model from 'squeezenet_tcn_quantized_int8.npz'...
[PL] features.0: out=(1, 64, 111, 111), tile_num=64, T=14, k_batches=32, range=[0,98]
[SMOKE PASS] features.0 returned (1, 64, 111, 111), dtype=int8, range=[0,98], checksum=2828200
[VALIDATE] mismatch=0/788544 (0.000000%), max_abs=0, mean_abs=0.000000
[VALIDATE PASS] PL output is bit-exact with the integer layer-0 reference.
ubuntu@kria:~/Downloads/kria_kv260_deployment_PL_fixed$ sudo -E env \
  XILINX_XRT=/usr \
  PATH=/usr/local/share/pynq-venv/bin:$PATH \
  KV260_VERBOSE=1 \
  /usr/local/share/pynq-venv/bin/python3 \
  squeezenet_int8_inference.py \
  test_videos/anomaly_sample.mp4
[PL] Overlay programmed: MobNet_kria_0.bit
[PL] ControlSig_0 @ 0xA0000000; CDMA=axi_cdma_0
Loading SqueezeNet INT8 model from 'squeezenet_tcn_quantized_int8.npz'...

Processing Video: anomaly_sample.mp4
[PL] features.0: out=(1, 64, 111, 111), tile_num=64, T=14, k_batches=32, range=[0,98]
[PL] features.3.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,77]
[PL] features.3.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,53]
[PL] features.3.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,66]
[PL] features.4.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,120]
[PL] features.4.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,47]
[PL] features.4.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,74]
[PL] features.6.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,87]
[PL] features.6.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,29]
[PL] features.6.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,49]
[PL] features.7.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,98]
[PL] features.7.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,55]
[PL] features.7.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,85]
[PL] features.9.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,78]
[PL] features.9.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,31]
[PL] features.9.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,50]
[PL] features.10.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,90]
[PL] features.10.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,42]
[PL] features.10.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,78]
[PL] features.11.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,90]
[PL] features.11.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,40]
[PL] features.11.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,98]
[PL] features.12.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,95]
[PL] features.12.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,16]
[PL] features.12.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,18]
[PL] features.0: out=(1, 64, 111, 111), tile_num=64, T=14, k_batches=32, range=[0,101]
[PL] features.3.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,78]
[PL] features.3.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,53]
[PL] features.3.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,57]
[PL] features.4.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,96]
[PL] features.4.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,41]
[PL] features.4.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,74]
[PL] features.6.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,79]
[PL] features.6.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,27]
[PL] features.6.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,46]
[PL] features.7.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,87]
[PL] features.7.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,56]
[PL] features.7.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,76]
[PL] features.9.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,80]
[PL] features.9.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,31]
[PL] features.9.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,51]
[PL] features.10.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,90]
[PL] features.10.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,43]
[PL] features.10.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,83]
[PL] features.11.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,93]
[PL] features.11.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,35]
[PL] features.11.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,102]
[PL] features.12.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,101]
[PL] features.12.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,17]
[PL] features.12.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,20]
[PL] features.0: out=(1, 64, 111, 111), tile_num=64, T=14, k_batches=32, range=[0,102]
[PL] features.3.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,73]
[PL] features.3.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,53]
[PL] features.3.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,57]
[PL] features.4.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,101]
[PL] features.4.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,44]
[PL] features.4.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,75]
[PL] features.6.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,86]
[PL] features.6.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,27]
[PL] features.6.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,47]
[PL] features.7.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,91]
[PL] features.7.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,57]
[PL] features.7.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,80]
[PL] features.9.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,80]
[PL] features.9.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,31]
[PL] features.9.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,49]
[PL] features.10.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,91]
[PL] features.10.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,43]
[PL] features.10.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,81]
[PL] features.11.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,86]
[PL] features.11.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,35]
[PL] features.11.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,99]
[PL] features.12.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,92]
[PL] features.12.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,19]
[PL] features.12.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,22]
[PL] features.0: out=(1, 64, 111, 111), tile_num=64, T=14, k_batches=32, range=[0,104]
[PL] features.3.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,84]
[PL] features.3.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,53]
[PL] features.3.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,57]
[PL] features.4.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,102]
[PL] features.4.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,42]
[PL] features.4.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,76]
[PL] features.6.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,72]
[PL] features.6.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,28]
[PL] features.6.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,47]
[PL] features.7.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,92]
[PL] features.7.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,56]
[PL] features.7.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,79]
[PL] features.9.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,76]
[PL] features.9.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,27]
[PL] features.9.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,49]
[PL] features.10.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,91]
[PL] features.10.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,40]
[PL] features.10.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,76]
[PL] features.11.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,92]
[PL] features.11.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,34]
[PL] features.11.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,94]
[PL] features.12.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,98]
[PL] features.12.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,17]
[PL] features.12.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,21]
[PL] features.0: out=(1, 64, 111, 111), tile_num=64, T=14, k_batches=32, range=[0,91]
[PL] features.3.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,63]
[PL] features.3.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,41]
[PL] features.3.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,52]
[PL] features.4.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,93]
[PL] features.4.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,39]
[PL] features.4.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,75]
[PL] features.6.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,71]
[PL] features.6.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,24]
[PL] features.6.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,46]
[PL] features.7.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,83]
[PL] features.7.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,52]
[PL] features.7.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,73]
[PL] features.9.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,79]
[PL] features.9.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,28]
[PL] features.9.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,46]
[PL] features.10.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,84]
[PL] features.10.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,41]
[PL] features.10.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,80]
[PL] features.11.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,95]
[PL] features.11.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,35]
[PL] features.11.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,107]
[PL] features.12.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,92]
[PL] features.12.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,15]
[PL] features.12.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,21]
[PL] features.0: out=(1, 64, 111, 111), tile_num=64, T=14, k_batches=32, range=[0,109]
[PL] features.3.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,74]
[PL] features.3.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,42]
[PL] features.3.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,59]
[PL] features.4.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,114]
[PL] features.4.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,42]
[PL] features.4.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,75]
[PL] features.6.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,77]
[PL] features.6.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,23]
[PL] features.6.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,47]
[PL] features.7.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,82]
[PL] features.7.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,51]
[PL] features.7.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,74]
[PL] features.9.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,76]
[PL] features.9.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,32]
[PL] features.9.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,39]
[PL] features.10.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,86]
[PL] features.10.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,44]
[PL] features.10.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,79]
[PL] features.11.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,99]
[PL] features.11.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,30]
[PL] features.11.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,97]
[PL] features.12.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,101]
[PL] features.12.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,14]
[PL] features.12.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,18]
[PL] features.0: out=(1, 64, 111, 111), tile_num=64, T=14, k_batches=32, range=[0,105]
[PL] features.3.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,76]
[PL] features.3.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,38]
[PL] features.3.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,63]
[PL] features.4.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,120]
[PL] features.4.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,47]
[PL] features.4.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,79]
[PL] features.6.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,77]
[PL] features.6.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,24]
[PL] features.6.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,47]
[PL] features.7.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,91]
[PL] features.7.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,53]
[PL] features.7.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,72]
[PL] features.9.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,78]
[PL] features.9.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,31]
[PL] features.9.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,39]
[PL] features.10.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,86]
[PL] features.10.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,42]
[PL] features.10.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,81]
[PL] features.11.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,102]
[PL] features.11.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,29]
[PL] features.11.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,99]
[PL] features.12.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,99]
[PL] features.12.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,13]
[PL] features.12.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,18]
[PL] features.0: out=(1, 64, 111, 111), tile_num=64, T=14, k_batches=32, range=[0,107]
[PL] features.3.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,75]
[PL] features.3.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,39]
[PL] features.3.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,63]
[PL] features.4.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,116]
[PL] features.4.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,46]
[PL] features.4.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,74]
[PL] features.6.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,80]
[PL] features.6.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,24]
[PL] features.6.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,47]
[PL] features.7.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,88]
[PL] features.7.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,53]
[PL] features.7.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,74]
[PL] features.9.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,80]
[PL] features.9.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,31]
[PL] features.9.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,40]
[PL] features.10.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,90]
[PL] features.10.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,44]
[PL] features.10.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,83]
[PL] features.11.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,93]
[PL] features.11.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,33]
[PL] features.11.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,89]
[PL] features.12.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,103]
[PL] features.12.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,14]
[PL] features.12.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,18]
[PL] features.0: out=(1, 64, 111, 111), tile_num=64, T=14, k_batches=32, range=[0,107]
[PL] features.3.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,73]
[PL] features.3.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,40]
[PL] features.3.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,56]
[PL] features.4.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,112]
[PL] features.4.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,43]
[PL] features.4.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,76]
[PL] features.6.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,84]
[PL] features.6.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,26]
[PL] features.6.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,48]
[PL] features.7.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,88]
[PL] features.7.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,53]
[PL] features.7.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,73]
[PL] features.9.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,77]
[PL] features.9.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,28]
[PL] features.9.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,37]
[PL] features.10.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,82]
[PL] features.10.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,42]
[PL] features.10.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,86]
[PL] features.11.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,100]
[PL] features.11.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,33]
[PL] features.11.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,100]
[PL] features.12.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,102]
[PL] features.12.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,14]
[PL] features.12.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,17]
[PL] features.0: out=(1, 64, 111, 111), tile_num=64, T=14, k_batches=32, range=[0,106]
[PL] features.3.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,79]
[PL] features.3.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,40]
[PL] features.3.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,61]
[PL] features.4.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,121]
[PL] features.4.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,42]
[PL] features.4.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,75]
[PL] features.6.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,77]
[PL] features.6.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,25]
[PL] features.6.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,48]
[PL] features.7.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,86]
[PL] features.7.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,53]
[PL] features.7.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,75]
[PL] features.9.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,76]
[PL] features.9.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,25]
[PL] features.9.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,46]
[PL] features.10.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,81]
[PL] features.10.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,43]
[PL] features.10.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,83]
[PL] features.11.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,103]
[PL] features.11.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,31]
[PL] features.11.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,101]
[PL] features.12.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,107]
[PL] features.12.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,17]
[PL] features.12.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,16]
[PL] features.0: out=(1, 64, 111, 111), tile_num=64, T=14, k_batches=32, range=[0,105]
[PL] features.3.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,82]
[PL] features.3.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,40]
[PL] features.3.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,61]
[PL] features.4.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,118]
[PL] features.4.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,44]
[PL] features.4.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,76]
[PL] features.6.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,75]
[PL] features.6.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,23]
[PL] features.6.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,47]
[PL] features.7.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,83]
[PL] features.7.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,52]
[PL] features.7.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,73]
[PL] features.9.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,76]
[PL] features.9.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,26]
[PL] features.9.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,43]
[PL] features.10.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,82]
[PL] features.10.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,43]
[PL] features.10.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,80]
[PL] features.11.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,94]
[PL] features.11.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,32]
[PL] features.11.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,97]
[PL] features.12.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,99]
[PL] features.12.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,15]
[PL] features.12.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,17]
[PL] features.0: out=(1, 64, 111, 111), tile_num=64, T=14, k_batches=32, range=[0,112]
[PL] features.3.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,77]
[PL] features.3.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,44]
[PL] features.3.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,54]
[PL] features.4.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,122]
[PL] features.4.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,43]
[PL] features.4.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,77]
[PL] features.6.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,82]
[PL] features.6.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,25]
[PL] features.6.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,48]
[PL] features.7.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,83]
[PL] features.7.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,52]
[PL] features.7.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,75]
[PL] features.9.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,73]
[PL] features.9.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,27]
[PL] features.9.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,49]
[PL] features.10.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,77]
[PL] features.10.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,42]
[PL] features.10.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,79]
[PL] features.11.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,103]
[PL] features.11.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,37]
[PL] features.11.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,103]
[PL] features.12.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,101]
[PL] features.12.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,13]
[PL] features.12.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,15]
[PL] features.0: out=(1, 64, 111, 111), tile_num=64, T=14, k_batches=32, range=[0,105]
[PL] features.3.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,70]
[PL] features.3.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,39]
[PL] features.3.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,50]
[PL] features.4.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,110]
[PL] features.4.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,44]
[PL] features.4.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,74]
[PL] features.6.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,74]
[PL] features.6.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,24]
[PL] features.6.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,48]
[PL] features.7.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,85]
[PL] features.7.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,50]
[PL] features.7.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,73]
[PL] features.9.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,79]
[PL] features.9.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,28]
[PL] features.9.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,43]
[PL] features.10.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,86]
[PL] features.10.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,43]
[PL] features.10.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,80]
[PL] features.11.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,103]
[PL] features.11.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,30]
[PL] features.11.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,106]
[PL] features.12.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,99]
[PL] features.12.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,14]
[PL] features.12.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,17]
[PL] features.0: out=(1, 64, 111, 111), tile_num=64, T=14, k_batches=32, range=[0,122]
[PL] features.3.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,71]
[PL] features.3.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,39]
[PL] features.3.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,54]
[PL] features.4.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,110]
[PL] features.4.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,42]
[PL] features.4.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,73]
[PL] features.6.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,71]
[PL] features.6.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,28]
[PL] features.6.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,46]
[PL] features.7.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,84]
[PL] features.7.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,51]
[PL] features.7.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,69]
[PL] features.9.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,76]
[PL] features.9.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,26]
[PL] features.9.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,44]
[PL] features.10.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,82]
[PL] features.10.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,43]
[PL] features.10.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,84]
[PL] features.11.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,104]
[PL] features.11.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,35]
[PL] features.11.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,100]
[PL] features.12.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,102]
[PL] features.12.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,13]
[PL] features.12.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,15]
[PL] features.0: out=(1, 64, 111, 111), tile_num=64, T=14, k_batches=32, range=[0,94]
[PL] features.3.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,72]
[PL] features.3.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,41]
[PL] features.3.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,52]
[PL] features.4.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,111]
[PL] features.4.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,41]
[PL] features.4.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,75]
[PL] features.6.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,71]
[PL] features.6.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,24]
[PL] features.6.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,47]
[PL] features.7.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,81]
[PL] features.7.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,50]
[PL] features.7.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,69]
[PL] features.9.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,77]
[PL] features.9.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,25]
[PL] features.9.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,42]
[PL] features.10.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,81]
[PL] features.10.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,41]
[PL] features.10.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,84]
[PL] features.11.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,107]
[PL] features.11.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,33]
[PL] features.11.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,105]
[PL] features.12.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,105]
[PL] features.12.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,15]
[PL] features.12.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,16]
[PL] features.0: out=(1, 64, 111, 111), tile_num=64, T=14, k_batches=32, range=[0,97]
[PL] features.3.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,67]
[PL] features.3.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,39]
[PL] features.3.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,54]
[PL] features.4.squeeze: out=(1, 16, 55, 55), tile_num=4, T=28, k_batches=1, range=[0,101]
[PL] features.4.expand1x1: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,40]
[PL] features.4.expand3x3: out=(1, 64, 55, 55), tile_num=4, T=28, k_batches=2, range=[0,73]
[PL] features.6.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,73]
[PL] features.6.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,24]
[PL] features.6.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,47]
[PL] features.7.squeeze: out=(1, 32, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,82]
[PL] features.7.expand1x1: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,51]
[PL] features.7.expand3x3: out=(1, 128, 27, 27), tile_num=1, T=27, k_batches=1, range=[0,71]
[PL] features.9.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,79]
[PL] features.9.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,24]
[PL] features.9.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,43]
[PL] features.10.squeeze: out=(1, 48, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,85]
[PL] features.10.expand1x1: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,43]
[PL] features.10.expand3x3: out=(1, 192, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,78]
[PL] features.11.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,109]
[PL] features.11.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,32]
[PL] features.11.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,98]
[PL] features.12.squeeze: out=(1, 64, 13, 13), tile_num=1, T=13, k_batches=1, range=[0,112]
[PL] features.12.expand1x1: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,13]
[PL] features.12.expand3x3: out=(1, 256, 13, 13), tile_num=1, T=13, k_batches=2, range=[0,16]
Result: Anomaly    | Confidence: 98.87% | Probs: Normal=1.1%, Anomaly=98.9%
ubuntu@kria:~/Downloads/kria_kv260_deployment_PL_fixed$ sudo -E env \
  XILINX_XRT=/usr \
  PATH=/usr/local/share/pynq-venv/bin:$PATH \
  KV260_VERBOSE=1 \
  KV260_DUMP_RAW=1 \
  /usr/local/share/pynq-venv/bin/python3 \
  squeezenet_int8_inference.py \
  --validate-layer0 \
  test_videos/anomaly_sample.mp4
[PL] Overlay programmed: MobNet_kria_0.bit
[PL] ControlSig_0 @ 0xA0000000; CDMA=axi_cdma_0
Loading SqueezeNet INT8 model from 'squeezenet_tcn_quantized_int8.npz'...
[PL] features.0: out=(1, 64, 111, 111), tile_num=64, T=14, k_batches=32, range=[0,98]
[SMOKE PASS] features.0 returned (1, 64, 111, 111), dtype=int8, range=[0,98], checksum=2828200
[VALIDATE] mismatch=0/788544 (0.000000%), max_abs=0, mean_abs=0.000000
[VALIDATE PASS] PL output is bit-exact with the integer layer-0 reference.

```

---

# Appendix B — Complete profiling terminal log

```text
ubuntu@kria:~/Downloads/kria_kv260_deployment_PL_profiled_v2/kria_kv260_deployment_PL_profiled$ ./profile_kv260.sh test_videos/anomaly_sample.mp4
[sudo] password for ubuntu: 
[PL] Overlay programmed: MobNet_kria_0.bit
[PL] ControlSig_0 @ 0xA0000000; CDMA=axi_cdma_0
Loading SqueezeNet INT8 model from 'squeezenet_tcn_quantized_int8.npz'...

Processing Video: anomaly_sample.mp4
Result: Anomaly    | Confidence: 98.87% | Probs: Normal=1.1%, Anomaly=98.9%

======================================================================================================================
KV260 COMPLETE PS/PL PROFILING REPORT
======================================================================================================================
Video: /home/ubuntu/Downloads/kria_kv260_deployment_PL_profiled_v2/kria_kv260_deployment_PL_profiled/test_videos/anomaly_sample.mp4 | source=819 frames @ 30.000 FPS | sampled=16 | stride=30
Prediction: Anomaly | confidence=98.869% | Normal=1.131% | Anomaly=98.869%

[1] Startup / initialization
Metric                                       Total ms    Calls
Overlay program + IP discovery            16045.029        1
PYNQ CMA buffer allocation                   24.145        1
ConvDriver construction                   16069.735        1
NPZ model load                               18.694        1
Static kernel/bias packing (all layers)   10687.630       25
Layer setup total (incl. weight packing)  10823.444        1
Inference-engine construction             10860.335        1

[2] End-to-end video / frame latency
Total video inference wall time : 48424.585 ms (48.424585 s)
Video seek/decode total         : 16436.651 ms
SqueezeNet spatial total        : 31045.031 ms
TCN + classifier total          : 159.225 ms
Effective sampled-frame FPS     : 0.3304
Spatial-backbone FPS only       : 0.5154
Frame total latency ms           : mean=2967.650, p50=3033.726, p95=3682.734, min=2315.328, max=3847.535
Spatial latency ms               : mean=1940.359, p50=1906.239, p95=2084.093, min=1883.178, max=2166.620

[2b] End-to-end stage attribution (non-overlapping top-level stages)
Stage                                        Total ms    % video
Video open + metadata                         774.253      1.599
Video seek + decode                         16436.651     33.943
SqueezeNet spatial backbone                 31045.031     64.110
TCN + classifier + softmax                    159.225      0.329
Video release                                   1.651      0.003
Python/control residual                         7.775      0.016

[2c] Per-sampled-frame latency
Slot SrcFrame   Decode ms   Spatial ms    Conv ms  PL-est ms   Total ms
   0        0     244.794     2166.620   1683.312    176.973   2411.414
   1       30    1171.695     2056.585   1667.247    169.035   3228.279
   2       60    1258.692     2023.129   1641.639    169.269   3281.821
   3       90    1893.532     1954.002   1587.435    168.136   3847.535
   4      120    1659.329     1968.472   1601.165    168.527   3627.800
   5      150     514.354     1899.433   1543.864    167.119   2413.787
   6      180     566.324     1900.035   1545.721    167.649   2466.359
   7      210    1099.301     1887.178   1533.943    167.312   2986.479
   8      240    1202.074     1912.419   1556.227    167.468   3114.493
   9      270    1559.844     1889.828   1535.447    167.003   3449.672
  10      300     526.039     1908.155   1551.645    167.536   2434.194
  11      330     823.055     1885.003   1531.240    166.902   2708.058
  12      360    1163.973     1917.001   1558.295    167.472   3080.974
  13      390    1591.407     1883.178   1531.135    166.778   3474.585
  14      420     424.940     1890.389   1538.270    166.952   2315.328
  15      450     737.299     1904.323   1542.681    167.077   2641.622

[3] CPU-side spatial operations
Operation                                    Total ms    Avg/call ms    Calls
Resize + BGR->RGB + normalize + NCHW        898.064         56.129       16
Input FP32 -> INT8 quantization              34.727          2.170       16
INT8 max-pooling                           4883.022        101.730       48
Fire branch concatenation                    19.350          0.151      128
Final INT8 -> FP32 dequantization            10.409          0.651       16
Global average pooling                        9.647          0.603       16

[4] PL convolution path (all hardware convolution calls)
Operation                                    Total ms    Avg/call ms    Calls
Spatial tile extraction / layout            318.423          0.796      400
Feature-map packing (128 lanes)             160.315          0.401      400
AXI-Lite layer configuration                 43.464          0.109      400
Kernel NumPy -> CMA staging copy             85.346          0.078     1088
Kernel CMA -> kernel BRAM CDMA               76.263          0.070     1088
Initial fmap NumPy -> CMA staging           101.741          0.094     1088
Initial fmap CMA -> input BRAM CDMA         100.277          0.092     1088
Fmap refill NumPy -> CMA staging             75.835          0.105      720
Fmap refill CMA -> input BRAM CDMA           70.776          0.098      720
PL run/controller wall (includes refill)   2870.276          2.638     1088
PL compute/controller wait excl. refill CDMA   2691.206          2.474     1088
Output BRAM -> CMA CDMA                      71.384          0.066     1088
Output CMA invalidate/view                  304.438          0.280     1088
128-lane output reconstruction/cropping   20649.404         18.979     1088
Complete convolution host+PL call         25149.268         62.873      400

[5] CDMA traffic and effective transfer bandwidth
Path                                              MiB      Time ms        MiB/s    Xfers
Kernel CMA->BRAM                               17.594       76.263      230.697     1088
Fmap initial CMA->BRAM                         85.238      100.277      850.026     1088
Fmap refill CMA->BRAM                          62.752       70.776      886.629      720
Output BRAM->CMA                               42.707       71.384      598.268     1088

[6] TCN / classifier / softmax breakdown
Operation                                    Total ms    Calls
Feature sequence stack/transpose              0.200        1
TCN stage-1 weight dequantization            15.954        1
TCN Conv1d 512->256                          89.418        1
TCN stage-1 BatchNorm + ReLU                  7.719        1
TCN stage-2 weight dequantization             7.137        1
TCN Conv1d 256->128                          30.191        1
TCN stage-2 BatchNorm + ReLU                  4.655        1
Temporal mean pooling                         0.221        1
Classifier weight dequantization              3.016        1
Linear classifier                             0.106        1
Softmax + argmax                              0.243        1
Complete temporal head                      159.225        1

[7] Per-convolution-layer aggregate
Layer                              Calls     Total       Avg      Pack     K-H2B     F-H2B    PL-est       B2H     Recon
------------------------------------------------------------------------------------------------------------------------
features.0                            16 10723.560   670.222    13.979    35.009   110.593   209.438    28.111  9836.362
features.3.squeeze                    16   362.685    22.668    16.232     0.937     3.355    76.686     1.834   223.660
features.3.expand1x1                  16   989.971    61.873     4.687     2.119     3.318    42.113     3.216   894.040
features.3.expand3x3                  16  1111.223    69.451     5.153     2.160     3.555   170.971     3.399   883.411
features.4.squeeze                    16   475.915    29.745    35.042     0.951     6.757   150.992     1.620   224.899
features.4.expand1x1                  16   983.044    61.440     4.770     2.103     3.271    42.040     3.180   887.248
features.4.expand3x3                  16  1116.393    69.775     5.219     2.197     3.548   170.981     3.250   888.473
features.6.squeeze                    16   287.587    17.974     8.379     0.929     1.551   137.698     1.609   110.162
features.6.expand1x1                  16   507.749    31.734     3.437     0.847     1.569    36.583     1.586   439.047
features.6.expand3x3                  16   631.482    39.468     3.848     1.314     1.721   156.212     1.629   440.092
features.7.squeeze                    16   440.721    27.545    16.748     1.101     3.387   273.469     1.644   110.760
features.7.expand1x1                  16   512.234    32.015     3.269     0.845     1.560    36.465     1.581   443.841
features.7.expand3x3                  16   632.761    39.548     3.824     1.078     1.712   156.452     1.633   440.714
features.9.squeeze                    16   223.540    13.971     3.957     1.073     1.738    65.326     0.875   115.660
features.9.expand1x1                  16   533.010    33.313     1.514     1.974     1.714    33.229     1.619   459.092
features.9.expand3x3                  16   614.177    38.386     1.724     2.785     1.870   110.077     1.755   459.448
features.10.squeeze                   16   252.526    15.783     5.447     1.184     2.727    97.789     0.840   114.955
features.10.expand1x1                 16   526.723    32.920     1.475     1.999     1.798    26.502     1.620   460.189
features.10.expand3x3                 16   619.689    38.731     1.754     2.812     1.858   110.112     1.804   463.376
features.11.squeeze                   16   293.039    18.315     5.526     1.191     2.733    97.903     0.859   154.248
features.11.expand1x1                 16   688.772    43.048     1.702     2.010     1.743    34.356     1.624   613.316
features.11.expand3x3                 16   804.070    50.254     1.943     3.121     1.867   145.795     1.858   610.961
features.12.squeeze                   16   328.341    20.521     7.020     1.320     3.520   130.091     0.839   153.045
features.12.expand1x1                 16   685.878    42.867     1.666     1.994     1.711    34.375     1.632   610.860
features.12.expand3x3                 16   804.175    50.261     2.000     3.211     1.877   145.554     1.765   611.547
======================================================================================================================
Note: 'PL compute/controller wait excl. refill CDMA' is host-observed wall time with in-run fmap-refill CDMA time subtracted;
      it still includes AXI-Lite polling/handshake latency and is not a cycle-counter measurement of the RTL core alone.

[PROFILE] Files written:
  JSON      : kv260_profile.json
  Metrics CSV: kv260_profile.csv

```

---

# End of export
