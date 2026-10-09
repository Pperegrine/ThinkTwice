"""Create deployment-only evaluator overlay and one unchanged official route."""
import difflib
import hashlib
import json
import io
from pathlib import Path
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[5]
repo = root / 'ThinkTwice'
dest = root / '.thinktwice-runtime/launch/20261009-smoke-v5'
dest.mkdir(parents=True, exist_ok=True)
source = repo / 'leaderboard/leaderboard/leaderboard_evaluator.py'
text = source.read_text(encoding='utf-8')
old = "cmd = 'DISPLAY= bash ' + os.path.join(self.carla_path, 'CarlaUE4.sh')+f' -opengl -carla-rpc-port={args.port} -nosound'"
new = "cmd = ['/bin/bash', os.environ['THINKTWICE_CARLA_LAUNCHER'], '-opengl', f'-carla-rpc-port={args.port}', '-nosound']"
assert text.count(old) == 1
patched = text.replace(old, new)
# The SIGINT bound method can retain the evaluator until interpreter shutdown.
# Its route cleanup has already completed before atexit stops the own server.
# Avoid a second destructor RPC to that stopped server; normal cleanup is intact.
old_destructor = '        self._cleanup()\n        if hasattr(self, \'manager\')'
assert patched.count(old_destructor) == 1
patched = patched.replace(old_destructor, "        if not getattr(self, '_deployment_cleanup_completed', False):\n            self._cleanup()\n        if hasattr(self, 'manager')")
cleanup_end = '            self.statistics_manager.scenario = None'
assert patched.count(cleanup_end) == 1
patched = patched.replace(cleanup_end, cleanup_end + '\n\n        self._deployment_cleanup_completed = True')
route_start = '        crash_message = ""'
assert patched.count(route_start) == 1
patched = patched.replace(route_start, '        self._deployment_cleanup_completed = False\n' + route_start)
old_spawn = 'server_process = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)'
assert patched.count(old_spawn) == 1
patched = patched.replace(old_spawn, 'server_process = subprocess.Popen(cmd, start_new_session=True)\n        _OWN_CARLA_PROCESSES.append(server_process)')
old_wait = '        time.sleep(wait_time)\n        self.client = carla.Client(args.host, int(args.port))'
assert patched.count(old_wait) == 1
patched = patched.replace(old_wait, '''        # Deployment readiness only: a failed early rpclib connection may not
        # reconnect. Use a fresh, bounded probe before the original client.
        ready_deadline = time.monotonic() + 180
        last_error = None
        while time.monotonic() < ready_deadline:
            if server_process.poll() is not None:
                raise RuntimeError('Own CARLA exited before RPC readiness')
            try:
                ready_client = carla.Client(args.host, int(args.port))
                ready_client.set_timeout(2.0)
                version = ready_client.get_server_version()
                print('CARLA RPC ready:', args.host, args.port, version, flush=True)
                del ready_client
                break
            except RuntimeError as exc:
                last_error = str(exc)
                time.sleep(2)
        else:
            raise RuntimeError('CARLA RPC readiness timed out: ' + str(last_error))
        self.client = carla.Client(args.host, int(args.port))''')
# Initialization wall-clock allowance only; simulation delta/control unchanged.
assert patched.count('self.world.tick()') == 1
assert patched.count('CarlaDataProvider.get_world().tick()') == 1
patched = patched.replace('self.world.tick()', 'self.world.tick(120.0)')
patched = patched.replace('CarlaDataProvider.get_world().tick()', 'CarlaDataProvider.get_world().tick(120.0)')
old_kill = "    kill_process = subprocess.Popen('killall -9 -r CarlaUE4-Linux', shell=True)\n    kill_process.wait()\n    time.sleep(5)"
assert patched.count(old_kill) == 1
patched = patched.replace(old_kill, '    _cleanup_own_carla()')
prefix = '''# Deployment overlay only; official model/agent/control sources unchanged.
import atexit
import os
import signal
_OWN_CARLA_PROCESSES = []
def _cleanup_own_carla():
    for process in _OWN_CARLA_PROCESSES:
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=15)
            except ProcessLookupError:
                pass
            except Exception:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
atexit.register(_cleanup_own_carla)

'''
future = 'from __future__ import print_function\n'
assert patched.count(future) == 1
patched = patched.replace(future, future + '\n' + prefix)
target = dest / 'leaderboard_evaluator_wsl.py'
if target.exists() and target.read_text(encoding='utf-8') != patched:
    raise RuntimeError('Existing overlay differs; preserved')
target.write_text(patched, encoding='utf-8')
diff = ''.join(difflib.unified_diff(text.splitlines(True), patched.splitlines(True),
                                  fromfile=str(source), tofile=str(target)))
(dest / 'evaluator-deployment.diff').write_text(diff, encoding='utf-8')
observer = root / 'ThinkTwice/docs/reproduction/env-agent/scripts/thinktwice_observed_agent.py'
observer_diff = ''.join(difflib.unified_diff([], observer.read_text(encoding='utf-8').splitlines(True),
                                           fromfile='/dev/null', tofile=str(observer)))
(dest / 'agent-observation.diff').write_text(observer_diff, encoding='utf-8')
route_source = repo / 'leaderboard/data/routes_for_evaluation/routes_town05_long.xml'
routes = ET.parse(str(route_source)).getroot()
selected = next(x for x in routes.findall('route') if x.attrib['town'] == 'Town05')
single = ET.Element('routes')
single.append(selected)
route_dest = dest / 'routes_town05_single.xml'
route_buffer = io.BytesIO()
ET.ElementTree(single).write(route_buffer, encoding='utf-8', xml_declaration=True)
payload = route_buffer.getvalue()
if route_dest.exists() and route_dest.read_bytes() != payload:
    raise RuntimeError('Existing single route differs; preserved')
route_dest.write_bytes(payload)
manifest = {'scope': 'Prepared only; no inference or route run',
            'evaluator_original_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'evaluator_overlay_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
            'route_source': str(route_source), 'selected_original_route': selected.attrib,
            'route_count': 1, 'route_sha256': hashlib.sha256(payload).hexdigest(),
            'deployment_changes': ['CARLA process-local graphics launcher', 'own process-group cleanup only',
                                   'bounded fresh-client RPC readiness before original client',
                                   'initialization tick wall-clock timeout120s, physics delta unchanged',
                                   'skip destructor duplicate RPC only after successful route cleanup; reset per route'],
            'diagnostic_wrapper_sha256': hashlib.sha256(observer.read_bytes()).hexdigest(),
            'diagnostic_changes': ['observer subclass calls original setup/run_step/forward; returns values unchanged',
                                   'save first real batch/output and record all six prediction levels plus controls'],
            'model_agent_control_changes': []}
(dest / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print(json.dumps(manifest, indent=2))
