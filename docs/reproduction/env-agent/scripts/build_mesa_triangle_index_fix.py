"""Preserve original aggregate output deref path during triangle strip stores."""
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

root = Path('/opt/thinktwice/src/mesa-24.0.5')
source = root / 'src/gallium/drivers/d3d12/d3d12_nir_passes.c'
prefix = Path('/opt/thinktwice/mesa24-triangle-fix-v2/lib/dri')
assert not prefix.exists()
before = source.read_text()
old = '''   nir_def *value = intr->src[1].ssa;
   nir_store_deref(b, deref, value, 0xf);
   nir_instr_remove(&intr->instr);'''
assert before.count(old) == 1
new = '''   /* Retain array/struct element indices below the original output root. */
   nir_deref_path path;
   nir_deref_path_init(&path, nir_src_as_deref(intr->src[0]), NULL);
   for (unsigned i = 1; path.path[i]; i++)
      deref = nir_build_deref_follower(b, deref, path.path[i]);
   nir_deref_path_finish(&path);
   nir_def *value = intr->src[1].ssa;
   nir_store_deref(b, deref, value, nir_intrinsic_write_mask(intr));
   nir_instr_remove(&intr->instr);'''
after = before.replace(old, new)
backup = source.with_suffix('.c.before-triangle-index-fix')
assert not backup.exists()
shutil.copy2(str(source), str(backup))
source.write_text(after)
build = root / 'build-d3d12-debug'
subprocess.run(['ninja', '-C', str(build), '-j2', 'src/gallium/targets/dri/libgallium_dri.so'], check=True)
prefix.mkdir(parents=True)
target = prefix / 'swrast_dri.so'
shutil.copy2(str(build / 'src/gallium/targets/dri/libgallium_dri.so'), str(target))
evidence = Path(__file__).resolve().parent.parent / 'evidence/20261009-takeover'
original = source.with_suffix('.c.before-triangle-copy-fix').read_text()
diff = ''.join(difflib.unified_diff(original.splitlines(True), after.splitlines(True),
                                  fromfile='Mesa24.0.5 original d3d12_nir_passes.c', tofile=str(source)))
(evidence / 'mesa-triangle-fix-v2.diff').write_text(diff)
report = {'scope': 'local deployment fix: split aggregate copy and retain deref path/write mask',
          'library': str(target), 'bytes': target.stat().st_size,
          'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
          'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'original_source_backup': str(source.with_suffix('.c.before-triangle-copy-fix')),
          'previous_install_and_candidates_preserved': True, 'runtime_validation': 'pending',
          'model_agent_control_changes': []}
(evidence / 'mesa-triangle-fix-v2-build.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2), flush=True)
