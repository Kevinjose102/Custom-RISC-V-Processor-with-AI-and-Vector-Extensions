# AI-Accelerated SqueezeNet 1.1 + TCN Video Anomaly Detection
## Kria KV260 FPGA Hardware Deployment Package

This self-contained directory contains all necessary files for deploying the **SqueezeNet 1.1 + TCN INT8** video anomaly detection pipeline onto the **Xilinx Kria KV260 Vision AI Starter Kit** using the `ConvDriver` AXI-CDMA hardware accelerator.

---

## 📁 Package Manifest

| File / Folder | Purpose |
| :--- | :--- |
| **`squeezenet_anomaly_detection_kria.ipynb`** | Interactive Jupyter Notebook with real-time video HUD widget for Kria KV260. |
| **`squeezenet_int8_inference.py`** | Standalone Python inference script (CLI-compatible, runs on board or host). |
| **`squeezenet_tcn_quantized_int8.npz`** | 220-key hardware-aligned INT8 weights, INT32 biases, and 15-bit hardware scale registers. |
| **`test_videos/`** | Contains verification video clips:<br/>• `anomaly_sample.mp4` (Physical altercation/assault anomaly)<br/>• `normal_sample.mp4` (Normal pedestrian flow) |
| **`requirements.txt`** | Python dependencies (NumPy, OpenCV, Pillow, ipywidgets). |
| **`README.md`** | This setup & deployment guide. |

---

## ⚡ Hardware Memory Mapping

The hardware accelerator IP communicates with the Kria KV260 Processing System (PS) via AXI-CDMA and BRAM:

| Buffer / IP Interface | Base Address | Width | Description |
| :--- | :--- | :--- | :--- |
| **`FMAP_IN_BRAM_ADDR`** | `0xE0000000` | 1024-bit (128 bytes) | Input feature map CDMA BRAM |
| **`FMAP_OUT_BRAM_ADDR`** | `0xE2000000` | 1024-bit (128 bytes) | Output feature map CDMA BRAM |
| **`KERNEL_BRAM_ADDR`** | `0xE4000000` | 1024-bit (128 bytes) | Packed INT8 weights & INT32 biases |
| **`AXI CDMA 0`** | `axi_cdma_0` | 32-bit AXI Lite | High-speed DMA controller |
| **`ControlSig_0`** | `ControlSig_0` | 32-bit AXI Lite | Control registers (`_R_START`, `_R_GLOBALSCALE`, etc.) |

---

## 🚀 How to Deploy on Kria KV260

### Step 1: Copy this Folder to Kria KV260
Transfer this directory to your Kria KV260 board via `scp`:
```bash
scp -r kria_kv260_deployment ubuntu@<KRIA_IP_ADDRESS>:~/
```
*(Replace `<KRIA_IP_ADDRESS>` with the IP of your Kria board, e.g., `192.168.1.100`)*

### Step 2: Ensure Bitstream Files Are Present
Place your FPGA bitstream files in this deployment directory:
* `MobNet_kria_0.bit`
* `MobNet_kria_0.hwh`

*(If your bitstream has a different name, such as `MobNet256_8.bit`, `squeezenet_int8_inference.py` automatically detects any `.bit` file in the folder, or you can rename it to `MobNet_kria_0.bit`)*

### Step 3: Run Inference

#### Option A: Interactive Jupyter Notebook (Recommended)
1. Open your browser on your PC and access Jupyter on the Kria:
   ```
   http://<KRIA_IP_ADDRESS>:9090
   ```
2. Open `squeezenet_anomaly_detection_kria.ipynb`.
3. Run all cells sequentially.
4. Cell 5 will process `test_videos/anomaly_sample.mp4` and display the real-time HUD with detection results.

#### Option B: Terminal / Command Line
SSH into the Kria board and run:
```bash
cd ~/kria_kv260_deployment
python3 squeezenet_int8_inference.py test_videos/anomaly_sample.mp4
```

Expected output:
```
Loading SqueezeNet INT8 model from 'squeezenet_tcn_quantized_int8.npz'...
Processing Video: anomaly_sample.mp4
Result: Anomaly    | Confidence: 98.84% | Probs: Normal=1.2%, Anomaly=98.8%
```

To test the normal baseline video:
```bash
python3 squeezenet_int8_inference.py test_videos/normal_sample.mp4
```

Expected output:
```
Processing Video: normal_sample.mp4
Result: Normal     | Confidence: 63.24% | Probs: Normal=63.2%, Anomaly=36.8%
```
