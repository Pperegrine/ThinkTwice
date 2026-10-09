#!/bin/bash
# Source only in a ThinkTwice-Focal / ttenv shell. No system/global changes.
_tt_scripts="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_tt_root="$(cd "$_tt_scripts/../../../../.." && pwd)"
export PATH=/opt/thinktwice/conda/bin:/opt/thinktwice/cuda113-ptx/bin:$PATH
export CUDA_HOME=/opt/thinktwice/cuda113-ptx
export LD_LIBRARY_PATH=/opt/thinktwice/cudnn832-runtime/lib:/opt/thinktwice/cuda113-ptx/lib
export PYTHONPATH="/opt/thinktwice/candidate-site:/opt/thinktwice/voxel-candidate:$_tt_root/ThinkTwice:$_tt_root/ThinkTwice/open_loop_training:$_tt_root/ThinkTwice/leaderboard:$_tt_root/ThinkTwice/leaderboard/team_code:$_tt_root/ThinkTwice/scenario_runner"
export CUDA_CACHE_PATH=/opt/thinktwice/cuda-cache
export CUDA_CACHE_MAXSIZE=4294967296
export TORCH_HOME=/opt/thinktwice/torch-cache
export THINKTWICE_VOXEL_ROOT=/opt/thinktwice/voxel-candidate
export THINKTWICE_CARLA_LAUNCHER="$_tt_scripts/launch_carla_wsl_triangle_fix_v2.sh"
export BENCHMARK=town05long
export LANG=C.UTF-8 LC_ALL=C.UTF-8
unset _tt_scripts _tt_root
