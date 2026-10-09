"""User-selected bounded smoke: observe >=200 inferences then graceful SIGINT.

Original route statistics are retained unchanged; bounded acceptance is separate.
No tick, settings, actor, model or control mutation is performed.
"""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import time
import traceback
import xml.etree.ElementTree as ET

p = argparse.ArgumentParser()
p.add_argument('--run-dir', required=True)
p.add_argument('--minimum-inferences', type=int, default=200)
p.add_argument('--output-name', default='smoke-acceptance.json')
a = p.parse_args()
run = Path(a.run_dir).resolve()
assert Path(a.output_name).name == a.output_name
output = run / a.output_name
assert not output.exists(), 'Preserve prior acceptance'
r = {'scope': 'user-selected short closed-loop smoke, not full route completion',
     'minimum_inferences': a.minimum_inferences, 'pass': False, 'started': time.time()}

def save():
    output.write_text(json.dumps(r, indent=2))

def events():
    lines = (run / 'sensor-inference/agent-events.jsonl').read_text().splitlines()
    parsed = []
    for i, line in enumerate(lines):
        try:
            parsed.append(json.loads(line))
        except ValueError:
            if i != len(lines) - 1:
                raise
    return parsed

try:
    expected = '--checkpoint=' + str(run / 'results.json')
    candidates = []
    for path in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            args = path.read_bytes().decode().split('\0')
            if expected in args and any(x.endswith('/leaderboard_evaluator_wsl.py') for x in args):
                assert path.stat().st_uid == os.getuid()
                candidates.append(int(path.parent.name))
        except (FileNotFoundError, PermissionError):
            continue
    assert len(candidates) == 1, candidates
    evaluator = candidates[0]
    r['own_evaluator_pid'] = evaluator
    save()
    while True:
        data = events()
        inf = [x for x in data if x['event'] == 'inference']
        controls = [x for x in data if x['event'] == 'control']
        failures = [x for x in data if x['event'] == 'failure']
        assert not failures, failures
        assert all(x['pass'] for x in inf) and all(x['valid'] for x in controls)
        r['inference_count_observed'] = len(inf)
        r['last_control_step'] = controls[-1]['step'] if controls else None
        save()
        if len(inf) >= a.minimum_inferences:
            break
        assert Path('/proc/%d/cmdline' % evaluator).exists(), 'Evaluator exited before threshold'
        time.sleep(3)
    import carla
    client = carla.Client('127.0.0.1', 22023)
    client.set_timeout(10.0)
    world = client.get_world()
    # A fresh CARLA client initially has frame0/empty actor cache until its
    # streaming snapshot arrives. Waiting observes the running evaluator;
    # it does not advance the simulation.
    world.wait_for_tick(10.0)
    heroes = [x for x in world.get_actors().filter('vehicle.*') if x.attributes.get('role_name') == 'hero']
    assert len(heroes) == 1, len(heroes)
    hero = heroes[0]
    loc, velocity = hero.get_location(), hero.get_velocity()
    snap = world.get_snapshot()
    r['readonly_live_probe'] = {'map': world.get_map().name, 'frame': snap.frame,
                                'elapsed_seconds': snap.timestamp.elapsed_seconds,
                                'fixed_delta_seconds': snap.timestamp.delta_seconds,
                                'ego_actor_id': hero.id, 'location': [loc.x, loc.y, loc.z],
                                'speed_m_s': math.sqrt(velocity.x**2 + velocity.y**2 + velocity.z**2),
                                'vehicle_actor_count': len(world.get_actors().filter('vehicle.*'))}
    route = ET.parse(str(run.parents[1] / 'launch/20261009-smoke-v5/routes_town05_single.xml')).getroot()
    first = route.find('route/waypoint')
    r['ego_displacement_from_route_start_m'] = math.hypot(loc.x-float(first.get('x')), loc.y-float(first.get('y')))
    assert r['readonly_live_probe']['map'] == 'Town05'
    assert all(math.isfinite(x) for x in r['readonly_live_probe']['location'])
    assert r['ego_displacement_from_route_start_m'] > 1.0
    # Verify identity again immediately before signaling only this evaluator.
    assert expected in Path('/proc/%d/cmdline' % evaluator).read_bytes().decode().split('\0')
    termination = {'reason': 'user_selected_short_smoke_threshold_reached',
                   'minimum_inferences': a.minimum_inferences, 'observed_before_signal': len(inf),
                   'signal': 'SIGINT to own original evaluator handler', 'evaluator_pid': evaluator,
                   'wall_time': time.time(), 'full_route_completion_requested': False}
    (run / 'termination.json').write_text(json.dumps(termination, indent=2))
    os.kill(evaluator, signal.SIGINT)
    r['termination'] = termination
    save()
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        raw = json.loads((run / 'run.json').read_text())
        if 'finished' in raw:
            break
        time.sleep(2)
    else:
        raise RuntimeError('Own evaluator did not finish graceful cleanup in180s')
    data = events()
    inf = [x for x in data if x['event'] == 'inference']
    controls = [x for x in data if x['event'] == 'control']
    failures = [x for x in data if x['event'] == 'failure']
    r['inference_count'] = len(inf)
    r['controls_count'] = len(controls)
    r['six_levels_all_finite'] = all(x['pass'] and all(len(v)==6 and all(v) for v in x['six_levels_finite'].values()) for x in inf)
    r['controls_all_valid'] = all(x['valid'] for x in controls)
    r['inference_steps_contiguous'] = all(y['step']==x['step']+1 for x,y in zip(inf, inf[1:]))
    r['failures'] = failures
    r['raw_full_route_statuses'] = raw.get('route_statuses')
    r['raw_route_progress_percent'] = raw.get('route_progress')
    r['raw_evaluator_returncode'] = raw.get('returncode')
    r['full_route_completed'] = raw.get('pass', False)
    r['pass'] = (len(inf)>=a.minimum_inferences and r['six_levels_all_finite'] and
                 r['controls_all_valid'] and r['inference_steps_contiguous'] and not failures and
                 bool(r['raw_route_progress_percent']) and r['raw_route_progress_percent'][0]>0 and
                 raw.get('returncode')==0 and not raw.get('server_abort'))
except Exception:
    r['error'] = traceback.format_exc()
finally:
    r['finished'] = time.time()
    save()
    print(json.dumps(r, indent=2), flush=True)
raise SystemExit(0 if r['pass'] else 1)
