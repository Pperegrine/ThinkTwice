"""Clamp CUDA11.1-11.3 Jiterator targets to supported compute86 PTX.

No model/operator formula change. Preserve original source/installed CUDA library.
"""
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

root = Path('/opt/thinktwice/src/pytorch-1.12.1')
source = root / 'aten/src/ATen/native/cuda/jit_utils.cpp'
original = source.read_text()
old = '''    max_dev_version = CUDAVersion(8, 0);
  } else {
    // If the driver version is unknown'''
new = '''    max_dev_version = CUDAVersion(8, 0);
  } else if (nvrtc_version >= CUDAVersion(11, 1) &&
             nvrtc_version <= CUDAVersion(11, 3)) {
    // Deployment compatibility: these NVRTC versions support at most 8.6.
    // Future devices must receive forward-compatible PTX, not sm_120 SASS.
    max_dev_version = CUDAVersion(8, 6);
  } else {
    // If the driver version is unknown'''
assert original.count(old) == 1
backup = source.with_suffix('.cpp.before-nvrtc-arch-fix')
assert not backup.exists()
shutil.copy2(str(source), str(backup))
source.write_text(original.replace(old, new))
env = os.environ.copy()
env['PATH'] = '/opt/thinktwice/conda/bin:/opt/thinktwice/cuda113-ptx/bin:' + env['PATH']
env['LD_LIBRARY_PATH'] = '/opt/thinktwice/cuda113-ptx/lib:/opt/thinktwice/cudnn832-runtime/lib'
subprocess.run(['ninja', '-C', str(root / 'build'), '-j2', 'lib/libtorch_cuda.so'], env=env, check=True)
installed = Path('/opt/thinktwice/candidate-site/torch/lib/libtorch_cuda.so')
preserved = Path('/opt/thinktwice/candidate-backups/torch-before-nvrtc-arch-fix')
preserved.mkdir(parents=True, exist_ok=False)
shutil.copy2(str(installed), str(preserved / installed.name))
shutil.copy2(str(root / 'build/lib/libtorch_cuda.so'), str(installed))
evidence = Path(__file__).resolve().parent.parent / 'evidence/20261009-takeover'
diff = ''.join(difflib.unified_diff(original.splitlines(True), source.read_text().splitlines(True),
                                   fromfile=str(backup), tofile=str(source)))
(evidence / 'torch-nvrtc-arch-fix.diff').write_text(diff)
report = {'scope': 'CUDA runtime compilation target only, same torch1.12.1 ABI1',
          'installed_library': str(installed), 'bytes': installed.stat().st_size,
          'sha256': hashlib.sha256(installed.read_bytes()).hexdigest(),
          'backup': str(preserved / installed.name), 'source_backup': str(backup),
          'model_control_operator_formula_changes': [], 'runtime_validation': 'pending'}
(evidence / 'torch-nvrtc-arch-fix-build.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2), flush=True)
