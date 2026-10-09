"""Recompile only crashing NIR file with symbols; installed release retained."""
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess

build = Path('/opt/thinktwice/src/mesa-24.0.5/build-d3d12')
prefix = Path('/opt/thinktwice/mesa24-nir-debug-v2/lib/dri')
assert not prefix.exists(), 'Preserve existing diagnostic library'
commands = subprocess.check_output(['ninja', '-t', 'commands'], cwd=str(build)).decode().splitlines()
matches = [x for x in commands if ' -c ' in x and x.endswith('/nir_lower_wpos_ytransform.c')]
assert len(matches) == 1, matches
command = shlex.split(matches[0]) + ['-g', '-O1', '-fno-omit-frame-pointer']
print(json.dumps({'cwd': str(build), 'compile_command': command}), flush=True)
# Put flags in an independent Ninja graph so Ninja does not replace our object
# with its release command when resolving dependencies.
graph = (build / 'build.ninja').read_text()
object_path = shlex.split(matches[0])[shlex.split(matches[0]).index('-o') + 1]
start = graph.index('build ' + object_path + ':')
end = graph.index('\n\n', start)
block = graph[start:end]
lines = block.splitlines()
args_line = next(i for i, line in enumerate(lines) if line.startswith(' ARGS ='))
lines[args_line] += ' -g -O1 -fno-omit-frame-pointer'
graph = graph[:start] + '\n'.join(lines) + graph[end:]
(build / 'build-nir-debug.ninja').write_text(graph)
subprocess.run(['ninja', '-f', 'build-nir-debug.ninja', '-j2',
                'src/gallium/targets/dri/libgallium_dri.so'], cwd=str(build), check=True)
prefix.mkdir(parents=True)
target = prefix / 'swrast_dri.so'
shutil.copy2(str(build / 'src/gallium/targets/dri/libgallium_dri.so'), str(target))
sections = subprocess.check_output(['readelf', '-S', str(target)]).decode()
assert '.debug_info' in sections and '.debug_line' in sections, sections
report = {'scope': 'same Mesa24.0.5, one NIR compilation unit symbols/O1 only',
          'source_changes': [], 'release_install_unchanged': True,
          'path': str(target), 'bytes': target.stat().st_size,
          'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'command': command}
(prefix.parent.parent / 'manifest.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2), flush=True)
