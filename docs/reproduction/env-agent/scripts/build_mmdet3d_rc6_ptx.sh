#!/bin/bash
set -euo pipefail
cd /opt/thinktwice/src/mmdetection3d-47285b3f1e9dba358e98fcd12e523cfd0769c876
export PATH=/opt/thinktwice/conda/bin:/opt/thinktwice/cuda113-ptx/bin:$PATH
export CUDA_HOME=/opt/thinktwice/cuda113-ptx
export LD_LIBRARY_PATH=$CUDA_HOME/lib:/opt/thinktwice/conda/lib/python3.7/site-packages/torch/lib:${LD_LIBRARY_PATH:-}
export TORCH_CUDA_ARCH_LIST='8.6+PTX'
export MAX_JOBS=2 MMCV_WITH_OPS=1 FORCE_CUDA=1
python setup.py bdist_wheel
