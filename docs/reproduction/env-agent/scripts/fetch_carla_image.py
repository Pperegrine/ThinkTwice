"""Fetch official CARLA Docker blobs without installing a container daemon."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request

root=Path(__file__).resolve().parents[5]
evidence=root/'ThinkTwice/docs/reproduction/env-agent/evidence/20261009-carla-assets'
dest=root/'.thinktwice-runtime/assets/carla-0.9.10.1-image'
dest.mkdir(parents=True,exist_ok=True)
manifest=json.loads((evidence/'manifest.json').read_text(encoding='utf-8-sig'))
proxy='http://127.0.0.1:7892'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({'http':proxy,'https':proxy}))
def token():
    with opener.open('https://auth.docker.io/token?service=registry.docker.io&scope=repository:carlasim/carla:pull',timeout=30) as r:
        return json.load(r)['token']
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''): h.update(block)
    return h.hexdigest()

total=sum(x['size'] for x in manifest['layers'])+manifest['config']['size']
print('Official carlasim/carla:0.9.10.1 compressed bytes',total,'free bytes',shutil.disk_usage(dest).free,flush=True)
if shutil.disk_usage(dest).free < total*2+20*1024**3: raise RuntimeError('insufficient reserved disk space')
records=[]
for i,blob in enumerate([manifest['config']]+manifest['layers']):
    sha=blob['digest'].split(':')[1]
    path=dest/(sha+'.blob')
    print('BLOB',i,'size',blob['size'],'sha256',sha,flush=True)
    if not path.exists() or path.stat().st_size!=blob['size'] or digest(path)!=sha:
        partial=path.with_suffix('.part')
        # Tokens are scoped public pull credentials, passed only to curl and never logged.
        result=subprocess.run(['curl.exe','-sS','-L','--fail','--retry','2','--retry-all-errors',
            '--connect-timeout','20','--max-time','900','--proxy',proxy,'-C','-',
            '-H','Authorization: Bearer '+token(),
            'https://registry-1.docker.io/v2/carlasim/carla/blobs/'+blob['digest'],
            '-o',str(partial)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        if result.returncode:
            print('DOWNLOAD_ERROR',result.returncode,result.stderr.decode(errors='replace'),flush=True)
            raise SystemExit(result.returncode)
        if partial.stat().st_size!=blob['size'] or digest(partial)!=sha:
            raise RuntimeError('size/SHA256 mismatch for '+sha)
        partial.replace(path)
    records.append({'digest':blob['digest'],'bytes':blob['size'],'path':str(path),'sha256_verified':True})
    (evidence/'download-manifest.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    print('VERIFIED',i,flush=True)
config=json.loads((dest/(manifest['config']['digest'].split(':')[1]+'.blob')).read_text())
(evidence/'image-config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
print('IMAGE_DOWNLOAD_COMPLETE','working_dir',config.get('config',{}).get('WorkingDir'),flush=True)
