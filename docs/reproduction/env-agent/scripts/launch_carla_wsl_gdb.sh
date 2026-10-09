#!/bin/bash
set -euo pipefail
test "$(id -u)" -ne 0
# Diagnostic-only launch of the same shipping executable and original arguments.
exec env DISPLAY=:0 \
  LD_LIBRARY_PATH=/opt/thinktwice/mesa24/lib:/usr/lib/wsl/lib \
  LIBGL_DRIVERS_PATH=/opt/thinktwice/mesa24/lib/dri \
  GALLIUM_DRIVER=d3d12 MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA \
  allow_glsl_cross_stage_interpolation_mismatch=true \
  /usr/bin/gdb --batch \
  -ex 'set pagination off' -ex 'set print thread-events off' \
  -ex 'handle SIGPIPE nostop noprint pass' \
  -ex run -ex 'thread apply all bt 12' -ex 'info sharedlibrary' \
  --args /opt/thinktwice/carla-0.9.10.1/CarlaUE4/Binaries/Linux/CarlaUE4-Linux-Shipping CarlaUE4 "$@"
