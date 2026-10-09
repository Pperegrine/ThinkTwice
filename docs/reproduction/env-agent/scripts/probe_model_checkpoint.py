"""Official CPU model construction and complete checkpoint key/shape comparison."""
import argparse
import importlib
import json
import os
from pathlib import Path
import sys
import traceback

p = argparse.ArgumentParser()
p.add_argument('--output', required=True)
p.add_argument('--device', choices=['cpu', 'cuda'], default='cpu')
a = p.parse_args()
output = Path(a.output).resolve()
root = Path(__file__).resolve().parents[5]
repo = root / 'ThinkTwice'
os.chdir(str(repo))
sys.path.insert(0, str(repo))
sys.path.insert(0, str(repo / 'open_loop_training'))
sys.path.insert(0, os.environ.get('THINKTWICE_VOXEL_ROOT', '/opt/thinktwice/build'))
r = {'scope': 'CPU model/key/shape only; not CUDA inference', 'pass': False}
try:
    import torch
    r['torch'] = {'version': torch.__version__, 'path': torch.__file__, 'abi': torch._C._GLIBCXX_USE_CXX11_ABI}
    from mmcv import Config
    from mmdet3d.models import build_model
    importlib.import_module('open_loop_training.code')
    cfg = Config.fromfile(str(repo / 'open_loop_training/configs/thinktwice.py'))
    r['refine_num'] = cfg.cfg.refine_num
    assert r['refine_num'] == 5
    model = build_model(cfg.model, train_cfg=cfg.get('train_cfg'), test_cfg=cfg.get('test_cfg'))
    expected = model.state_dict()
    checkpoint = torch.load(str(root / 'thinktwice.pth'), map_location='cpu')['state_dict']
    r['checkpoint_keys'] = len(checkpoint)
    r['model_keys'] = len(expected)
    r['missing'] = sorted(set(expected) - set(checkpoint))
    r['unexpected'] = sorted(set(checkpoint) - set(expected))
    r['shape_mismatches'] = {k: {'model': list(expected[k].shape), 'checkpoint': list(checkpoint[k].shape)}
                             for k in set(expected) & set(checkpoint) if expected[k].shape != checkpoint[k].shape}
    assert not r['missing'] and not r['unexpected'] and not r['shape_mismatches']
    model.load_state_dict(checkpoint, strict=True)
    if a.device == 'cuda':
        model = model.cuda().eval()
        torch.cuda.synchronize()
        r['scope'] = 'official model/strict checkpoint/GPU placement; not forward inference'
    r['parameter_devices'] = sorted(set(str(x.device) for x in model.parameters()))
    r['parameter_count'] = sum(x.numel() for x in model.parameters())
    r['pass'] = True
except Exception:
    r['error'] = traceback.format_exc()
finally:
    output.write_text(json.dumps(r, indent=2), encoding='utf-8')
    print(json.dumps(r, indent=2), flush=True)
raise SystemExit(0 if r['pass'] else 1)
