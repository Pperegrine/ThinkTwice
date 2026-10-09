#!/bin/bash
set -euo pipefail
root="$PWD"
logs="$root/ThinkTwice/docs/reproduction/env-agent/evidence/20261009-takeover"
exec > >(tee -a "$logs/install-ops.log") 2>&1
export PATH=/opt/thinktwice/conda/bin:/opt/thinktwice/cuda113-ptx/bin:/usr/bin:/bin
export CUDA_HOME=/opt/thinktwice/cuda113-ptx
export LD_LIBRARY_PATH=/usr/lib/wsl/lib:$CUDA_HOME/lib64
export TORCH_CUDA_ARCH_LIST='8.6+PTX'
export MAX_JOBS=2
mkdir -p /opt/thinktwice/assets /opt/thinktwice/build
cp /mnt/d/wheels/mmcv_full.whl /opt/thinktwice/assets/mmcv_full-1.7.0-cp37-cp37m-manylinux1_x86_64.whl
python -m pip install /opt/thinktwice/assets/mmcv_full-1.7.0-cp37-cp37m-manylinux1_x86_64.whl 'spconv-cu113==2.3.6'
python -m pip freeze > "$logs/pip-freeze-ops.txt"
python "$root/ThinkTwice/docs/reproduction/env-agent/scripts/probe_ops.py" --op deform --repo "$root/ThinkTwice" --output "$logs/deform-prebuilt.json" || true
python "$root/ThinkTwice/docs/reproduction/env-agent/scripts/probe_ops.py" --op spconv --repo "$root/ThinkTwice" --output "$logs/spconv-prebuilt.json" || true
# Copy unchanged official sources into a Linux build directory; no in-repo artifacts.
cp -a "$root/ThinkTwice/open_loop_training/ops" /opt/thinktwice/build/
cp "$root/ThinkTwice/open_loop_training/setup.py" /opt/thinktwice/build/
cd /opt/thinktwice/build
python setup.py build_ext --inplace > "$logs/voxel-build.log" 2>&1
python "$root/ThinkTwice/docs/reproduction/env-agent/scripts/probe_ops.py" --op voxel --repo /opt/thinktwice --output "$logs/voxel-ptx.json"
