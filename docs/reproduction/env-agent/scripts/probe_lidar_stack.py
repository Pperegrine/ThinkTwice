"""Official complete LiDAR stack with checkpoint weights and synthetic points.

This is a CUDA execution/shape/finite gate, not the real sensor gate.
"""
import argparse
from collections import OrderedDict
import importlib
import json
import os
from pathlib import Path
import sys
import time
import traceback

p = argparse.ArgumentParser()
p.add_argument('--output', required=True)
a = p.parse_args()
output = Path(a.output).resolve()
root = Path(__file__).resolve().parents[5]
repo = root / 'ThinkTwice'
os.chdir(str(repo))
sys.path[:0] = [os.environ.get('THINKTWICE_VOXEL_ROOT', '/opt/thinktwice/voxel-candidate'), str(repo), str(repo / 'open_loop_training')]
r = {'scope': 'synthetic complete official LiDAR CUDA stack, not real sensors', 'pass': False}
try:
    import numpy as np
    import torch
    from mmcv import Config
    from mmdet.models import build_backbone
    importlib.import_module('open_loop_training.code')
    cfg = Config.fromfile(str(repo / 'open_loop_training/configs/thinktwice.py'))
    model = build_backbone(cfg.model.lidar_encoder)
    checkpoint = torch.load(str(root / 'thinktwice.pth'), map_location='cpu')['state_dict']
    prefix = 'lidar_encoder.'
    selected = OrderedDict((k[len(prefix):], v) for k, v in checkpoint.items() if k.startswith(prefix))
    metadata = getattr(checkpoint, '_metadata', {})
    selected._metadata = OrderedDict((k[len(prefix):], v) for k, v in metadata.items()
                                     if k == prefix[:-1] or k.startswith(prefix))
    r['metadata_entries_preserved'] = len(selected._metadata)
    r['original_input_weight_shape'] = list(selected['pts_middle_encoder.conv_input.0.weight'].shape)
    assert selected._metadata['pts_middle_encoder.conv_input.0']['version'] == 2
    model.load_state_dict(selected, strict=True)
    r['strict_lidar_keys'] = len(selected)
    model = model.cuda().eval()
    rng = np.random.RandomState(42)
    bounds = np.array(cfg.model.lidar_encoder.pts_voxel_layer.point_cloud_range, dtype=np.float32)
    points = np.zeros((1, 12000, 5), dtype=np.float32)
    points[0, :, :3] = rng.uniform(bounds[:3] + .05, bounds[3:] - .05, (12000, 3))
    points[0, :, 3:] = rng.uniform(0, 1, (12000, 2))
    inputs = torch.from_numpy(points).cuda()
    r['inputs'] = {'shape': list(inputs.shape), 'point_cloud_range': bounds.tolist()}
    r['torch'] = {'version': torch.__version__, 'path': torch.__file__}
    results = []
    with torch.no_grad():
        for iteration in range(2):
            torch.cuda.synchronize()
            start = time.perf_counter()
            outputs = model(inputs)
            torch.cuda.synchronize()
            seconds = time.perf_counter() - start
            shapes = []
            for value in outputs:
                array = value.detach().cpu().numpy()
                assert np.isfinite(array).all()
                shapes.append(list(array.shape))
            results.append({'iteration': iteration, 'seconds': seconds, 'shapes': shapes, 'finite': True})
    r['invocations'] = results
    r['cache_state'] = 'existing driver cache; first invocation is not asserted cache-cold'
    r['pass'] = True
except Exception:
    r['error'] = traceback.format_exc()
output.write_text(json.dumps(r, indent=2))
print(json.dumps(r, indent=2), flush=True)
raise SystemExit(0 if r['pass'] else 1)
