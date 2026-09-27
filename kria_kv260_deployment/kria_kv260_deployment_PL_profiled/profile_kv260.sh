#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VIDEO="${1:-test_videos/anomaly_sample.mp4}"
PYTHON="/usr/local/share/pynq-venv/bin/python3"
BITFILE="$SCRIPT_DIR/MobNet_kria_0.bit"

# PYNQ persists the last programmed bitstream path in global_pl_state.json.
# If this deployment directory was copied/renamed, that cache may still point
# at the previous directory and Overlay() fails before parsing the new .hwh.
# Clear the cache before launch; derive its location from the active PYNQ venv
# rather than hard-coding the Python minor version. The Python loader also has
# a retry fallback if Overlay() still encounters stale metadata.
PYNQ_STATE="$($PYTHON -c 'import os, pynq; print(os.path.join(os.path.dirname(pynq.__file__), "pl_server", "global_pl_state.json"))')"
sudo rm -f "$PYNQ_STATE"

sudo -E env \
  XILINX_XRT=/usr \
  PATH="/usr/local/share/pynq-venv/bin:$PATH" \
  KV260_VERBOSE=0 \
  "$PYTHON" \
  squeezenet_int8_inference.py \
  --bit "$BITFILE" \
  --profile \
  "$VIDEO"
