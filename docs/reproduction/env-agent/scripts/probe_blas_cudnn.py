"""Isolate old cuBLAS/cuDNN from the known failing CUDA random kernel."""
import argparse
import json
from pathlib import Path
import time
import traceback

import numpy as np
import torch

p = argparse.ArgumentParser()
p.add_argument('--output', required=True)
a = p.parse_args()
r = {'torch': torch.__version__, 'torch_path': torch.__file__,
     'cuda': torch.version.cuda, 'cudnn': torch.backends.cudnn.version(), 'stages': {}}


def timed(fn):
    torch.cuda.synchronize()
    start = time.perf_counter()
    value = fn()
    torch.cuda.synchronize()
    seconds = time.perf_counter() - start
    actual = value.detach().cpu().numpy()
    assert np.isfinite(actual).all()
    return actual, seconds


def mm():
    array = np.arange(32 * 32, dtype=np.float32).reshape(32, 32) / 1024
    value = torch.from_numpy(array).cuda()
    actual, first = timed(lambda: value @ value)
    np.testing.assert_allclose(actual, array @ array, rtol=2e-4, atol=2e-4)
    warm = [timed(lambda: value @ value)[1] for _ in range(10)]
    return {'first_seconds': first, 'warm_seconds': warm, 'shape': list(actual.shape), 'reference_match': True}


def conv():
    layer = torch.nn.Conv2d(4, 4, 3, padding=1, bias=False).eval()
    with torch.no_grad():
        layer.weight.fill_(0.125)
        source = torch.from_numpy(np.ones((1, 4, 16, 16), dtype=np.float32))
        reference = layer(source).numpy()
        layer = layer.cuda()
        value = source.cuda()
        actual, first = timed(lambda: layer(value))
        np.testing.assert_allclose(actual, reference, rtol=2e-4, atol=2e-4)
        warm = [timed(lambda: layer(value))[1] for _ in range(10)]
    return {'first_seconds': first, 'warm_seconds': warm, 'shape': list(actual.shape), 'reference_match': True}


for name, fn in (('cublas_matmul', mm), ('cudnn_convolution', conv)):
    try:
        result = fn()
        r['stages'][name] = {'pass': True, 'result': result}
    except Exception:
        r['stages'][name] = {'pass': False, 'error': traceback.format_exc()}
    r['cache_state'] = 'existing driver cache; first invocation is not asserted cache-cold'
    Path(a.output).write_text(json.dumps(r, indent=2))
    print(json.dumps({name: r['stages'][name]}, indent=2), flush=True)
raise SystemExit(0 if all(x['pass'] for x in r['stages'].values()) else 1)
