"""Preserve old candidate module, validate new wheel CRC, install without deps."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

root = Path(__file__).resolve().parents[5]
wheel = Path('/opt/thinktwice/src/relink-mmcv/mmcv-1.7.0/dist/mmcv_full-1.7.0-cp37-cp37m-linux_x86_64.whl')
with zipfile.ZipFile(str(wheel)) as z:
    assert z.testzip() is None
    assert 'mmcv/_ext.cpython-37m-x86_64-linux-gnu.so' in z.namelist()
candidate = Path('/opt/thinktwice/candidate-site')
backup = Path('/opt/thinktwice/candidate-backups/mmcv-abi0-split')
backup.mkdir(parents=True, exist_ok=False)
items = [candidate / 'mmcv', candidate / 'mmcv_full-1.7.0.dist-info']
assert all(x.exists() for x in items)
for item in items:
    shutil.move(str(item), str(backup / item.name))
result = subprocess.run([sys.executable, '-m', 'pip', 'install', '--no-deps', '--target', str(candidate), str(wheel)])
report = {'wheel_crc_pass': True, 'old_candidate_preserved': str(backup),
          'returncode': result.returncode, 'pass': result.returncode == 0}
(root / 'ThinkTwice/docs/reproduction/env-agent/evidence/20261009-takeover/mmcv-candidate-install01.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
raise SystemExit(result.returncode)
