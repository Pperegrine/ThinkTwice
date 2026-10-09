"""Use verified local large wheels and pin legacy runtime dependencies."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[5]
cache = root / '.thinktwice-runtime/assets/py37-wheels'
pins = {'matplotlib': '3.5.2', 'plotly': '5.18.0', 'pandas': '1.3.5',
        'scikit_learn': '1.0.2', 'scikit_image': '0.19.3', 'PyWavelets': '1.3.0'}
wheels = []
for name, version in pins.items():
    files = list(cache.glob(name + '-' + version + '-*.whl'))
    assert len(files) == 1, files
    wheels.append(str(files[0]))
report = root / 'ThinkTwice/docs/reproduction/env-agent/evidence/20261009-takeover/scientific-runtime-install02.json'
args = [sys.executable, '-m', 'pip', 'install', '--report', str(report)] + wheels
args += ['numpy==1.20.3', 'networkx==2.2', 'trimesh==2.35.39', 'Shapely==1.6.4.post2',
         'pyquaternion==0.9.9', 'cachetools==4.2.4', 'fire==0.5.0', 'descartes==1.1.0']
raise SystemExit(subprocess.call(args))
