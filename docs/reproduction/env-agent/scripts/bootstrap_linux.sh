#!/bin/bash
set -euo pipefail
root="$PWD"
logs="$root/ThinkTwice/docs/reproduction/env-agent/evidence/20261009-takeover"
exec > >(tee -a "$logs/linux-bootstrap.log") 2>&1
set -x
date -u
mkdir -p /opt/thinktwice
if [ ! -x /opt/thinktwice/conda/bin/python ]; then
  bash "$root/.thinktwice-runtime/assets/Miniconda3-py37_23.1.0-1-Linux-x86_64.sh" -b -p /opt/thinktwice/conda
fi
export PATH=/opt/thinktwice/conda/bin:$PATH
python --version
python -m pip install 'pip==24.0' 'setuptools==59.5.0' 'wheel==0.42.0'
python -m pip install 'numpy==1.20.3' 'typing_extensions==4.7.1' 'ninja==1.11.1.1'
python -m pip install 'torch==1.12.1+cu113' 'torchvision==0.13.1+cu113' --extra-index-url https://download.pytorch.org/whl/cu113
python "$root/ThinkTwice/docs/reproduction/env-agent/scripts/probe_basics.py" "$logs/linux-basics.json"
