#!/bin/bash
set -euo pipefail
if [ "$(id -u)" -eq 0 ]; then
  echo 'Run CARLA under dedicated ttenv user in ThinkTwice-Focal.' >&2
  exit 2
fi
# Deployment-only wrapper: original shipping binary/assets/shaders stay unchanged.
exec env DISPLAY=:0 \
  LD_LIBRARY_PATH=/opt/thinktwice/mesa24/lib:/usr/lib/wsl/lib \
  LIBGL_DRIVERS_PATH=/opt/thinktwice/mesa24/lib/dri \
  GALLIUM_DRIVER=d3d12 MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA \
  allow_glsl_cross_stage_interpolation_mismatch=true \
  /bin/bash /opt/thinktwice/carla-0.9.10.1/CarlaUE4.sh "$@"
