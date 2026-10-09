"""Extract only CARLA's application directory from verified official image layers."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sys
import tarfile

root=Path.cwd()
ev=root/'ThinkTwice/docs/reproduction/env-agent/evidence/20261009-carla-assets'
assets=root/'.thinktwice-runtime/assets/carla-0.9.10.1-image'
dest=Path('/opt/thinktwice/carla-0.9.10.1')
dest.mkdir(parents=True,exist_ok=False)
manifest=json.loads((ev/'manifest.json').read_text())
count=0
size=0
for layer in manifest['layers']:
    blob=assets/(layer['digest'].split(':')[1]+'.blob')
    h=hashlib.sha256()
    with blob.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024**2),b''): h.update(chunk)
    if h.hexdigest()!=layer['digest'].split(':')[1]: raise RuntimeError('layer hash mismatch')
    print('EXTRACT_LAYER',layer['digest'],flush=True)
    with tarfile.open(str(blob),'r|gz') as tar:
        for member in tar:
            parts=PurePosixPath(member.name).parts
            if parts[:2]!=('home','carla') or len(parts)<3: continue
            rel=PurePosixPath(*parts[2:])
            if '..' in rel.parts: raise RuntimeError('unsafe path')
            target=dest/str(rel)
            if dest not in target.resolve().parents: raise RuntimeError('unsafe target')
            if rel.name.startswith('.wh.'):
                raise RuntimeError('CARLA-layer whiteout needs explicit handling: '+str(rel))
            if member.issym():
                link=(target.parent/member.linkname).resolve()
                if dest not in link.parents: raise RuntimeError('external CARLA symlink '+str(rel))
            if member.islnk():
                linkparts=PurePosixPath(member.linkname).parts
                if linkparts[:2]!=('home','carla'): raise RuntimeError('external hardlink')
                member.linkname=str(PurePosixPath(*linkparts[2:]))
            if not (member.isfile() or member.isdir() or member.issym() or member.islnk()):
                raise RuntimeError('unsupported special file '+str(rel))
            member.name=str(rel)
            tar.extract(member,str(dest))
            count+=1
            size+=member.size
report={'path':str(dest),'entries':count,'uncompressed_regular_bytes':size,
        'launcher':(dest/'CarlaUE4.sh').exists(),
        'shipping_binary':[str(p.relative_to(dest)) for p in dest.rglob('CarlaUE4-Linux-Shipping')],
        'python_api_eggs':[str(p.relative_to(dest)) for p in dest.rglob('*.egg')],
        'map_packages':[str(p.relative_to(dest)) for p in dest.rglob('*.pak')]}
(ev/'extraction-report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
