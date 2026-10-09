"""Validate gzip/tar and extract fixed release archives into a new dedicated directory."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import traceback

p = argparse.ArgumentParser()
p.add_argument('--assets', required=True)
p.add_argument('--target', default='/opt/thinktwice/carla-0.9.10.1')
p.add_argument('--output', required=True)
a = p.parse_args()
expected = {'CARLA_0.9.10.1.tar.gz': 3956990664,
            'AdditionalMaps_0.9.10.1.tar.gz': 1823090196}
target = Path(a.target).resolve()
stage = target.with_name(target.name + '.extracting')
r = {'target': str(target), 'archives': [], 'pass': False,
     'hash_scope': 'Local file identity, not an official checksum'}
previous = {}
if Path(a.output).is_file():
    previous = {x['filename']: x for x in json.loads(Path(a.output).read_text()).get('archives', [])}

def checked_members(tar, base):
    members = tar.getmembers()
    # Consume remaining gzip bytes, checking CRC/truncation beyond tar end markers.
    while tar.fileobj.read(8 * 1024**2):
        pass
    for m in members:
        dest = (base / m.name).resolve()
        if dest != base and base not in dest.parents:
            raise RuntimeError('Unsafe archive path: ' + m.name)
        if m.issym() or m.islnk():
            linkbase = dest.parent if m.issym() else base
            link = (linkbase / m.linkname).resolve()
            if link != base and base not in link.parents:
                raise RuntimeError('Unsafe archive link: ' + m.name)
        elif not (m.isfile() or m.isdir()):
            raise RuntimeError('Unsupported archive entry: ' + m.name)
    return members

try:
    if target.exists() or stage.exists():
        raise RuntimeError('Existing destination preserved; inspect before any retry')
    for name, size in expected.items():
        path = Path(a.assets) / name
        if path.stat().st_size != size:
            raise RuntimeError('Wrong archive size: ' + str(path))
        h = hashlib.sha256()
        with path.open('rb') as f:
            for chunk in iter(lambda: f.read(8 * 1024**2), b''):
                h.update(chunk)
        cached = previous.get(name, {})
        if cached.get('sha256') == h.hexdigest() and cached.get('gzip_tar_integrity'):
            item = cached.copy()
            item['reused_matching_hash_integrity_evidence'] = True
        else:
            with tarfile.open(str(path), 'r:gz') as tar:
                members = checked_members(tar, stage)
            item = {'filename': name, 'bytes': size, 'sha256': h.hexdigest(),
                    'entries': len(members), 'uncompressed_bytes': sum(m.size for m in members),
                    'gzip_tar_integrity': True, 'first_entries': [m.name for m in members[:10]],
                    'root_entries': sorted(set(m.name.split('/')[0] for m in members))}
            if name.startswith('AdditionalMaps') and any(m.name.split('/')[0] not in ('CarlaUE4', 'Engine') for m in members):
                raise RuntimeError('Unexpected maps layout; inspect import procedure')
        r['archives'].append(item)
        print(json.dumps(item), flush=True)
    needed = sum(x['uncompressed_bytes'] for x in r['archives']) + 10 * 1024**3
    r['linux_free_before'] = shutil.disk_usage(target.parent).free
    if r['linux_free_before'] < needed:
        raise RuntimeError('Insufficient Linux extraction reserve')
    stage.mkdir()
    for name in expected:
        # Full path/link validation above; streaming avoids repeatedly seeking compressed data.
        with tarfile.open(str(Path(a.assets) / name), 'r|gz') as tar:
            for member in tar:
                dest = (stage / member.name).resolve()
                if dest != stage and stage not in dest.parents:
                    raise RuntimeError('Unsafe extraction path: ' + member.name)
                tar.extract(member, str(stage))
    if not (stage / 'CarlaUE4.sh').is_file():
        raise RuntimeError('Missing CarlaUE4.sh')
    r['python_eggs'] = [x.name for x in (stage / 'PythonAPI/carla/dist').glob('*.egg')]
    if 'carla-0.9.10-py3.7-linux-x86_64.egg' not in r['python_eggs']:
        raise RuntimeError('Expected original egg filename not found')
    r['map_procedure'] = 'Extract AdditionalMaps overlay into release root, as upstream transfuser/2022/setup_carla.sh; archives preserved'
    stage.rename(target)
    r['pass'] = True
except Exception:
    r['error'] = traceback.format_exc()
finally:
    Path(a.output).write_text(json.dumps(r, indent=2), encoding='utf-8')
    print(json.dumps(r, indent=2), flush=True)
raise SystemExit(0 if r['pass'] else 1)
