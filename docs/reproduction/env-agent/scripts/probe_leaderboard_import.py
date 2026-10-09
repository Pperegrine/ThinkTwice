"""Import gate only, no CARLA process or route execution."""
import argparse
import importlib
import json
import os
from pathlib import Path
import sys
import traceback

p = argparse.ArgumentParser()
p.add_argument('--output', required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[5]
repo = root / 'ThinkTwice'
os.environ.setdefault('BENCHMARK', 'town05long')
sys.path[:0] = [os.environ.get('THINKTWICE_VOXEL_ROOT', '/opt/thinktwice/build'), str(repo), str(repo / 'leaderboard'),
                str(repo / 'scenario_runner'), str(repo / 'open_loop_training')]
r = {'scope': 'import only; no route or sensor inference', 'pass': False, 'modules': []}
try:
    for name in ('leaderboard.leaderboard_evaluator', 'team_code.thinktwice_agent',
                 'thinktwice_observed_agent'):
        module = importlib.import_module(name)
        r['modules'].append({'name': name, 'path': module.__file__})
    import py_compile
    py_compile.compile(str(root / '.thinktwice-runtime/launch/20261009-smoke-v2/leaderboard_evaluator_wsl.py'), doraise=True)
    r['overlay_python37_syntax'] = True
    r['pass'] = True
except Exception:
    r['error'] = traceback.format_exc()
Path(a.output).write_text(json.dumps(r, indent=2), encoding='utf-8')
print(json.dumps(r, indent=2), flush=True)
raise SystemExit(0 if r['pass'] else 1)
