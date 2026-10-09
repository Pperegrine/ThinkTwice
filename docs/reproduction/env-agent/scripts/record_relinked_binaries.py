"""Formal final candidate extension identities, separate from old split builds."""
import hashlib
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[5]
out = root / 'ThinkTwice/docs/reproduction/env-agent/evidence/20261009-takeover'
files = [Path('/opt/thinktwice/voxel-candidate/ops/voxel_pooling/voxel_pooling_ext.cpython-37m-x86_64-linux-gnu.so'),
         Path('/opt/thinktwice/candidate-site/mmcv/_ext.cpython-37m-x86_64-linux-gnu.so'),
         Path('/opt/thinktwice/candidate-site/torchvision/_C.so')]
records = []
for index, file in enumerate(files):
    record = {'path': str(file), 'bytes': file.stat().st_size,
              'sha256_local': hashlib.sha256(file.read_bytes()).hexdigest()}
    result = subprocess.run(['readelf', '-d', str(file)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    record['readelf_returncode'] = result.returncode
    record['needed'] = [line.strip() for line in result.stdout.splitlines() if '(NEEDED)' in line]
    assert result.returncode == 0
    assert not any('libtorch_cuda_cu.so' in x or 'libtorch_cuda_cpp.so' in x for x in record['needed'])
    log = out / ('relinked-extension-%d-cuobjdump-ptx.txt' % index)
    with log.open('w') as f:
        result = subprocess.run(['/opt/thinktwice/cuda113-ptx/bin/cuobjdump', '--list-ptx', str(file)], stdout=f, stderr=subprocess.STDOUT)
    assert result.returncode == 0
    record['ptx_listing'] = str(log)
    record['scope'] = 'PTX and link identity only, not numerical execution'
    records.append(record)
(out / 'relinked-extension-identities.json').write_text(json.dumps(records, indent=2))
print(json.dumps(records, indent=2))
