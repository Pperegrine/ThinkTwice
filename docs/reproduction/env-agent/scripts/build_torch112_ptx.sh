#!/bin/bash
set -euo pipefail
# Build a reviewable wheel first; never replace the installed torch implicitly.
cd /opt/thinktwice/src/pytorch-1.12.1
export PATH=/opt/thinktwice/conda/bin:/opt/thinktwice/cuda113-ptx/bin:$PATH
export CUDA_HOME=/opt/thinktwice/cuda113-ptx
export CUDA_TOOLKIT_ROOT_DIR=$CUDA_HOME
export CMAKE_PREFIX_PATH=/opt/thinktwice/conda:$CUDA_HOME
export CUDNN_INCLUDE_DIR=/opt/thinktwice/src/cudnn-v8.3.2.44
export CUDNN_LIBRARY=/opt/thinktwice/conda/lib/python3.7/site-packages/torch/lib/libcudnn.so.8
export CUDNN_LIB_DIR=/opt/thinktwice/cudnn832-link/lib
export LD_LIBRARY_PATH=$CUDA_HOME/lib:$CUDNN_LIB_DIR:/opt/thinktwice/conda/lib/python3.7/site-packages/torch/lib:${LD_LIBRARY_PATH:-}
export TORCH_CUDA_ARCH_LIST='8.6+PTX'
export PYTORCH_BUILD_VERSION=1.12.1
export PYTORCH_BUILD_NUMBER=1
export MAX_JOBS=${MAX_JOBS:-2}
export USE_CUDA=1 USE_CUDNN=1 BUILD_TEST=0 USE_DISTRIBUTED=0
export USE_NCCL=0 USE_GLOO=0 USE_MPI=0 USE_TENSORPIPE=0
export USE_KINETO=0 USE_NUMPY=1
export _GLIBCXX_USE_CXX11_ABI=0
python - <<'PY'
import json
from pathlib import Path
manifest=json.loads(Path('/opt/thinktwice/assets/submodules/manifest.json').read_text())
assert manifest and all(x['pass'] for x in manifest), 'Incomplete pinned submodules'
import yaml, numpy, typing_extensions
print('Source prerequisites checked; building wheel only',flush=True)
PY
python setup.py bdist_wheel --cmake
