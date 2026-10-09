"""Fetch fixed upstream gitlinks via official archive endpoints when git HTTPS is blocked."""
import configparser
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import time
import urllib.request

root=Path('/opt/thinktwice/src/pytorch-1.12.1')
cache=Path('/opt/thinktwice/assets/submodules')
cache.mkdir(parents=True,exist_ok=True)
manifest=[]
def get(url,dest):
    def validate(path):
        if str(path).endswith('.json') or dest.suffix == '.json':
            obj=json.loads(path.read_text())
            if 'tree' not in obj or obj.get('truncated'): raise RuntimeError('Incomplete git tree response')
        else:
            with tarfile.open(str(path),'r:gz') as archive:
                archive.getmembers()
                while archive.fileobj.read(8*1024**2): pass
    if dest.exists():
        try: validate(dest)
        except Exception:
            saved=dest.with_name(dest.name+'.invalid-'+str(time.time_ns()))
            dest.rename(saved)
            print('PRESERVED invalid cached archive',str(saved),flush=True)
    if not dest.exists():
        partial=dest.with_name(dest.name+'.part-'+str(time.time_ns()))
        subprocess.run(['curl','-fLsS','--retry','1','--connect-timeout','15','--max-time','120',url,'-o',str(partial)],check=True)
        validate(partial)
        partial.rename(dest)
    return dest.read_bytes()

def fetch_tree(base,repo,commit,depth=0):
    gm=base/'.gitmodules'
    if not gm.exists(): return
    cfg=configparser.ConfigParser()
    cfg.read(str(gm))
    treefile=cache/(repo.replace('/','_')+'_'+commit+'_tree.json')
    raw=get('https://api.github.com/repos/'+repo+'/git/trees/'+commit+'?recursive=1',treefile)
    tree=json.loads(raw)
    links={x['path']:x['sha'] for x in tree['tree'] if x['mode']=='160000'}
    for section in cfg.sections():
        path=cfg[section]['path']
        url=cfg[section]['url']
        sha=links.get(path)
        if sha is None: continue
        dest=base/path
        name=path.replace('/','_')+'_'+sha
        archive=cache/(name+'.tar.gz')
        if url.startswith('https://github.com/'):
            childrepo=url[len('https://github.com/'):].removesuffix('.git') if hasattr(str,'removesuffix') else url[len('https://github.com/'):].replace('.git','')
            archive_url='https://codeload.github.com/'+childrepo+'/tar.gz/'+sha
        elif url.startswith('https://gitlab.com/'):
            childrepo=None
            project=url[len('https://gitlab.com/'):].replace('.git','')
            archive_url='https://gitlab.com/'+project+'/-/archive/'+sha+'/source.tar.gz'
        else:
            raise RuntimeError('unsupported official submodule URL '+url)
        print('FETCH',path,sha,archive_url,flush=True)
        try:
            data=get(archive_url,archive)
            dest.mkdir(parents=True,exist_ok=True)
            with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as tar:
                for member in tar.getmembers():
                    pieces=member.name.split('/',1)
                    if len(pieces)!=2 or not pieces[1]: continue
                    member.name=pieces[1]
                    lexical_target=dest/member.name
                    target=lexical_target.resolve()
                    if dest.resolve() not in target.parents: raise RuntimeError('unsafe archive path')
                    if member.issym() or member.islnk():
                        # Upstream links must stay inside this extracted dependency.
                        link=((lexical_target.parent if member.issym() else dest)/member.linkname).resolve()
                        if dest.resolve() not in link.parents: raise RuntimeError('unsafe archive link')
                    tar.extract(member,str(dest))
            manifest.append({'path':str(dest),'gitlink':sha,'source':archive_url,'sha256':hashlib.sha256(data).hexdigest(),'pass':True})
            if childrepo: fetch_tree(dest,childrepo,sha,depth+1)
        except Exception as e:
            manifest.append({'path':str(dest),'gitlink':sha,'source':archive_url,'pass':False,'error':str(e)})
            print('FETCH FAILED',path,str(e),flush=True)
        (cache/'manifest.json').write_text(json.dumps(manifest,indent=2))

fetch_tree(root,'pytorch/pytorch','v1.12.1')
raise SystemExit(0 if all(x['pass'] for x in manifest) else 1)
