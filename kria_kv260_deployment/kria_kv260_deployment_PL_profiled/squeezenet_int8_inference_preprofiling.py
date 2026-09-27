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


SUPPORTED_TILE_NUMS = (1, 4, 16, 64)
DEFAULT_HW_TIMEOUT_S = float(os.environ.get("KV260_HW_TIMEOUT_S", "10.0"))
DEFAULT_CDMA_TIMEOUT_S = float(os.environ.get("KV260_CDMA_TIMEOUT_S", "2.0"))


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
            for label, addr in (("fmap_src", self._phys_fmap_src_b1),
                                ("fmap_dst", self._phys_fmap_dst_b1),
                                ("kernel_src", self._phys_ker_src_b1)):
                if int(addr) > 0xFFFFFFFF:
                    raise RuntimeError(
                        f"CMA buffer {label} is above 4 GiB (0x{int(addr):X}), but this bitstream's AXI-CDMA has 32-bit addresses."
                    )

            self._bram_fmap_in_b1   = self.FMAP_IN_BRAM_ADDR_BATCH1
            self._bram_ker_b1       = self.KERNEL_BRAM_ADDR_BATCH1
            self._bram_fmap_out_b1  = self.FMAP_OUT_BRAM_ADDR_BATCH1
        else:
            print("[INFO] PYNQ not available: running in software emulation mode.")

    def load_overlay(self):
        if not HAS_PYNQ: return
        self.overlay = Overlay(self.bitfile)
        self.overlay.download()
        missing = [n for n in (self.MEM_BATCH1, self.AXI_IP_NAME) if n not in self.overlay.ip_dict]
        if missing:
            raise RuntimeError(f"Overlay is missing required IP(s): {missing}. Found: {sorted(self.overlay.ip_dict)}")
        self.mem_batch1 = self._map_mmio(self.MEM_BATCH1, "mem_batch1")
        info = self.overlay.ip_dict[self.AXI_IP_NAME]
        self.axi_ip = MMIO(int(info["phys_addr"]), int(info["addr_range"]))
        print(f"[PL] Overlay programmed: {os.path.basename(self.bitfile)}")
        print(f"[PL] {self.AXI_IP_NAME} @ 0x{int(info['phys_addr']):08X}; CDMA={self.MEM_BATCH1}")

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
        if int(tile_num) not in SUPPORTED_TILE_NUMS:
            raise ValueError(
                f"Unsupported PL tile_num={tile_num}; this bitstream's CCU supports only {SUPPORTED_TILE_NUMS}."
            )
        _write = self.axi_ip.write
        _write(self._R_START, 0)
        _write(self._R_THEN_COMPLETE_IT, 0)
        _write(self._R_IMG_KER_STRIDE, (stride << 16) | (kernel_size << 8) | image_size)
        _write(self._R_SLIDE,          (slide_v << 10) | slide_h)
        _write(self._R_RELUEN,         relu_en)
        _write(self._R_DEPTHENB,       depth_en)
        _write(self._R_GLOBALSCALE,    global_scale)
        _write(self._R_TILE_IN_CHANNEL_NUM, (in_channel_num << 8) | tile_num)
        _write(self._R_KERNEL_IMAGE_DEPTH,  (image_depth << 8) | kernel_depth)

    def run(self, fmap_batch1=None, fmap_depth=None, timeout_s=DEFAULT_HW_TIMEOUT_S):
        """Run one configured convolution batch with bounded, edge-safe PL handshaking."""
        if not HAS_PYNQ:
            return
        if fmap_batch1 is None or len(fmap_batch1) == 0:
            raise ValueError("fmap_batch1 must contain at least the preloaded feature-map chunk")

        _write = self.axi_ip.write
        _read = self.axi_ip.read
        _write(self._R_THEN_COMPLETE_IT, 0)
        fmap_iteration = 0  # chunk 0 is preloaded by the caller
        deadline = time.monotonic() + float(timeout_s)

        # batch_conv_done is level-based; require the previous transaction to have cleared
        # before creating the next START edge. This avoids accepting a stale DONE=1.
        while (_read(self._R_BATCH_CONV_DONE) & 0x1) != 0:
            if time.monotonic() > deadline:
                raise TimeoutError("PL batch_conv_done stayed high while START=0; controller did not re-arm")
        _write(self._R_START, 1)

        try:
            while (_read(self._R_BATCH_CONV_DONE) & 0x1) == 0:
                if (_read(self._R_TILE_NUM_NOT_RIGHT) & 0x1) != 0:
                    raise RuntimeError(
                        "PL asserted tile_num_not_right. The synthesized CCU accepts only tile_num 1/4/16/64."
                    )
                if time.monotonic() > deadline:
                    raise TimeoutError(
                        "Timed out waiting for PL batch_conv_done "
                        f"(incomplete=0x{_read(self._R_CHANNEL_IS_INCOMPLETE):08X}, "
                        f"tile_bad=0x{_read(self._R_TILE_NUM_NOT_RIGHT):08X})."
                    )

                if (_read(self._R_CHANNEL_IS_INCOMPLETE) & 0x1) == 1:
                    fmap_iteration += 1
                    if fmap_iteration >= len(fmap_batch1):
                        raise RuntimeError(
                            f"PL requested feature-map chunk {fmap_iteration}, but host packed only "
                            f"{len(fmap_batch1)} chunk(s)."
                        )
                    self.write_fmap_to_cdma(fmap_batch1[fmap_iteration], fmap_depth, 1)
                    _write(self._R_THEN_COMPLETE_IT, 1)

                    # Hold ACK until the PL consumes it; this prevents re-sending the same request
                    # if software loops faster than the 100 MHz controller changes status.
                    while ((_read(self._R_CHANNEL_IS_INCOMPLETE) & 0x1) == 1 and
                           (_read(self._R_BATCH_CONV_DONE) & 0x1) == 0):
                        if time.monotonic() > deadline:
                            raise TimeoutError("Timed out waiting for PL to acknowledge the next FMAP chunk")
                    _write(self._R_THEN_COMPLETE_IT, 0)
        finally:
            _write(self._R_THEN_COMPLETE_IT, 0)
            _write(self._R_START, 0)

    def _wait_cdma_idle(self, cdma, timeout_s=DEFAULT_CDMA_TIMEOUT_S):
        deadline = time.monotonic() + float(timeout_s)
        while True:
            status = int(cdma.read(0x04))
            if status & 0x2:
                return status
            if time.monotonic() > deadline:
                raise TimeoutError(f"AXI-CDMA timeout; DMASR=0x{status:08X}")

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

        self._wait_cdma_idle(cdma)

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

        self._wait_cdma_idle(cdma)

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

        self._wait_cdma_idle(cdma)

    def auto_tile_fast(self, img_size, kernel_size, stride, padding, max_input_tile=32, min_output_tile=1):
        """Choose a square tiling that is legal for this synthesized CCU.

        The HWH exposes CCU local parameters for exactly tile_num={1,4,16,64}, i.e.
        Nt={1,2,4,8} tiles per spatial dimension. Boundary tiles are zero-padded and
        reconstructed with cropping, so O does not need to be divisible by T.
        """
        I, K, S, P = map(int, (img_size, kernel_size, stride, padding))
        O = (I + 2 * P - K) // S + 1
        padded_extent = I + 2 * P

        chosen = None
        for Nt in (1, 2, 4, 8):
            T = int(math.ceil(O / Nt))
            if T < min_output_tile:
                continue
            R = (T - 1) * S + K
            if R <= max_input_tile:
                chosen = (T, Nt, R)
                break
        if chosen is None:
            raise ValueError(
                f"Cannot tile I={I}, K={K}, S={S}, P={P} into the bitstream-supported "
                f"tile counts {SUPPORTED_TILE_NUMS} with max input tile {max_input_tile}."
            )

        T, Nt, R = chosen
        Delta = T * S
        coords = []
        tile_id = 0
        for r in range(Nt):
            y0 = r * Delta
            y1 = min(y0 + R, padded_extent)
            for c in range(Nt):
                x0 = c * Delta
                x1 = min(x0 + R, padded_extent)
                coords.append((tile_id, x0, x1, y0, y1))
                tile_id += 1
        return T, O, Nt, R, Delta, coords

    def tile_image_fast(self, image, P, coords):
        # image shape [1,C,H,W]; all tiles have fixed R x R storage.
        padded = np.pad(image[0], ((0, 0), (P, P), (P, P)), mode='constant')
        _, x0, x1, y0, y1 = coords[0]
        R_h, R_w = y1 - y0, x1 - x0
        # The first tile is full-sized by construction; zeros make partial boundary tiles deterministic.
        n, C = len(coords), padded.shape[0]
        out = np.zeros((n, C, R_h, R_w), dtype=padded.dtype)
        for i, (_, x0, x1, y0, y1) in enumerate(coords):
            h_slice = max(0, min(R_h, padded.shape[1] - y0))
            w_slice = max(0, min(R_w, padded.shape[2] - x0))
            if h_slice and w_slice:
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
        if tile_num not in SUPPORTED_TILE_NUMS:
            raise RuntimeError(f"Internal tiler produced unsupported tile_num={tile_num}")

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
            'output_size': int(tile_param[1]),
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

    def print_pl_layer_plan(self):
        print("\n[PL] SqueezeNet convolution deployment plan")
        print("layer                              in  out  k  tile  T  R  fmap_chunks  kernel_batches")
        print("-" * 92)
        for name, li in self.layers.items():
            fmap_chunks = math.ceil(li['in_channel_num'] * li['tile_num'] / self.total_num_lanes)
            print(
                f"{name:34s} {li['in_channel_num']:3d} {li['kernel_num']:4d} "
                f"{li['weight_size']:1d} {li['tile_num']:5d} {li['slide_horizontal_size']:2d} "
                f"{li['tile_size']:2d} {fmap_chunks:11d} {li['kernel_batch_iteration']:14d}"
            )

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

    def _conv_software_reference(self, layer_info, x_int8):
        """Integer reference matching the PL Q1.15 requantizer as closely as possible."""
        W_int8 = layer_info['weight_raw']
        B_int32 = layer_info['bias_raw']
        scale_factor = int(layer_info['perlayer_scale'])
        stride = int(layer_info['stride'])
        padding = int(layer_info['padding'])
        relu_en = int(layer_info['relu_enable'])

        C_out, C_in, Kh, Kw = W_int8.shape
        _, _, Hin, Win = x_int8.shape
        x_pad = (np.pad(x_int8[0], ((0, 0), (padding, padding), (padding, padding)), mode='constant')
                 if padding > 0 else x_int8[0])
        Hout = (Hin + 2 * padding - Kh) // stride + 1
        Wout = (Win + 2 * padding - Kw) // stride + 1
        out_int8 = np.zeros((1, C_out, Hout, Wout), dtype=np.int8)
        W32 = W_int8.astype(np.int32)

        for h in range(Hout):
            hs = h * stride
            for w in range(Wout):
                ws = w * stride
                patch = x_pad[:, hs:hs+Kh, ws:ws+Kw]
                acc = (np.sum(patch[None, :, :, :].astype(np.int32) * W32, axis=(1, 2, 3), dtype=np.int64)
                       + B_int32.astype(np.int64))
                # DWM-style signed Q1.15 scaling: multiply, add 2^14 rounding bias, arithmetic >>> 15.
                scaled = (acc * scale_factor + (1 << 14)) >> 15
                clamped = np.clip(scaled, -128, 127).astype(np.int8)
                if relu_en:
                    clamped = np.maximum(clamped, 0)
                out_int8[0, :, h, w] = clamped
        return out_int8

    def _reconstruct_hw_batch(self, arr, dst, kernel_batch_index, layer_info):
        """Map one [T*T,128] PL output BRAM image into NCHW.

        Lane layout follows the host packer / synthesized Fmap router: contiguous groups
        of tile_num lanes correspond to one output kernel, with tile_id as the lane offset.
        """
        T = int(layer_info['slide_horizontal_size'])
        Nt = int(layer_info['tile_num_per_row'])
        tile_num = int(layer_info['tile_num'])
        O = int(layer_info['output_size'])
        C_out = int(layer_info['kernel_num'])
        kernels_per_batch = self.total_num_lanes // tile_num

        if arr.shape != (T * T, self.total_num_lanes):
            raise RuntimeError(f"Unexpected PL output shape {arr.shape}; expected {(T*T, self.total_num_lanes)}")

        for local_k in range(kernels_per_batch):
            out_ch = kernel_batch_index * kernels_per_batch + local_k
            if out_ch >= C_out:
                break
            lane_base = local_k * tile_num
            for tile_id in range(tile_num):
                tr, tc = divmod(tile_id, Nt)
                y0, x0 = tr * T, tc * T
                if y0 >= O or x0 >= O:
                    continue
                vh, vw = min(T, O - y0), min(T, O - x0)
                lane = lane_base + tile_id
                block = arr[:, lane].reshape(T, T)
                dst[0, out_ch, y0:y0+vh, x0:x0+vw] = block[:vh, :vw]

    def conv_accelerator(self, layer_info, x_int8):
        """Run one SqueezeNet convolution in PL, or exact integer emulation off-board."""
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

            k_iter = int(layer_info['kernel_batch_iteration'])
            kernel_batch = layer_info['kernel_batch1']
            T = int(layer_info['slide_horizontal_size'])
            read_size = T * int(layer_info['slide_vertical_size'])
            O = int(layer_info['output_size'])
            convoluted_image = np.zeros((1, int(layer_info['kernel_num']), O, O), dtype=np.int8)

            for i in range(k_iter):
                self.driver.write_kernel_to_cdma(kernel_batch[i], kernel_batch.shape[1], 1)
                self.driver.write_fmap_to_cdma(packed_fmap[0], layer_info['tile_depth'], 1)
                self.driver.run(packed_fmap, layer_info['tile_depth'])
                arr1 = self.driver.read_fmap_from_cdma(read_size, 1)
                if os.environ.get("KV260_DUMP_RAW", "0") == "1":
                    safe_name = layer_info['name'].replace('.', '_')
                    np.save(f"raw_{safe_name}_batch{i}.npy", arr1)
                self._reconstruct_hw_batch(arr1, convoluted_image, i, layer_info)

            if os.environ.get("KV260_VERBOSE", "0") == "1":
                print(
                    f"[PL] {layer_info['name']}: out={convoluted_image.shape}, "
                    f"tile_num={layer_info['tile_num']}, T={T}, k_batches={k_iter}, "
                    f"range=[{int(convoluted_image.min())},{int(convoluted_image.max())}]"
                )
            return convoluted_image
        else:
            return self._conv_software_reference(layer_info, x_int8)

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
    import argparse
    import glob

    parser = argparse.ArgumentParser(description="KV260 PL SqueezeNet INT8 + NumPy TCN inference")
    parser.add_argument("video", nargs="?", help="Input video (.mp4)")
    parser.add_argument("--model", default="squeezenet_tcn_quantized_int8.npz")
    parser.add_argument("--bit", default="MobNet_kria_0.bit")
    parser.add_argument("--print-plan", action="store_true", help="Print hardware tiling/batching plan")
    parser.add_argument("--smoke-layer0", action="store_true", help="Run only features.0 on the first frame and exit")
    parser.add_argument("--validate-layer0", action="store_true", help="Compare PL features.0 against integer CPU reference")
    args = parser.parse_args()

    bitfile = args.bit
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
    runner = SqueezeNetInt8Inference(driver, args.model)

    if args.print_plan:
        runner.print_pl_layer_plan()
        if not args.smoke_layer0 and not args.video:
            raise SystemExit(0)

    target_video = args.video
    if not target_video:
        videos = sorted(glob.glob(os.path.join("test_videos", "*.mp4")))
        target_video = videos[0] if videos else None

    if args.validate_layer0 and not HAS_PYNQ:
        raise SystemExit("--validate-layer0 requires PYNQ/KV260 so that the first result is genuinely from PL")

    if args.smoke_layer0 or args.validate_layer0:
        if not target_video or not os.path.exists(target_video):
            raise SystemExit("No video available for layer-0 smoke/validation")
        cap = cv2.VideoCapture(target_video)
        ok, frame = cap.read()
        cap.release()
        if not ok or frame is None:
            raise SystemExit(f"Could not decode first frame of {target_video}")
        img = cv2.resize(frame, (runner.IMAGE_SIZE, runner.IMAGE_SIZE), interpolation=cv2.INTER_AREA)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_norm = (img.astype(np.float32) / 127.5) - 1.0
        img_chw = np.transpose(img_norm, (2, 0, 1))[np.newaxis, ...]
        x_int8 = np.clip(np.round(img_chw / runner.input_scale), -128, 127).astype(np.int8)
        y = runner.conv_accelerator(runner.layers["features.0"], x_int8)
        print(f"[SMOKE PASS] features.0 returned {y.shape}, dtype={y.dtype}, "
              f"range=[{int(y.min())},{int(y.max())}], checksum={int(y.astype(np.int64).sum())}")

        if args.validate_layer0:
            ref = runner._conv_software_reference(runner.layers["features.0"], x_int8)
            delta = y.astype(np.int16) - ref.astype(np.int16)
            mism = int(np.count_nonzero(delta))
            total = int(delta.size)
            print(f"[VALIDATE] mismatch={mism}/{total} ({100.0*mism/total:.6f}%), "
                  f"max_abs={int(np.max(np.abs(delta)))}, mean_abs={float(np.mean(np.abs(delta))):.6f}")
            if mism:
                idx = tuple(int(v) for v in np.argwhere(delta != 0)[0])
                print(f"[VALIDATE] first mismatch at {idx}: PL={int(y[idx])}, REF={int(ref[idx])}, delta={int(delta[idx])}")
                np.save("diagnostics_layer0_pl.npy", y)
                np.save("diagnostics_layer0_ref.npy", ref)
                print("[VALIDATE] Saved diagnostics_layer0_pl.npy and diagnostics_layer0_ref.npy")
                raise SystemExit(2)
            print("[VALIDATE PASS] PL output is bit-exact with the integer layer-0 reference.")
        raise SystemExit(0)

    if target_video and os.path.exists(target_video):
        runner.predict_video(target_video)
    else:
        print("[INFO] No test video specified. Usage: python3 squeezenet_int8_inference.py <video.mp4>")
