"""Replay saved original sensor batch through unchanged official model."""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import time
import traceback

p = argparse.ArgumentParser()
p.add_argument('--batch', required=True)
p.add_argument('--output', required=True)
a = p.parse_args()
batch_path = Path(a.batch).resolve()
output = Path(a.output).resolve()
root = Path(__file__).resolve().parents[5]
repo = root / 'ThinkTwice'
os.chdir(str(repo))
sys.path[:0] = ['/opt/thinktwice/voxel-candidate', str(repo), str(repo / 'open_loop_training')]
os.environ.setdefault('BENCHMARK', 'town05long')
r = {'scope': 'saved real CARLA batch replay; not a connected closed loop', 'pass': False,
     'batch': str(batch_path), 'batch_sha256': hashlib.sha256(batch_path.read_bytes()).hexdigest()}
def persist(stage):
    r['stage'] = stage
    output.write_text(json.dumps(r, indent=2))

def describe(x):
    import torch
    if torch.is_tensor(x):
        return {'shape': list(x.shape), 'dtype': str(x.dtype),
                'finite': bool(torch.isfinite(x).all().item())}
    if isinstance(x, dict):
        return {str(k): describe(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [describe(v) for v in x]
    return {'type': type(x).__name__}

try:
    import torch
    from mmcv import Config
    from mmdet3d.models import build_model
    importlib.import_module('open_loop_training.code')
    r['torch'] = {'version': torch.__version__, 'path': torch.__file__,
                  'abi': torch._C._GLIBCXX_USE_CXX11_ABI}
    lib = Path('/opt/thinktwice/candidate-site/torch/lib/libtorch_cuda.so')
    r['libtorch_cuda_sha256'] = hashlib.sha256(lib.read_bytes()).hexdigest()
    persist('nvrtc_prod')
    product = torch.tensor([[2, 3], [4, 5]], device='cuda', dtype=torch.long).prod(1)
    torch.cuda.synchronize()
    assert product.cpu().tolist() == [6, 20]
    r['nvrtc_prod'] = {'pass': True, 'result': product.cpu().tolist(),
                       'runtime_libraries': [s for s in Path('/proc/self/maps').read_text().splitlines()
                                             if 'libnvrtc' in s]}
    persist('model_setup')
    cfg = Config.fromfile(str(repo / 'open_loop_training/configs/thinktwice.py'))
    r['refine_num'] = cfg.cfg.refine_num
    assert r['refine_num'] == 5
    model = build_model(cfg.model, train_cfg=cfg.get('train_cfg'), test_cfg=cfg.get('test_cfg'))
    state = torch.load(str(root / 'thinktwice.pth'), map_location='cpu')['state_dict']
    model.load_state_dict(state, strict=True)
    r['checkpoint_keys'] = len(state)
    model = model.cuda().eval()
    batch = torch.load(str(batch_path), map_location='cpu')
    # Match original agent's top-level tensor transfer exactly.
    for key in batch:
        if torch.is_tensor(batch[key]):
            batch[key] = batch[key].cuda()
    r['inputs'] = describe(batch)
    r['invocations'] = []
    for index in range(2):
        persist('forward_%d' % index)
        torch.cuda.synchronize()
        begin = time.perf_counter()
        with torch.no_grad():
            pred = model.forward_inference(batch)
        torch.cuda.synchronize()
        seconds = time.perf_counter() - begin
        shapes = describe(pred)
        levels = {k: [bool(torch.isfinite(v[:, i]).all().item()) for i in range(v.shape[1])]
                  for k, v in pred.items() if k in ('pred_wp', 'mu_branches', 'sigma_branches',
                                                   'future_mu', 'future_sigma')}
        assert len(levels) == 5 and all(len(v) == 6 and all(v) for v in levels.values()), levels
        assert all(x.get('finite', True) for x in shapes.values()), shapes
        r['invocations'].append({'index': index, 'seconds_synchronized': seconds,
                                  'outputs': shapes, 'six_levels_finite': levels, 'pass': True})
        persist('forward_%d_pass' % index)
    r['pass'] = True
except Exception:
    r['error'] = traceback.format_exc()
finally:
    output.write_text(json.dumps(r, indent=2))
    print(json.dumps(r, indent=2), flush=True)
raise SystemExit(0 if r['pass'] else 1)
