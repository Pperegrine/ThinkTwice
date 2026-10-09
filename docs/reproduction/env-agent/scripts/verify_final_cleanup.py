"""Read-only final verification of this dedicated distro after bounded smoke."""
import json
import os
from pathlib import Path
import time

root = Path(__file__).resolve().parents[5]
run = root / '.thinktwice-runtime/runs/20261009-smoke13-cleanup-final'
acceptance = json.loads((run / 'smoke-acceptance.json').read_text())
raw = json.loads((run / 'run.json').read_text())
assert acceptance['pass'] and raw['returncode'] == 0 and not raw.get('server_abort')
remaining = []
for path in Path('/proc').glob('[0-9]*/cmdline'):
    try:
        args = path.read_bytes().decode(errors='replace').split('\0')
        if int(path.parent.name) == os.getpid():
            continue
        targets = ('CarlaUE4-Linux-Shipping', 'leaderboard_evaluator_wsl.py',
                   'run_single_route_smoke.py', 'finish_short_smoke.py')
        if any(Path(arg).name in targets for arg in args if arg):
            remaining.append({'pid': int(path.parent.name), 'args': args})
    except (FileNotFoundError, PermissionError):
        continue
disk = os.statvfs(str(root))
report = {'pass': not remaining, 'time': time.time(),
          'scope': 'read-only dedicated ThinkTwice-Focal process inventory',
          'remaining_smoke_processes': remaining,
          'project_volume_available_bytes': disk.f_bavail * disk.f_frsize,
          'evaluator_returncode': raw['returncode'], 'bounded_smoke_pass': acceptance['pass']}
target = run / 'cleanup-verification.json'
assert not target.exists(), 'Preserve existing verification'
target.write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2), flush=True)
raise SystemExit(0 if report['pass'] else 1)
