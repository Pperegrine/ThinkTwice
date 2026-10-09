#!/bin/bash
set -euo pipefail
export PATH=/opt/thinktwice/conda/bin:/opt/thinktwice/cuda113-ptx/bin:$PATH
export PYTHONPATH=/opt/thinktwice/candidate-site
export CUDA_HOME=/opt/thinktwice/cuda113-ptx
export LD_LIBRARY_PATH=/opt/thinktwice/cudnn832-runtime/lib:$CUDA_HOME/lib
export TORCH_CUDA_ARCH_LIST='8.6+PTX'
export MAX_JOBS=${MAX_JOBS:-2} FORCE_CUDA=1
python -c 'import torch; assert torch.__file__.startswith("/opt/thinktwice/candidate-site/"); assert torch.__version__.split("+")[0] == "1.12.1"; print(torch.__file__, flush=True)'
case "$1" in
  mmcv)
    cd /opt/thinktwice/src/relink-mmcv/mmcv-1.7.0
    export MMCV_WITH_OPS=1
    python setup.py bdist_wheel
    ;;
  vision)
    cd /opt/thinktwice/src/relink-vision/vision-0.13.1
    export BUILD_VERSION=0.13.1
    python setup.py bdist_wheel
    ;;
  voxel)
    cd /opt/thinktwice/src/relink-voxel
    python setup.py build_ext --build-lib /opt/thinktwice/voxel-candidate
    if [ -f ops/__init__.py ]; then
      cp ops/__init__.py /opt/thinktwice/voxel-candidate/ops/
    fi
    cp ops/voxel_pooling/{__init__.py,voxel_pooling.py} /opt/thinktwice/voxel-candidate/ops/voxel_pooling/
    ;;
  *) echo 'Expected mmcv, vision, or voxel' >&2; exit 2 ;;
esac
