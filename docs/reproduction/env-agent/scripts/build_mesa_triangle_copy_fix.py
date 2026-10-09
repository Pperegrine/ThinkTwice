"""Local D3D12 deployment fix: split aggregate copies before lowering.

Evidence: smoke08 full Mesa symbols/asserter, d3d12_lower_triangle_strip ->
nir_lower_var_copies -> assert(glsl_type_is_vector_or_scalar(dst_deref->type)).
No CARLA shader, model, agent or control source is changed.
"""
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

source_root = Path('/opt/thinktwice/src/mesa-24.0.5')
source = source_root / 'src/gallium/drivers/d3d12/d3d12_nir_passes.c'
prefix = Path('/opt/thinktwice/mesa24-triangle-fix/lib/dri')
assert not prefix.exists(), 'Preserve existing candidate'
before = source.read_text()
old = '   nir_metadata_preserve(impl, nir_metadata_none);\n   NIR_PASS_V(shader, nir_lower_var_copies);'
assert before.count(old) == 1
after = before.replace(old, '   nir_metadata_preserve(impl, nir_metadata_none);\n'
                      '   /* Triangle-strip emission creates aggregate output copies. */\n'
                      '   NIR_PASS_V(shader, nir_split_var_copies);\n'
                      '   NIR_PASS_V(shader, nir_lower_var_copies);')
backup = source.with_suffix('.c.before-triangle-copy-fix')
assert not backup.exists()
shutil.copy2(str(source), str(backup))
source.write_text(after)
build = source_root / 'build-d3d12-debug'
subprocess.run(['ninja', '-C', str(build), '-j2', 'src/gallium/targets/dri/libgallium_dri.so'], check=True)
prefix.mkdir(parents=True)
library = prefix / 'swrast_dri.so'
shutil.copy2(str(build / 'src/gallium/targets/dri/libgallium_dri.so'), str(library))
diff = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                   fromfile=str(backup), tofile=str(source)))
evidence = Path(__file__).resolve().parent.parent / 'evidence/20261009-takeover'
(evidence / 'mesa-triangle-copy-fix.diff').write_text(diff)
report = {'scope': 'local deployment driver fix; not claimed upstream',
          'source': str(source), 'backup': str(backup),
          'source_before_sha256': hashlib.sha256(before.encode()).hexdigest(),
          'source_after_sha256': hashlib.sha256(after.encode()).hexdigest(),
          'library': str(library), 'bytes': library.stat().st_size,
          'sha256': hashlib.sha256(library.read_bytes()).hexdigest(),
          'original_installed_release_and_debug_preserved': True,
          'model_agent_control_changes': [], 'runtime_validation': 'pending'}
(evidence / 'mesa-triangle-copy-fix-build.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2), flush=True)
