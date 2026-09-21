#!/usr/bin/env bash
# install_figures.sh
#
# Installs or regenerates figures for centralized_ipc_hld.md into this directory.
#
# Usage (from repo root):
#   bash doc/modular-chassis-voq/img/install_figures.sh
#
# Optional: copy pre-rendered PNGs from an external assets directory:
#   SRC=/path/to/assets bash doc/modular-chassis-voq/img/install_figures.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DST="$SCRIPT_DIR"
mkdir -p "$DST"

if [[ -n "${SRC:-}" ]]; then
  if [[ ! -d "$SRC" ]]; then
    echo "Source assets directory not found: $SRC" >&2
    exit 1
  fi

  cp -v "$SRC/centralized_ipc_message_flow.png"           "$DST/centralized_ipc_message_flow.png"
  cp -v "$SRC/centralized_ipc_flow_steady_state.png"      "$DST/centralized_ipc_flow_steady_state.png"
  cp -v "$SRC/centralized_ipc_per_key_coalescing.png"     "$DST/centralized_ipc_per_key_coalescing.png"
  cp -v "$SRC/centralized_ipc_flow_cold_start.png"        "$DST/centralized_ipc_flow_cold_start.png"
  cp -v "$SRC/centralized_ipc_perf_hybrid_throughput.png" "$DST/centralized_ipc_perf_hybrid_throughput.png"

  if [[ -f "$SRC/zmq_redis_convergence_timing.png" ]]; then
    cp -v "$SRC/zmq_redis_convergence_timing.png" "$DST/zmq_redis_convergence_timing.png"
  fi
fi

if [[ ! -f "$DST/zmq_redis_convergence_timing.png" ]]; then
  python3 "$DST/gen_zmq_redis_convergence_timing.py"
fi

if [[ ! -f "$DST/centralized_ipc_frame_envelope.png" ]]; then
  python3 "$DST/gen_frame_envelope_figure.py"
fi

echo "Installed figures into $DST"
