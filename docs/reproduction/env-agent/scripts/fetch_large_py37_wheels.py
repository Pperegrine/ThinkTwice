"""Fetch official PyPI wheels with published JSON SHA256 using existing explicit proxy."""
import hashlib
import json
from pathlib import Path
import subprocess
import argparse

base = Path(__file__).resolve().parents[5] / '.thinktwice-runtime/assets/py37-wheels'
base.mkdir(exist_ok=True, parents=True)
records = []
parser = argparse.ArgumentParser()
parser.add_argument('packages', nargs='*', help='name==version')
args = parser.parse_args()
packages = [tuple(x.split('==')) for x in args.packages] if args.packages else [('scipy', '1.7.3'), ('matplotlib', '3.5.3')]
for name, version in packages:
    meta = base / (name + '-' + version + '.json')
    cmd = ['curl.exe', '--proxy', 'http://127.0.0.1:7892', '-fLsS',
           '--connect-timeout', '10', '--max-time', '60']
    subprocess.run(cmd + ['https://pypi.org/pypi/%s/%s/json' % (name, version), '-o', str(meta)], check=True)
    urls = json.loads(meta.read_text(encoding='utf-8'))['urls']
    choices = [x for x in urls if 'cp37-cp37m-manylinux' in x['filename'] and 'x86_64' in x['filename']]
    if not choices:
        choices = [x for x in urls if x['filename'].endswith(('py3-none-any.whl', 'py2.py3-none-any.whl'))]
    if len(choices) > 1:
        older_abi = [x for x in choices if 'manylinux2010' in x['filename']]
        if len(older_abi) == 1:
            choices = older_abi
    assert len(choices) == 1, [x['filename'] for x in choices]
    item = choices[0]
    dest = base / item['filename']
    expected = item['digests']['sha256']
    if not dest.exists():
        part = dest.with_name(dest.name + '.part')
        subprocess.run(cmd + ['--continue-at', '-', item['url'], '-o', str(part)], check=True)
        assert part.stat().st_size == item['size']
        assert hashlib.sha256(part.read_bytes()).hexdigest() == expected
        part.rename(dest)
    assert hashlib.sha256(dest.read_bytes()).hexdigest() == expected
    records.append({'filename': dest.name, 'url': item['url'], 'sha256': expected,
                    'bytes': dest.stat().st_size, 'checksum_source': 'official PyPI release JSON'})
    print(json.dumps(records[-1]), flush=True)
manifest = base / 'manifest.json'
previous = json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else []
merged = {x['filename']: x for x in previous + records}
manifest.write_text(json.dumps(list(merged.values()), indent=2), encoding='utf-8')
