"""Record installed candidate identity without launching new GPU kernels."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', required=True)
args = parser.parse_args()
output = Path(args.output).resolve()
assert not output.exists(), 'Preserve existing identity evidence'

import torch
import torchvision
import mmcv
import spconv
from mmcv import _ext

root = Path(__file__).resolve().parents[5]
paths = [Path(torch.__file__).parent / 'lib/libtorch_cuda.so', Path(torchvision._C.__file__) if hasattr(torchvision, '_C') else Path('/opt/thinktwice/candidate-site/torchvision/_C.so'),
         Path(_ext.__file__),
         Path('/opt/thinktwice/mesa24-triangle-fix-v2/lib/dri/swrast_dri.so'),
         root / 'thinktwice.pth']
report = {'scope': 'installed isolated candidate identity; hashes are local file identities',
          'python': {'executable': sys.executable, 'version': platform.python_version()},
          'torch': {'version': torch.__version__, 'path': torch.__file__, 'cuda': torch.version.cuda,
                    'abi': torch._C._GLIBCXX_USE_CXX11_ABI},
          'torchvision': {'version': torchvision.__version__, 'path': torchvision.__file__},
          'mmcv': {'version': mmcv.__version__, 'path': mmcv.__file__},
          'spconv': {'version': spconv.__version__, 'path': spconv.__file__},
          'libraries': [{'path': str(p), 'bytes': p.stat().st_size,
                         'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]}
output.write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2), flush=True)
