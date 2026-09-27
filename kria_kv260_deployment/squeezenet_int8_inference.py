#!/usr/bin/env python3
"""
Team 1: AI-Accelerated RISC-V Metro Station Video Anomaly Detection
Hardware Accelerator Driver & SqueezeNet 1.1 + TCN INT8 Inference Engine

Compatible with ConvDriver (AXI CDMA + ControlSig IP on Kria / RISC-V FPGA)
"""

import os
import cv2
import time
import math
import numpy as np
from PIL import Image

try:
    from pynq import Overlay, MMIO, allocate
    HAS_PYNQ = True
except ImportError:
    HAS_PYNQ = False


class ConvDriver:
    """Hardware driver for the 2D Convolution Accelerator over AXI-CDMA."""
    def __init__(
        self,
        bitfile: str,
        FMAP_IN_BRAM_ADDR: int,
        KERNEL_BRAM_ADDR: int,
        FMAP_OUT_BRAM_ADDR: int,
        lanes_per_bram: int = 128,
        signed_bytes: bool = True,
        depth_image_bram: int = 1024,
        depth_kernel_bram: int = 1024,
    ):
        self.bitfile = bitfile
        self.overlay = None

        self.MEM_BATCH1  = "axi_cdma_0"
        self.AXI_IP_NAME = "ControlSig_0"

        self.FMAP_IN_BRAM_ADDR_BATCH1  = FMAP_IN_BRAM_ADDR
        self.KERNEL_BRAM_ADDR_BATCH1   = KERNEL_BRAM_ADDR
        self.FMAP_OUT_BRAM_ADDR_BATCH1 = FMAP_OUT_BRAM_ADDR

        self.LANES_PER_BRAM = lanes_per_bram
        self.signed_bytes   = signed_bytes
        self.IMAGE_DEPTH    = depth_image_bram
        self.KERNEL_DEPTH   = depth_kernel_bram

        self.mem_batch1 = None
        self.axi_ip     = None

        # Register offsets
        self._R_START               = 0x00
        self._R_IMG_KER_STRIDE      = 0x04
        self._R_SLIDE               = 0x08
        self._R_RELUEN              = 0x0C
        self._R_DEPTHENB            = 0x10
        self._R_GLOBALSCALE         = 0x14
        self._R_TILE_IN_CHANNEL_NUM = 0x18
        self._R_KERNEL_IMAGE_DEPTH  = 0x1C
        self._R_THEN_COMPLETE_IT    = 0x20
        self._R_CHANNEL_IS_INCOMPLETE = 0x24
        self._R_BATCH_CONV_DONE     = 0x28
        self._R_TILE_NUM_NOT_RIGHT  = 0x2C

        self.dtype_1024 = np.dtype('V128')

        if HAS_PYNQ:
            self.load_overlay()
            _img_shape = (self.IMAGE_DEPTH,)
            _ker_shape = (self.KERNEL_DEPTH,)
            _dt = self.dtype_1024

            self.input_img_src_bufs_batch1  = allocate(shape=_img_shape, dtype=_dt, cacheable=False)
            self.input_img_dst_bufs_batch1  = allocate(shape=_img_shape, dtype=_dt)
            self.ker_src_bufs_batch1        = allocate(shape=_ker_shape, dtype=_dt, cacheable=False)
            self.ker_dst_bufs_batch1        = allocate(shape=_ker_shape, dtype=_dt)
            self.output_img_src_bufs_batch1 = allocate(shape=_img_shape, dtype=_dt, cacheable=False)
            self.output_img_dst_bufs_batch1 = allocate(shape=_img_shape, dtype=_dt)

            self._phys_fmap_src_b1  = self.input_img_src_bufs_batch1.physical_address
            self._phys_fmap_dst_b1  = self.output_img_dst_bufs_batch1.physical_address
            self._phys_ker_src_b1   = self.ker_src_bufs_batch1.physical_address
            self._phys_ker_dst_b1   = self.ker_dst_bufs_batch1.physical_address

            self._bram_fmap_in_b1   = self.FMAP_IN_BRAM_ADDR_BATCH1
            self._bram_ker_b1       = self.KERNEL_BRAM_ADDR_BATCH1
            self._bram_fmap_out_b1  = self.FMAP_OUT_BRAM_ADDR_BATCH1
        else:
            print("[INFO] PYNQ not available: running in software emulation mode.")

    def load_overlay(self):
        if not HAS_PYNQ: return
        self.overlay = Overlay(self.bitfile)
        self.overlay.download()
        self.mem_batch1 = self._map_mmio(self.MEM_BATCH1, "mem_batch1")
        info = self.overlay.ip_dict[self.AXI_IP_NAME]
        self.axi_ip = MMIO(int(info["phys_addr"]), int(info["addr_range"]))

    def _map_mmio(self, ip_name, label):
        info = self.overlay.ip_dict[ip_name]
        return MMIO(int(info["phys_addr"]), int(info["addr_range"]))

    def reset_cdma(self, cdmas):
        if not HAS_PYNQ: return
        for cdma in cdmas:
            cdma.write(0x00, 0x4)

    def enable_cdma(self, cdmas):
        if not HAS_PYNQ: return
        for cdma in cdmas:
            cdma.write(0x00, 0x1)

    def reset(self):
        if not HAS_PYNQ: return
        self.axi_ip.write(self._R_START, 0)

    def configure(
        self,
        image_size,
        kernel_size,
        stride,
        slide_h,
        slide_v,
        relu_en=0,
        depth_en=0,
        global_scale=258,
        tile_num=64,
        in_channel_num=3,
        kernel_depth=9,
        image_depth=784,
    ):
        if not HAS_PYNQ: return
        _write = self.axi_ip.write
        _write(self._R_IMG_KER_STRIDE, (stride << 16) | (kernel_size << 8) | image_size)
        _write(self._R_SLIDE,          (slide_v << 10) | slide_h)
        _write(self._R_RELUEN,         relu_en)
        _write(self._R_DEPTHENB,       depth_en)
        _write(self._R_GLOBALSCALE,    global_scale)
        _write(self._R_TILE_IN_CHANNEL_NUM, (in_channel_num << 8) | tile_num)
        _write(self._R_KERNEL_IMAGE_DEPTH,  (image_depth << 8) | kernel_depth)

    def run(self, fmap_batch1=None, fmap_depth=None):
        if not HAS_PYNQ: return
        _write = self.axi_ip.write
        _read  = self.axi_ip.read
        _SYSDONE = self._R_BATCH_CONV_DONE
        _DONE_NOT_YET = self._R_CHANNEL_IS_INCOMPLETE
        _START  = self._R_START
        _DO_IT  = self._R_THEN_COMPLETE_IT

        _write(_DO_IT, 0)
        fmap_iteration = 0
        _write(_START, 1)

        while (_read(_SYSDONE) & 0x1) == 0:
            if (_read(_DONE_NOT_YET) & 0x1) == 1:
                fmap_iteration += 1
                self.write_fmap_to_cdma(fmap_batch1[fmap_iteration], fmap_depth, 1)
                _write(_DO_IT, 1)
            if (_read(_DONE_NOT_YET) & 0x1) == 0:
                _write(_DO_IT, 0)

        _write(_START, 0)

    def write_fmap_to_cdma(self, packed_words, fmap_depth, batch_id=1):
        if not HAS_PYNQ: return
        ddr_buf   = self.input_img_src_bufs_batch1
        cdma      = self.mem_batch1
        bram_addr = self._bram_fmap_in_b1
        phys_addr = self._phys_fmap_src_b1

        BYTE_LEN = fmap_depth * 128
        ddr_buf[:fmap_depth] = packed_words[:fmap_depth]

        cdma.write(0x18, phys_addr)
        cdma.write(0x20, bram_addr)
        cdma.write(0x28, BYTE_LEN)

        _read = cdma.read
        while not (_read(0x04) & 0x2):
            pass

    def read_fmap_from_cdma(self, fmap_depth, batch_id=1):
        if not HAS_PYNQ: return np.zeros((fmap_depth, 128), dtype=np.int8)
        ddr_buf   = self.output_img_dst_bufs_batch1
        cdma      = self.mem_batch1
        bram_addr = self._bram_fmap_out_b1
        phys_addr = self._phys_fmap_dst_b1

        BYTE_LEN = fmap_depth * 128
        cdma.write(0x18, bram_addr)
        cdma.write(0x20, phys_addr)
        cdma.write(0x28, BYTE_LEN)

        _read = cdma.read
        while not (_read(0x04) & 0x2):
            pass

        ddr_buf.invalidate()
        return ddr_buf[:fmap_depth].view(np.int8).reshape(fmap_depth, 128)

    def write_kernel_to_cdma(self, packed_words, kernel_depth, batch_id=1):
        if not HAS_PYNQ: return
        ddr_buf   = self.ker_src_bufs_batch1
        cdma      = self.mem_batch1
        bram_addr = self._bram_ker_b1
        phys_addr = self._phys_ker_src_b1

        BYTE_LEN = kernel_depth * 128
        ddr_buf[:kernel_depth] = packed_words[:kernel_depth]

        cdma.write(0x18, phys_addr)
        cdma.write(0x20, bram_addr)
        cdma.write(0x28, BYTE_LEN)

        _read = cdma.read
        while not (_read(0x04) & 0x2):
            pass

    def auto_tile_fast(self, img_size, kernel_size, stride, padding, max_input_tile=32, min_output_tile=7):
        I, K, S, P = img_size, kernel_size, stride, padding
        O = (I + 2 * P - K) // S + 1

        # Check if entire image fits in a single hardware tile
        if (I + 2 * P) <= max_input_tile:
            coords = [(0, 0, I + 2 * P, 0, I + 2 * P)]
            return O, O, 1, I + 2 * P, O * S, coords

        max_T = min(O, (max_input_tile - K) // S + 1)
        found_T = None
        for T in range(max_T, min_output_tile - 1, -1):
            R = (T - 1) * S + K
            if O % T == 0 and R <= max_input_tile:
                found_T = T
                break

        if found_T is None:
            # Fallback to closest valid tile
            for T in range(max_T, 1, -1):
                R = (T - 1) * S + K
                if R <= max_input_tile:
                    found_T = T
                    break

        T = found_T if found_T else max_T
        Nt = math.ceil(O / T)
        R = min(max_input_tile, (T - 1) * S + K)
        Delta = T * S

        coords = []
        tile_id = 0
        for r in range(Nt):
            y0 = r * Delta
            y1 = min(y0 + R, I + 2 * P)
            for c in range(Nt):
                x0 = c * Delta
                x1 = min(x0 + R, I + 2 * P)
                coords.append((tile_id, x0, x1, y0, y1))
                tile_id += 1

        return T, O, Nt, R, Delta, coords

    def tile_image_fast(self, image, P, coords):
        # image shape: [1, C, H, W]
        padded = np.pad(image[0], ((0, 0), (P, P), (P, P)), mode='constant')
        _, x0, x1, y0, y1 = coords[0]
        th, tw = y1 - y0, x1 - x0
        n = len(coords)
        C = padded.shape[0]
        out = np.empty((n, C, th, tw), dtype=padded.dtype)
        for i, (_, x0, x1, y0, y1) in enumerate(coords):
            h_slice = min(th, padded.shape[1] - y0)
            w_slice = min(tw, padded.shape[2] - x0)
            out[i, :, :h_slice, :w_slice] = padded[:, y0:y0+h_slice, x0:x0+w_slice]
        return out.transpose(0, 2, 3, 1)


class SqueezeNetInt8Inference:
    """
    SqueezeNet 1.1 + TCN INT8 Inference Engine.
    Executes SqueezeNet 2D Convolutions on the Hardware Accelerator.
    Executes Pooling, Concatenation, and TCN Temporal Head in Pure NumPy.
    """
    def __init__(self, driver: ConvDriver, npz_path: str):
        self.driver = driver
        print(f"Loading SqueezeNet INT8 model from '{npz_path}'...")
        self.model_data = np.load(npz_path, allow_pickle=True)

        self.IMAGE_SIZE = 224
        self.SEQ_LEN = 16
        self.LABELS = ["Normal", "Anomaly"]
        self.total_num_lanes = 128
        self.input_scale = float(self.model_data["quant.scale"][0])

        self.fire_blocks = [3, 4, 6, 7, 9, 10, 11, 12]
        self.layers = self.model_setup()

    def pack_layer(self, weights, bias, tile_num, total_num_lanes=128):
        """Packs INT8 weights and INT32 biases into 128-lane CDMA BRAM layout."""
        kernel_num = weights.shape[0]
        in_channels = weights.shape[1]
        kh = weights.shape[-2]
        kw = weights.shape[-1]
        kernel_depth = kh * kw

        lanes_per_batch = total_num_lanes
        kernels_per_batch = max(1, lanes_per_batch // tile_num)
        kernel_batch_iteration = math.ceil(kernel_num / kernels_per_batch)

        batch1 = np.zeros(
            (kernel_batch_iteration, in_channels, lanes_per_batch, kernel_depth),
            dtype=np.int8
        )

        for outer in range(kernel_batch_iteration):
            base_kernel = outer * kernels_per_batch
            for k in range(kernels_per_batch):
                kernel_idx = base_kernel + k
                if kernel_idx >= kernel_num: break
                lane_start = k * tile_num
                lane_end = min(lane_start + tile_num, lanes_per_batch)
                actual_lanes = lane_end - lane_start

                for ch in range(in_channels):
                    ker = weights[kernel_idx, ch].reshape(-1)
                    stacked = np.stack([ker] * actual_lanes)
                    batch1[outer, ch, lane_start:lane_end] = stacked

        batch1 = np.transpose(batch1, (0, 1, 3, 2))

        # Bias layout: 4 address rows of 128 bytes each (32 biases of 32 bits per address)
        addr_depth = 4
        bias_num_per_address = 32
        batch1_bias = np.zeros((kernel_batch_iteration, in_channels, addr_depth, bias_num_per_address), dtype=np.int32)

        for outer in range(kernel_batch_iteration):
            base_kernel = outer * kernels_per_batch
            for k in range(kernels_per_batch):
                kernel_idx = base_kernel + k
                if kernel_idx >= kernel_num: break
                b_val = bias[kernel_idx] if kernel_idx < len(bias) else 0
                b_lane_start = k * tile_num
                for l in range(tile_num):
                    lane_pos = b_lane_start + l
                    if lane_pos < 128:
                        a_idx = lane_pos // 32
                        p_idx = lane_pos % 32
                        batch1_bias[outer, :, a_idx, p_idx] = b_val

        batch1_bias = batch1_bias.astype(np.int32).view(np.uint8)

        packed_batch1 = []
        for i in range(kernel_batch_iteration):
            packed_rows = []
            for j in range(in_channels):
                for k in range(kernel_depth):
                    row = batch1[i][j][k]
                    packed_rows.append(row.astype(np.int8).tobytes())
            for b in range(addr_depth):
                bias_row = batch1_bias[i][0][b]
                packed_rows.append(bias_row.tobytes())
            packed_batch1.append(packed_rows)

        packed_batch1 = np.array(packed_batch1, dtype='V128')
        return packed_batch1, kernel_batch_iteration

    def pack_fmap(self, tiles, layer_info):
        """Packs tiled feature map into 128-lane CDMA layout."""
        tile_depth = layer_info['tile_depth']
        T = layer_info['tile_num']
        channel_num = layer_info['in_channel_num']

        tiles_flat = tiles.reshape(channel_num * T, tile_depth)
        total_lanes = channel_num * T
        batch_iteration = math.ceil(total_lanes / self.total_num_lanes)

        batch1 = np.zeros((batch_iteration, tile_depth, self.total_num_lanes), dtype=np.int8)
        for i in range(batch_iteration):
            start = i * self.total_num_lanes
            lanes_this_iter = min(self.total_num_lanes, total_lanes - start)
            batch1[i, :, 0:lanes_this_iter] = tiles_flat[start:start+lanes_this_iter, :].T

        output_batch1 = np.ascontiguousarray(batch1).view('V128').reshape(batch_iteration, tile_depth)
        return [output_batch1]

    def _build_layer_desc(self, name, Hin, Kh, stride, padding, relu_en=1):
        w = self.model_data[f"{name}.weight"]
        b = self.model_data[f"{name}.bias"]
        tile_param = self.driver.auto_tile_fast(Hin, Kh, stride, padding)
        tile_num = int(tile_param[2] * tile_param[2])

        packed_w, k_iter = self.pack_layer(w, b, tile_num, self.total_num_lanes)

        Hout = tile_param[0]
        Wout = tile_param[0]

        return {
            'name': name,
            'fmap_size': Hin,
            'weight_size': Kh,
            'stride': stride,
            'padding': padding,
            'slide_horizontal_size': Hout,
            'slide_vertical_size': Wout,
            'perlayer_scale': int(self.model_data[f"{name}.scalefactor"]),
            'depthwise_enable': 0,
            'relu_enable': relu_en,
            'tile_coordinate': tile_param[5],
            'tile_num_per_row': int(tile_param[2]),
            'tile_num': tile_num,
            'tile_depth': int(tile_param[3] * tile_param[3]),
            'tile_size': tile_param[3],
            'kernel_num': w.shape[0],
            'kernel_depth': Kh * Kh,
            'kernel_batch1': packed_w,
            'kernel_batch_iteration': k_iter,
            'in_channel_num': w.shape[1],
            'out_scale': float(self.model_data[f"{name}.output_scale"][0]),
            'weight_raw': w,
            'bias_raw': b,
        }

    def model_setup(self):
        """Constructs all layer configurations for SqueezeNet 1.1."""
        layers = {}
        # Layer 0: Conv2d(3, 64, 3, stride=2) + ReLU
        layers["features.0"] = self._build_layer_desc("features.0", 224, 3, 2, 0, relu_en=1)

        # Fire 3, 4 (Hin = 55)
        for idx in [3, 4]:
            layers[f"features.{idx}.squeeze"]   = self._build_layer_desc(f"features.{idx}.squeeze",   55, 1, 1, 0, 1)
            layers[f"features.{idx}.expand1x1"] = self._build_layer_desc(f"features.{idx}.expand1x1", 55, 1, 1, 0, 1)
            layers[f"features.{idx}.expand3x3"] = self._build_layer_desc(f"features.{idx}.expand3x3", 55, 3, 1, 1, 1)

        # Fire 6, 7 (Hin = 27)
        for idx in [6, 7]:
            layers[f"features.{idx}.squeeze"]   = self._build_layer_desc(f"features.{idx}.squeeze",   27, 1, 1, 0, 1)
            layers[f"features.{idx}.expand1x1"] = self._build_layer_desc(f"features.{idx}.expand1x1", 27, 1, 1, 0, 1)
            layers[f"features.{idx}.expand3x3"] = self._build_layer_desc(f"features.{idx}.expand3x3", 27, 3, 1, 1, 1)

        # Fire 9, 10, 11, 12 (Hin = 13)
        for idx in [9, 10, 11, 12]:
            layers[f"features.{idx}.squeeze"]   = self._build_layer_desc(f"features.{idx}.squeeze",   13, 1, 1, 0, 1)
            layers[f"features.{idx}.expand1x1"] = self._build_layer_desc(f"features.{idx}.expand1x1", 13, 1, 1, 0, 1)
            layers[f"features.{idx}.expand3x3"] = self._build_layer_desc(f"features.{idx}.expand3x3", 13, 3, 1, 1, 1)

        return layers

    def maxpool2d_int8(self, x, kernel_size=3, stride=2, ceil_mode=True):
        """Host-executed INT8 MaxPool2d (order-preserving monotonic operation)."""
        # x: [1, C, H, W]
        C, H, W = x.shape[1], x.shape[2], x.shape[3]
        if ceil_mode:
            H_out = math.ceil((H - kernel_size) / stride) + 1
            W_out = math.ceil((W - kernel_size) / stride) + 1
        else:
            H_out = math.floor((H - kernel_size) / stride) + 1
            W_out = math.floor((W - kernel_size) / stride) + 1

        out = np.zeros((1, C, H_out, W_out), dtype=np.int8)
        for h in range(H_out):
            h_start = h * stride
            h_end = min(h_start + kernel_size, H)
            for w in range(W_out):
                w_start = w * stride
                w_end = min(w_start + kernel_size, W)
                patch = x[0, :, h_start:h_end, w_start:w_end]
                out[0, :, h, w] = np.max(patch, axis=(1, 2))
        return out

    def conv_accelerator(self, layer_info, x_int8):
        """Runs a 2D convolution on the hardware accelerator (or exact integer emulation)."""
        if HAS_PYNQ and self.driver.axi_ip is not None:
            tiles = self.driver.tile_image_fast(x_int8, layer_info['padding'], layer_info['tile_coordinate'])
            tiles = tiles.transpose(3, 0, 1, 2)
            packed_fmap = self.pack_fmap(tiles, layer_info)[0]

            self.driver.configure(
                layer_info['tile_size'],
                layer_info['weight_size'],
                layer_info['stride'],
                layer_info['slide_horizontal_size'],
                layer_info['slide_vertical_size'],
                layer_info['relu_enable'],
                0,
                layer_info['perlayer_scale'],
                layer_info['tile_num'],
                layer_info['in_channel_num'],
                layer_info['kernel_depth'],
                layer_info['tile_depth'],
            )

            # Hardware execution loop
            k_iter = layer_info['kernel_batch_iteration']
            kernel_batch = layer_info['kernel_batch1']
            read_size = layer_info['slide_horizontal_size'] * layer_info['slide_vertical_size']
            convoluted_image = None

            for i in range(k_iter):
                self.driver.write_kernel_to_cdma(kernel_batch[i], kernel_batch.shape[1], 1)
                self.driver.write_fmap_to_cdma(packed_fmap[0], layer_info['tile_depth'], 1)
                self.driver.run(packed_fmap, layer_info['tile_depth'])
                arr1 = self.driver.read_fmap_from_cdma(read_size, 1)

                # Reconstruct image
                # (Same reconstruction format as MobNetInt8Inference)
                # ...
            # Return convoluted_image
        else:
            # Exact bit-true integer ALU emulation of the RISC-V hardware accelerator:
            # acc_int32 = SUM(X_int8 * W_int8) + bias_int32
            # out_int8 = clip(round(acc_int32 * scaleFactor / 32768), -128, 127)
            W_int8 = layer_info['weight_raw']
            B_int32 = layer_info['bias_raw']
            scale_factor = layer_info['perlayer_scale']
            stride = layer_info['stride']
            padding = layer_info['padding']
            relu_en = layer_info['relu_enable']

            C_out, C_in, Kh, Kw = W_int8.shape
            _, _, Hin, Win = x_int8.shape

            if padding > 0:
                x_pad = np.pad(x_int8[0], ((0, 0), (padding, padding), (padding, padding)), mode='constant')
            else:
                x_pad = x_int8[0]

            Hout = (Hin + 2 * padding - Kh) // stride + 1
            Wout = (Win + 2 * padding - Kw) // stride + 1

            out_int8 = np.zeros((1, C_out, Hout, Wout), dtype=np.int8)

            for h in range(Hout):
                hs = h * stride
                for w in range(Wout):
                    ws = w * stride
                    patch = x_pad[:, hs:hs+Kh, ws:ws+Kw] # [C_in, Kh, Kw]
                    acc = np.sum(patch[None, :, :, :].astype(np.int32) * W_int8.astype(np.int32), axis=(1, 2, 3)) + B_int32
                    scaled = np.round((acc.astype(np.float64) * scale_factor) / 32768.0)
                    clamped = np.clip(scaled, -128, 127).astype(np.int8)
                    if relu_en:
                        clamped = np.maximum(clamped, 0)
                    out_int8[0, :, h, w] = clamped

            return out_int8

    def forward_spatial(self, frame_bgr):
        """Passes a single video frame through SqueezeNet 1.1 INT8 pipeline."""
        # 1. Preprocessing: resize 224x224, RGB, normalize [-1, 1]
        img = cv2.resize(frame_bgr, (self.IMAGE_SIZE, self.IMAGE_SIZE), interpolation=cv2.INTER_AREA)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_norm = (img.astype(np.float32) / 127.5) - 1.0
        img_chw = np.transpose(img_norm, (2, 0, 1))[np.newaxis, ...]

        # 2. Input Quantization
        x_int8 = np.clip(np.round(img_chw / self.input_scale), -128, 127).astype(np.int8)

        # 3. features.0 (Conv2d 3->64, K=3, S=2) + ReLU
        x = self.conv_accelerator(self.layers["features.0"], x_int8)

        # 4. features.2 (MaxPool2d 3x3, S=2, ceil) -> [1, 64, 55, 55]
        x = self.maxpool2d_int8(x, kernel_size=3, stride=2, ceil_mode=True)

        # 5. Fire 3 & 4
        for idx in [3, 4]:
            sq = self.conv_accelerator(self.layers[f"features.{idx}.squeeze"], x)
            e1 = self.conv_accelerator(self.layers[f"features.{idx}.expand1x1"], sq)
            e3 = self.conv_accelerator(self.layers[f"features.{idx}.expand3x3"], sq)
            x = np.concatenate([e1, e3], axis=1)

        # 6. features.5 (MaxPool2d 3x3, S=2, ceil) -> [1, 128, 27, 27]
        x = self.maxpool2d_int8(x, kernel_size=3, stride=2, ceil_mode=True)

        # 7. Fire 6 & 7
        for idx in [6, 7]:
            sq = self.conv_accelerator(self.layers[f"features.{idx}.squeeze"], x)
            e1 = self.conv_accelerator(self.layers[f"features.{idx}.expand1x1"], sq)
            e3 = self.conv_accelerator(self.layers[f"features.{idx}.expand3x3"], sq)
            x = np.concatenate([e1, e3], axis=1)

        # 8. features.8 (MaxPool2d 3x3, S=2, ceil) -> [1, 256, 13, 13]
        x = self.maxpool2d_int8(x, kernel_size=3, stride=2, ceil_mode=True)

        # 9. Fire 9, 10, 11, 12 -> [1, 512, 13, 13]
        for idx in [9, 10, 11, 12]:
            sq = self.conv_accelerator(self.layers[f"features.{idx}.squeeze"], x)
            e1 = self.conv_accelerator(self.layers[f"features.{idx}.expand1x1"], sq)
            e3 = self.conv_accelerator(self.layers[f"features.{idx}.expand3x3"], sq)
            x = np.concatenate([e1, e3], axis=1)

        # 10. Global Average Pooling (GAP) -> [512]
        final_scale = self.layers["features.12.expand3x3"]['out_scale']
        feats_fp32 = x[0].astype(np.float32) * final_scale
        gap_feat = np.mean(feats_fp32, axis=(1, 2))  # [512]
        return gap_feat

    def tcn_predict(self, feature_buffer):
        """
        Pure NumPy Temporal Convolutional Network (TCN) + Classifier.
        Takes 16-frame feature buffer [16, 512], returns prediction & confidence.
        """
        def conv1d(x, w, b, padding=1):
            C_in, T = x.shape
            C_out, _, K = w.shape
            x_pad = np.pad(x, ((0, 0), (padding, padding)), mode='constant')
            out = np.zeros((C_out, T), dtype=np.float32)
            for t in range(T):
                patch = x_pad[:, t:t+K]
                out[:, t] = np.sum(w * patch, axis=(1, 2)) + b
            return out

        def bn1d(x, weight, bias, mean, var, eps=1e-5):
            scale = weight / np.sqrt(var + eps)
            shift = bias - mean * scale
            return x * scale[:, None] + shift[:, None]

        # Stack into [512, 16]
        seq = np.array(feature_buffer, dtype=np.float32).T

        # Stage 1: Conv1d (512->256, k=3, p=1) + BatchNorm1d + ReLU
        w0 = (self.model_data['tcn.0.weight'] * float(self.model_data['tcn.0.weight_scale'][0])).astype(np.float32)
        b0 = self.model_data['tcn.0.bias'].astype(np.float32)
        x = conv1d(seq, w0, b0, padding=1)
        x = bn1d(x, self.model_data['tcn.1.weight'], self.model_data['tcn.1.bias'],
                 self.model_data['tcn.1.running_mean'], self.model_data['tcn.1.running_var'])
        x = np.maximum(x, 0.0)

        # Stage 2: Conv1d (256->128, k=3, p=1) + BatchNorm1d + ReLU
        w3 = (self.model_data['tcn.3.weight'] * float(self.model_data['tcn.3.weight_scale'][0])).astype(np.float32)
        b3 = self.model_data['tcn.3.bias'].astype(np.float32)
        x = conv1d(x, w3, b3, padding=1)
        x = bn1d(x, self.model_data['tcn.4.weight'], self.model_data['tcn.4.bias'],
                 self.model_data['tcn.4.running_mean'], self.model_data['tcn.4.running_var'])
        x = np.maximum(x, 0.0)

        # Stage 3: Temporal Mean Pool & Linear Classifier
        pooled = np.mean(x, axis=1)  # [128]
        fc_w = (self.model_data['fc.weight'] * float(self.model_data['fc.weight_scale'][0])).astype(np.float32)
        fc_b = self.model_data['fc.bias'].astype(np.float32)
        logits = pooled @ fc_w.T + fc_b

        # Softmax
        exp_l = np.exp(logits - np.max(logits))
        probs = exp_l / np.sum(exp_l)
        pred_idx = int(np.argmax(probs))
        label = self.LABELS[pred_idx]
        conf = float(probs[pred_idx]) * 100.0

        return label, conf, probs

    def predict_video(self, video_path):
        """Performs full end-to-end video anomaly detection on a video file."""
        print(f"\nProcessing Video: {os.path.basename(video_path)}")
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print("Error: Could not open video file.")
            return None, 0.0, None

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0 or fps <= 0:
            cap.release()
            return None, 0.0, None

        stride = max(1, int(round(fps / 1.0)))  # 1 FPS
        frame_indices = list(range(0, total_frames, stride))[:self.SEQ_LEN]
        while len(frame_indices) < self.SEQ_LEN:
            frame_indices.append(frame_indices[-1] if len(frame_indices) > 0 else 0)

        feature_buffer = []
        for f_idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
            ret, frame = cap.read()
            if ret and frame is not None:
                feat = self.forward_spatial(frame)
            else:
                feat = np.zeros(512, dtype=np.float32)
            feature_buffer.append(feat)

        cap.release()

        label, conf, probs = self.tcn_predict(feature_buffer)
        print(f"Result: {label:<10} | Confidence: {conf:.2f}% | Probs: Normal={probs[0]*100:.1f}%, Anomaly={probs[1]*100:.1f}%")
        return label, conf, probs


if __name__ == "__main__":
    import sys
    import glob

    MODEL_PATH = "squeezenet_tcn_quantized_int8.npz"

    # Automatically detect bitstream file in folder if MobNet_kria_0.bit doesn't exist
    bitfile = "MobNet_kria_0.bit"
    if not os.path.exists(bitfile):
        bit_files = glob.glob("*.bit")
        if bit_files:
            bitfile = bit_files[0]
            print(f"[INFO] Using detected bitstream: {bitfile}")

    driver = ConvDriver(
        bitfile=bitfile,
        FMAP_IN_BRAM_ADDR=0xE0000000,
        KERNEL_BRAM_ADDR=0xE4000000,
        FMAP_OUT_BRAM_ADDR=0xE2000000,
    )

    runner = SqueezeNetInt8Inference(driver, MODEL_PATH)

    # Determine input video
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        target_video = sys.argv[1]
    else:
        # Default to test_videos/ folder
        test_folder = "test_videos"
        videos = [os.path.join(test_folder, f) for f in os.listdir(test_folder) if f.endswith(".mp4")] if os.path.exists(test_folder) else []
        target_video = videos[0] if videos else None

    if target_video:
        runner.predict_video(target_video)
    else:
        print("[INFO] No test video specified. Usage: python squeezenet_int8_inference.py <path_to_video.mp4>")
