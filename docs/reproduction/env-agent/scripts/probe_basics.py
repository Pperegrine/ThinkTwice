"""Run with old/new isolated Python. No model or control modifications."""
import json
import os
import sys
import time
import traceback
import warnings

report = {'python': sys.version, 'executable': sys.executable, 'stages': {},
          'driver_cache': {k: os.environ.get(k) for k in ('CUDA_CACHE_PATH', 'CUDA_CACHE_MAXSIZE')}}
def stage(name, fn):
    start = time.perf_counter()
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            result = fn()
        report['stages'][name] = {'pass': True, 'seconds': time.perf_counter()-start,
                                 'result': result, 'warnings': [str(w.message) for w in caught]}
    except Exception:
        report['stages'][name] = {'pass': False, 'seconds': time.perf_counter()-start,
                                 'error': traceback.format_exc()}
    print(json.dumps({name: report['stages'][name]}, ensure_ascii=True), flush=True)
    with open(sys.argv[1], 'w') as f:
        json.dump(report, f, indent=2)

def cpu_bridge():
    import numpy as np
    import torch
    a = np.arange(12, dtype=np.float32).reshape(3,4)
    t = torch.from_numpy(a)
    a[0,0] = 7
    assert t[0,0].item() == 7
    b = t.numpy()
    assert np.array_equal(a,b) and np.isfinite(b).all()
    return {'numpy': np.__version__, 'numpy_file': np.__file__, 'torch': torch.__version__, 'torch_file': torch.__file__,
            'shape': list(b.shape), 'roundtrip': True}

def cuda_bridge():
    import numpy as np
    import torch
    a = np.arange(12, dtype=np.float32).reshape(3,4)
    t = torch.from_numpy(a).cuda()
    torch.cuda.synchronize()
    b = t.cpu().numpy()
    assert np.array_equal(a,b) and np.isfinite(b).all()
    return {'roundtrip': True, 'device': torch.cuda.get_device_name(0),
            'cuda': torch.version.cuda, 'arch': torch.cuda.get_arch_list()}

def cuda_bench():
    import torch
    def timed(fn):
        torch.cuda.synchronize()
        start=time.perf_counter()
        out=fn()
        torch.cuda.synchronize()
        elapsed=(time.perf_counter()-start)*1000
        # CPU check avoids introducing additional GPU reduction kernels into timing.
        import numpy as np
        assert np.isfinite(out.detach().cpu().numpy()).all()
        return out,elapsed
    a,cold_rng=timed(lambda: torch.randn(512,512,device='cuda'))
    _,first_mm=timed(lambda: a@a)
    warm_mm=[timed(lambda: a@a)[1] for _ in range(10)]
    conv=torch.nn.Conv2d(64,64,3,padding=1).cuda().eval()
    x=torch.randn(1,64,64,64,device='cuda')
    with torch.no_grad():
        _,first_conv=timed(lambda: conv(x))
        warm_conv=[timed(lambda: conv(x))[1] for _ in range(10)]
    return {'first_call_cache_state': 'existing driver cache; not cache-cold',
            'randn_first_ms': cold_rng,'matmul_first_ms': first_mm,'conv_first_ms': first_conv,
            'matmul_warm_ms': warm_mm,'conv_warm_ms': warm_conv,'finite': True}

stage('cpu_tensor_numpy',cpu_bridge)
stage('cuda_tensor_numpy',cuda_bridge)
stage('cuda_finite_sync_bench',cuda_bench)
sys.exit(0 if all(s['pass'] for s in report['stages'].values()) else 1)
