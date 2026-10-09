"""Fresh official sources for linking against candidate Torch; old builds retained."""
import hashlib
import json
import posixpath
from pathlib import Path, PurePosixPath
import shutil
import tarfile

root = Path(__file__).resolve().parents[5]
assets = root / '.thinktwice-runtime/assets'
records = []
for archive, parent in (('mmcv-v1.7.0.tar.gz', '/opt/thinktwice/src/relink-mmcv'),
                        ('torchvision-v0.13.1.tar.gz', '/opt/thinktwice/src/relink-vision')):
    file = assets / archive
    dest = Path(parent)
    assert not dest.exists(), 'Existing directory preserved: ' + parent
    with tarfile.open(str(file), 'r:gz') as tar:
        members = tar.getmembers()
        for member in members:
            path = PurePosixPath(member.name)
            assert not path.is_absolute() and '..' not in path.parts, member.name
            assert not member.isdev() and not member.isfifo(), member.name
            if member.issym() or member.islnk():
                target = PurePosixPath(member.linkname)
                assert not target.is_absolute(), member.name
                joined = posixpath.join(str(path.parent), member.linkname) if member.issym() else member.linkname
                normalized = PurePosixPath(posixpath.normpath(joined))
                assert normalized.parts and normalized.parts[0] == path.parts[0] and '..' not in normalized.parts, member.name
        dest.mkdir(parents=True)
        tar.extractall(str(dest), members=members)
    records.append({'archive': str(file), 'sha256_local': hashlib.sha256(file.read_bytes()).hexdigest(),
                    'destination': parent, 'members': len(members)})
voxel = Path('/opt/thinktwice/src/relink-voxel')
assert not voxel.exists()
voxel.mkdir(parents=True)
source = root / 'ThinkTwice/open_loop_training'
shutil.copy2(str(source / 'setup.py'), str(voxel / 'setup.py'))
shutil.copytree(str(source / 'ops'), str(voxel / 'ops'),
                ignore=shutil.ignore_patterns('__pycache__', '*.so', '*.pyd', 'build', '*.egg-info'))
records.append({'source': str(source), 'destination': str(voxel), 'scope': 'unmodified official setup and ops source copy'})
out = root / 'ThinkTwice/docs/reproduction/env-agent/evidence/20261009-takeover/relink-sources.json'
out.write_text(json.dumps(records, indent=2))
print(json.dumps(records, indent=2))
