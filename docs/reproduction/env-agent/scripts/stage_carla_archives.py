"""Copy completed browser downloads into isolated assets; never touch partials."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time

parser=argparse.ArgumentParser()
parser.add_argument('--source',default='D:/Download')
args=parser.parse_args()
root=Path(__file__).resolve().parents[5]
dest=root/'.thinktwice-runtime/assets/carla-0.9.10.1-release'
dest.mkdir(parents=True,exist_ok=True)
ev=root/'ThinkTwice/docs/reproduction/env-agent/evidence/20261009-carla-release'
ev.mkdir(parents=True,exist_ok=True)
expected={'CARLA_0.9.10.1.tar.gz':3956990664,'AdditionalMaps_0.9.10.1.tar.gz':1823090196}
report={'source_directory':args.source,'assets':[],'space_free_before':shutil.disk_usage(dest).free}
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024**2),b''):h.update(chunk)
    return h.hexdigest()
for name,amount in expected.items():
    source=Path(args.source)/name
    target=dest/name
    record={'filename':name,'expected_bytes':amount,
            'source_url':'https://carla-releases.s3.us-east-005.backblazeb2.com/Linux/'+name}
    if not source.is_file() or source.stat().st_size!=amount:
        record.update({'status':'awaiting_completed_browser_download',
                       'observed_bytes':source.stat().st_size if source.is_file() else None})
    else:
        before=(source.stat().st_size,source.stat().st_mtime_ns)
        identity=sha(source)
        if before!=(source.stat().st_size,source.stat().st_mtime_ns):raise RuntimeError('source still changing')
        if target.exists():
            if target.stat().st_size!=amount or sha(target)!=identity:
                raise RuntimeError('existing isolated asset differs; preserved: '+str(target))
        else:
            if shutil.disk_usage(dest).free < amount+50*1024**3:raise RuntimeError('insufficient extraction/temp reserve')
            partial=target.with_suffix(target.suffix+'.staging')
            if partial.exists():raise RuntimeError('existing staging copy preserved: '+str(partial))
            shutil.copy2(str(source),str(partial))
            if partial.stat().st_size!=amount or sha(partial)!=identity:raise RuntimeError('copy verification failed')
            partial.replace(target)
        record.update({'status':'size_and_copy_hash_verified','bytes':amount,'sha256':identity,
                       'hash_scope':'local identity only; no official published checksum claimed',
                       'original_path':str(source),'isolated_path':str(target)})
    report['assets'].append(record)
report['space_free_after']=shutil.disk_usage(dest).free
(ev/'staging-status.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
raise SystemExit(0 if all(x['status']=='size_and_copy_hash_verified' for x in report['assets']) else 3)
