"""Run only the dedicated CARLA process group, probe API, then stop own group."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import time
import traceback

p = argparse.ArgumentParser()
p.add_argument('--output-dir', required=True)
p.add_argument('--root', default='/opt/thinktwice/carla-0.9.10.1')
p.add_argument('--display', default='')
p.add_argument('--diagnostic-logging', action='store_true')
p.add_argument('--launcher')
p.add_argument('--traffic-manager', action='store_true')
a = p.parse_args()
out = Path(a.output_dir).resolve()
out.mkdir(parents=True, exist_ok=True)
logpath = out / 'server-console.log'
if logpath.exists():
    raise RuntimeError('Existing run evidence preserved; choose a new output directory')
cmd = ['/bin/bash', a.root + '/CarlaUE4.sh', '-opengl', '-carla-rpc-port=22123', '-nosound']
if a.launcher:
    cmd[1] = str(Path(a.launcher).resolve())
if a.diagnostic_logging:
    cmd += ['-stdout', '-FullStdOutLogOutput', '-unattended']
r = {'command': cmd, 'display': a.display, 'uid': os.getuid(), 'pass': False}
r['graphics_environment'] = {k: os.environ.get(k) for k in (
    'LD_LIBRARY_PATH', 'LIBGL_DRIVERS_PATH', 'MESA_LOADER_DRIVER_OVERRIDE',
    'GALLIUM_DRIVER', 'MESA_D3D12_DEFAULT_ADAPTER_NAME', 'LD_PRELOAD',
    'allow_glsl_cross_stage_interpolation_mismatch')}
proc = None
try:
    if os.getuid() == 0:
        raise RuntimeError('Unreal must run under dedicated non-root user')
    env = os.environ.copy()
    env['DISPLAY'] = a.display
    if a.diagnostic_logging:
        env.update(LIBGL_DEBUG='verbose', MESA_DEBUG='1')
    with logpath.open('wb') as log:
        proc = subprocess.Popen(cmd, cwd=a.root, env=env, stdout=log, stderr=subprocess.STDOUT,
                                start_new_session=True)
        r['pid'] = proc.pid
        print('CARLA PID', proc.pid, 'console', str(logpath), flush=True)
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise RuntimeError('Server exited before RPC ready, return code ' + str(proc.returncode))
            try:
                with socket.create_connection(('127.0.0.1', 22123), timeout=1):
                    break
            except OSError:
                time.sleep(2)
        else:
            raise RuntimeError('RPC not ready within 180 seconds')
        probe = Path(__file__).with_name('probe_carla_sync.py')
        probe_command = [os.sys.executable, str(probe), '--carla-root', a.root,
                         '--output', str(out / 'sync-probe.json')]
        if a.traffic_manager:
            probe_command.append('--traffic-manager')
        result = subprocess.Popen(probe_command,
                                stdout=log, stderr=subprocess.STDOUT)
        probe_deadline = time.monotonic() + 600
        while result.poll() is None:
            if proc.poll() is not None or time.monotonic() > probe_deadline:
                r['probe_stop_reason'] = 'server exited' if proc.poll() is not None else 'probe timeout'
                result.terminate()
                try:
                    result.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    result.kill()
                    result.wait()
                break
            time.sleep(1)
        r['probe_returncode'] = result.returncode
        r['pass'] = result.returncode == 0
except Exception:
    r['error'] = traceback.format_exc()
finally:
    if proc is not None:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            proc.wait(timeout=15)
        except ProcessLookupError:
            pass
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=10)
        r['server_returncode'] = proc.returncode
    saved = Path(a.root) / 'CarlaUE4/Saved/Logs'
    if saved.is_dir():
        for src in saved.glob('*.log'):
            shutil.copy2(str(src), str(out / src.name))
    (out / 'run.json').write_text(json.dumps(r, indent=2), encoding='utf-8')
    print(json.dumps(r, indent=2), flush=True)
raise SystemExit(0 if r['pass'] else 1)
