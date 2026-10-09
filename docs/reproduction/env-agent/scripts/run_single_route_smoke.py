"""Run one unchanged official route only after explicit passing CUDA gates."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import time

p = argparse.ArgumentParser()
p.add_argument('--output-dir', required=True)
p.add_argument('--basics', required=True)
p.add_argument('--deform', required=True)
p.add_argument('--dcn', required=True)
p.add_argument('--spconv', required=True)
p.add_argument('--voxel', required=True)
p.add_argument('--lidar', required=True)
p.add_argument('--identity', required=True)
p.add_argument('--model', required=True)
p.add_argument('--replay', required=True, help='Passing real sensor replay with exact current CUDA library')
p.add_argument('--short-smoke-inferences', type=int, default=200,
               help='User-selected bounded smoke; 0 only for an explicitly requested full route')
p.add_argument('--carla-launcher', help='Optional deployment diagnostic launcher; model/control unchanged')
a = p.parse_args()
root = Path(__file__).resolve().parents[5]
scripts = Path(__file__).resolve().parent
repo = root / 'ThinkTwice'
assert os.getuid() != 0, 'Use dedicated ttenv user'
gates = {}
for label in ('basics', 'deform', 'dcn', 'spconv', 'voxel', 'lidar', 'identity', 'model'):
    file = Path(getattr(a, label)).resolve()
    value = json.loads(file.read_text())
    passed = all(x['pass'] for x in value['stages'].values()) if label == 'basics' else value['pass']
    assert passed, 'Failed gate: ' + label
    if label == 'basics':
        torch_path = value['stages']['cpu_tensor_numpy']['result']['torch_file']
    elif label in ('lidar', 'identity', 'model'):
        torch_path = value['torch']['path']
    else:
        torch_path = value['torch_file']
    assert torch_path.startswith('/opt/thinktwice/candidate-site/'), (label, torch_path)
    if label == 'model':
        assert value['refine_num'] == 5 and value['parameter_devices'] == ['cuda:0']
    gates[label] = {'path': str(file), 'sha256': hashlib.sha256(file.read_bytes()).hexdigest()}
import torch
assert torch.__file__.startswith('/opt/thinktwice/candidate-site/'), torch.__file__
assert torch.__version__.split('+')[0] == '1.12.1'
replay_path = Path(a.replay).resolve()
replay = json.loads(replay_path.read_text())
assert replay['pass'] and replay['refine_num'] == 5
cuda_library = Path('/opt/thinktwice/candidate-site/torch/lib/libtorch_cuda.so')
assert replay['libtorch_cuda_sha256'] == hashlib.sha256(cuda_library.read_bytes()).hexdigest()
gates['real_batch_replay'] = {'path': str(replay_path),
                            'sha256': hashlib.sha256(replay_path.read_bytes()).hexdigest(),
                            'current_cuda_library_sha256': replay['libtorch_cuda_sha256']}
out = Path(a.output_dir).resolve()
out.mkdir(parents=True, exist_ok=False)
launch = root / '.thinktwice-runtime/launch/20261009-smoke-v5'
route = launch / 'routes_town05_single.xml'
env = os.environ.copy()
env.update({'CARLA_ROOT': '/opt/thinktwice/carla-0.9.10.1',
            'CUDA_VISIBLE_DEVICES': '0',
            'CUDA_CACHE_PATH': '/opt/thinktwice/cuda-cache',
            'CUDA_CACHE_MAXSIZE': '4294967296',
            'TORCH_HOME': '/opt/thinktwice/torch-cache',
            'BENCHMARK': 'town05long', 'ROUTES': str(route),
            'SAVE_PATH': str(out / 'original-agent-records'),
            'THINKTWICE_SENSOR_EVIDENCE': str(out / 'sensor-inference'),
            'THINKTWICE_CARLA_LAUNCHER': str(Path(a.carla_launcher).resolve() if a.carla_launcher else scripts / 'launch_carla_wsl_triangle_fix_v2.sh'),
            'THINKTWICE_VOXEL_ROOT': '/opt/thinktwice/voxel-candidate',
            'PYTHONPATH': ':'.join(['/opt/thinktwice/candidate-site', '/opt/thinktwice/voxel-candidate',
                                    str(repo), str(repo / 'leaderboard'),
                                    str(repo / 'leaderboard/team_code'), str(repo / 'scenario_runner'),
                                    str(repo / 'open_loop_training')]),
            'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8'})
command = [sys.executable, '-u', '-X', 'faulthandler', str(launch / 'leaderboard_evaluator_wsl.py'),
           '--scenarios=' + str(repo / 'leaderboard/data/scenarios/all_towns_traffic_scenarios_no256.json'),
           '--routes=' + str(route), '--repetitions=1', '--track=SENSORS',
           '--checkpoint=' + str(out / 'results.json'),
           '--agent=' + str(scripts / 'thinktwice_observed_agent.py'),
           '--agent-config=' + str(root / 'thinktwice.pth') + '+' + str(repo / 'open_loop_training/configs/thinktwice.py'),
           '--debug=0', '--record=', '--resume=False', '--host=127.0.0.1', '--port=22023',
           '--trafficManagerPort=22033', '--is_local=True', '--is_eval=True']
report = {'scope': 'one original route16 Town05, full five refinements and original controls',
          'command': command, 'gates': gates, 'started': time.time(), 'pass': False,
          'torch': {'version': torch.__version__, 'path': torch.__file__}}
(out / 'run.json').write_text(json.dumps(report, indent=2))
with (out / 'console.log').open('w') as console:
    process = subprocess.Popen(command, cwd=str(repo), env=env, stdout=console, stderr=subprocess.STDOUT)
    server_pid = None
    server_exit_seen_at = None
    finisher = None
    finisher_log = None
    while process.poll() is None:
        if (a.short_smoke_inferences > 0 and finisher is None and
                (out / 'sensor-inference/agent-events.jsonl').exists()):
            finisher_log = (out / 'short-smoke-finisher.log').open('w')
            finisher = subprocess.Popen([sys.executable, str(scripts / 'finish_short_smoke.py'),
                                         '--run-dir', str(out), '--minimum-inferences',
                                         str(a.short_smoke_inferences)],
                                        env=env, stdout=finisher_log, stderr=subprocess.STDOUT)
        if finisher is not None and finisher.poll() not in (None, 0):
            report['short_smoke_observer_error'] = 'See short-smoke-finisher.log; stopping own evaluator'
            process.send_signal(__import__('signal').SIGINT)
            # Do not repeatedly signal or accidentally expand to a full route.
            finisher = None
            a.short_smoke_inferences = -1
        # Observe only this evaluator's server. Abort failed runs instead of
        # waiting the original 6000s RPC timeout after the server has exited.
        content = (out / 'console.log').read_text(errors='replace')
        if server_pid is None:
            match = re.search(r'^Process ID:\s*(\d+)', content, re.MULTILINE)
            if match:
                candidate_pid = int(match.group(1))
                stat = Path('/proc/%d/stat' % candidate_pid)
                if stat.exists():
                    fields = stat.read_text().rsplit(')', 1)[1].split()
                    assert int(fields[1]) == process.pid, 'Server must belong to this evaluator'
                server_pid = candidate_pid
                report['server_pid'] = server_pid
        if server_pid is not None:
            stat = Path('/proc/%d/stat' % server_pid)
            exited = not stat.exists() or stat.read_text().rsplit(')', 1)[1].split()[0] == 'Z'
            if exited and server_exit_seen_at is None:
                server_exit_seen_at = time.monotonic()
            # Original cleanup closes the own server before evaluator atexit
            # completes. Give deliberate bounded termination its full cleanup
            # window; an unexpected native crash still uses the short grace.
            deliberate_stop = (out / 'termination.json').exists()
            grace = 60 if deliberate_stop else 10
            if exited and time.monotonic() - server_exit_seen_at > grace and process.poll() is None:
                report['server_abort'] = 'Own CARLA launcher exited while evaluator still running; see console for native error'
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                break
        time.sleep(2)
report['returncode'] = process.returncode
report['finished'] = time.time()
results = out / 'results.json'
if results.exists():
    evaluation = json.loads(results.read_text())
    report['evaluation'] = evaluation
    records = evaluation.get('_checkpoint', {}).get('records', [])
    report['route_statuses'] = [x.get('status') for x in records]
    report['route_progress'] = [x.get('scores', {}).get('score_route') for x in records]
    report['pass'] = process.returncode == 0 and len(records) == 1 and records[0].get('status') == 'Completed'
events = out / 'sensor-inference/agent-events.jsonl'
if events.exists():
    parsed = [json.loads(line) for line in events.read_text().splitlines()]
    inference = [x for x in parsed if x['event'] == 'inference']
    controls = [x for x in parsed if x['event'] == 'control']
    failures = [x for x in parsed if x['event'] == 'failure']
    report['sensor_gate'] = bool(inference) and all(x['pass'] for x in inference)
    report['inference_calls'] = len(inference)
    report['controls_valid'] = bool(controls) and all(x['valid'] for x in controls)
    report['failures'] = failures
    report['pass'] = report['pass'] and report['sensor_gate'] and report['controls_valid'] and not failures
else:
    report['pass'] = False
    report['sensor_gate'] = False
(out / 'run.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2), flush=True)
if finisher is not None:
    finisher.wait(timeout=30)
    if finisher_log is not None:
        finisher_log.close()
    acceptance = json.loads((out / 'smoke-acceptance.json').read_text())
    # Keep raw full-route run.json unchanged. This is a separate bounded gate.
    raise SystemExit(0 if finisher.returncode == 0 and acceptance['pass'] else 1)
raise SystemExit(0 if report['pass'] else 1)
