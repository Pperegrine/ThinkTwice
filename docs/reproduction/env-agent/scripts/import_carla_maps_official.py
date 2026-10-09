"""Apply release ImportAssets.sh keep-newer semantics, preserving every archive."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

p = argparse.ArgumentParser()
p.add_argument('--assets', required=True)
p.add_argument('--root', default='/opt/thinktwice/carla-0.9.10.1')
p.add_argument('--output-dir', required=True)
a = p.parse_args()
root = Path(a.root).resolve()
assets = Path(a.assets).resolve()
out = Path(a.output_dir).resolve()
out.mkdir(exist_ok=True, parents=True)
if (out / 'official-import.json').exists():
    raise RuntimeError('Preserve prior run evidence')
# Initial overlay followed upstream TransFuser. Restore any newer base asset first
# so the result also respects the original CARLA ImportAssets.sh keep-newer rule.
restored = []
with tarfile.open(str(assets / 'CARLA_0.9.10.1.tar.gz'), 'r|gz') as tar:
    for m in tar:
        target = (root / m.name).resolve()
        if target != root and root not in target.parents:
            raise RuntimeError('Unsafe path')
        if m.isfile() and target.is_file() and target.stat().st_mtime < m.mtime:
            tar.extract(m, str(root))
            restored.append(m.name)
maps = root / 'Import/AdditionalMaps_0.9.10.1.tar.gz'
maps.parent.mkdir(exist_ok=True)
source = assets / maps.name
def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(8 * 1024**2), b''):
            h.update(b)
    return h.hexdigest()
if not maps.exists():
    shutil.copy2(str(source), str(maps))
if maps.stat().st_size != 1823090196 or sha(maps) != 'b64b1d7b92090de99913c7a221984d54c4c462275b4d727e8cd4a20dc529646c':
    raise RuntimeError('Import archive identity mismatch; preserved')
with (out / 'official-import-console.log').open('wb') as log:
    proc = subprocess.run(['/bin/bash', 'ImportAssets.sh'], cwd=str(root), stdout=log, stderr=subprocess.STDOUT)
r = {'pass': proc.returncode == 0, 'returncode': proc.returncode,
     'command': ['bash', 'ImportAssets.sh'], 'restored_newer_base_assets': restored,
     'retained_import_archive': str(maps), 'method': 'original release tar --keep-newer-files'}
(out / 'official-import.json').write_text(json.dumps(r, indent=2), encoding='utf-8')
print(json.dumps({'pass': r['pass'], 'restored_newer_base_count': len(restored), 'returncode': proc.returncode}), flush=True)
raise SystemExit(proc.returncode)
