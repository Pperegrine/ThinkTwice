"""Independent CARLA API/map/clock acceptance; does not exercise ThinkTwice."""
import argparse
import glob
import json
import sys
import time
import traceback
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--carla-root', default='/opt/thinktwice/carla-0.9.10.1')
p.add_argument('--port', type=int, default=22123)
p.add_argument('--output', required=True)
p.add_argument('--traffic-manager', action='store_true', help='Diagnose original evaluator TM lifecycle')
a = p.parse_args()
r = {'scope': 'CARLA API, Town05, synchronous clock only', 'pass': False}
def persist(stage):
    r['stage'] = stage
    Path(a.output).write_text(json.dumps(r, indent=2), encoding='utf-8')
world = original = tm = None
try:
    eggs = glob.glob(a.carla_root + '/PythonAPI/carla/dist/carla-*-py3.7-linux-x86_64.egg')
    if len(eggs) != 1:
        raise RuntimeError('Expected exactly one original Python3.7 Linux egg: ' + repr(eggs))
    sys.path.insert(0, eggs[0])
    r['egg'] = eggs[0]
    import carla
    client = carla.Client('127.0.0.1', a.port)
    client.set_timeout(120.0)
    r.update(client_version=client.get_client_version(), server_version=client.get_server_version())
    persist('versions_connected')
    r['available_maps'] = client.get_available_maps()
    if a.traffic_manager:
        r['scope'] += ', original Traffic Manager lifecycle and seed2023'
        persist('creating_TM_before_map_load')
        tm = client.get_trafficmanager(22133)
        tm.set_synchronous_mode(False)
    persist('loading_Town05')
    world = client.load_world('Town05')
    r['map'] = world.get_map().name
    original = world.get_settings()
    settings = world.get_settings()
    settings.synchronous_mode = True
    settings.fixed_delta_seconds = 0.05
    world.apply_settings(settings)
    if tm is not None:
        world.reset_all_traffic_lights()
        persist('setting_TM_sync_and_seed')
        tm.set_synchronous_mode(True)
        tm.set_random_device_seed(2023)
    persist('synchronous_ticks')
    r['ticks'] = []
    for _ in range(10):
        begin = time.monotonic()
        frame = world.tick(120.0)
        snap = world.get_snapshot()
        r['ticks'].append({'frame': frame, 'snapshot_frame': snap.frame,
                           'elapsed_seconds': snap.timestamp.elapsed_seconds,
                           'delta_seconds': snap.timestamp.delta_seconds,
                           'wall_seconds': time.monotonic() - begin})
    ticks = r['ticks']
    assert 'Town05' in r['map']
    assert all(x['frame'] == x['snapshot_frame'] and abs(x['delta_seconds'] - 0.05) < 1e-6 for x in ticks)
    assert all(y['frame'] == x['frame'] + 1 for x, y in zip(ticks, ticks[1:]))
    r['pass'] = True
except Exception:
    r['error'] = traceback.format_exc()
finally:
    if world is not None and original is not None:
        try:
            if tm is not None:
                tm.set_synchronous_mode(False)
            world.apply_settings(original)
            r['settings_restored'] = True
        except Exception:
            r['settings_restored'] = False
            r['restore_error'] = traceback.format_exc()
    Path(a.output).write_text(json.dumps(r, indent=2), encoding='utf-8')
    print(json.dumps(r, indent=2), flush=True)
sys.exit(0 if r['pass'] else 1)
