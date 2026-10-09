"""Fix candidate identities and formal PTX tool output; not execution proof."""
import hashlib
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[5]
out = root / 'ThinkTwice/docs/reproduction/env-agent/evidence/20261009-takeover'
candidate = Path('/opt/thinktwice/candidate-site')
files = list(Path('/opt/thinktwice/src/mmcv-1.7.0/dist').glob('*.whl'))
files += list(Path('/opt/thinktwice/src/mmdetection3d-47285b3f1e9dba358e98fcd12e523cfd0769c876/dist').glob('*.whl'))
files += list((candidate / 'mmcv').glob('_ext*.so'))
records = []
for file in files:
    h = hashlib.sha256()
    with file.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    item = {'path': str(file), 'bytes': file.stat().st_size, 'sha256_local': h.hexdigest()}
    if file.suffix == '.so':
        log = out / 'mmcv-candidate-cuobjdump-list-ptx.txt'
        with log.open('w') as f:
            result = subprocess.run(['/opt/thinktwice/cuda113-ptx/bin/cuobjdump', '--list-ptx', str(file)],
                                    stdout=f, stderr=subprocess.STDOUT)
        item['cuobjdump_returncode'] = result.returncode
        item['ptx_listing'] = str(log)
        item['scope'] = 'PTX presence only; actual CUDA operator tests still required'
    records.append(item)
(out / 'candidate-identities.json').write_text(json.dumps(records, indent=2))
print(json.dumps(records, indent=2))
