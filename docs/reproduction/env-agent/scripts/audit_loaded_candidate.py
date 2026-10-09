"""Record loaded core library identity; reject old/source Torch core mixing."""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

p = argparse.ArgumentParser()
p.add_argument('--output', required=True)
p.add_argument('--extensions', action='store_true')
a = p.parse_args()
sys.path.insert(0, '/opt/thinktwice/voxel-candidate')
r = {'pass': False, 'scope': 'binary/import identity only, not numerical operator execution'}
try:
    import torch
    r['torch'] = {'version': torch.__version__, 'path': torch.__file__,
                  'cuda': torch.version.cuda, 'cudnn': torch.backends.cudnn.version(),
                  'abi': torch._C._GLIBCXX_USE_CXX11_ABI}
    assert torch.__file__.startswith('/opt/thinktwice/candidate-site/')
    modules = []
    if a.extensions:
        for name in ('mmcv._ext', 'torchvision._C', 'spconv.core_cc',
                     'ops.voxel_pooling.voxel_pooling_ext'):
            # torchvision _C is loaded via torch.ops, not a Python PyInit module.
            if name == 'torchvision._C':
                import torchvision
                assert torchvision.extension._has_ops()
                file = Path(torchvision.__file__).parent / '_C.so'
            else:
                module = importlib.import_module(name)
                file = Path(module.__file__)
            item = {'name': name, 'path': str(file), 'bytes': file.stat().st_size,
                    'sha256_local': hashlib.sha256(file.read_bytes()).hexdigest()}
            if file.suffix == '.so':
                result = subprocess.run(['readelf', '-d', str(file)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
                item['readelf_returncode'] = result.returncode
                item['needed'] = [line.strip() for line in result.stdout.splitlines() if '(NEEDED)' in line]
                assert result.returncode == 0
            modules.append(item)
    r['extensions'] = modules
    maps = Path('/proc/self/maps').read_text()
    paths = sorted(set(line.split()[-1] for line in maps.splitlines() if '/' in line))
    r['loaded_torch_core'] = [x for x in paths if '/libtorch' in x or '/libc10' in x]
    r['loaded_cuda_libraries'] = [x for x in paths if any(s in x for s in ('/libcuda', '/libcublas', '/libcusparse', '/libnvrtc'))]
    assert r['loaded_torch_core']
    assert all(x.startswith('/opt/thinktwice/candidate-site/torch/') for x in r['loaded_torch_core']), r['loaded_torch_core']
    r['driver_cache'] = {k: os.environ.get(k) for k in ('CUDA_CACHE_PATH', 'CUDA_CACHE_MAXSIZE')}
    r['pass'] = True
except Exception:
    r['error'] = traceback.format_exc()
Path(a.output).write_text(json.dumps(r, indent=2))
print(json.dumps(r, indent=2), flush=True)
raise SystemExit(0 if r['pass'] else 1)
