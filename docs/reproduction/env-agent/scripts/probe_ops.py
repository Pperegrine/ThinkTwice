"""Isolated CUDA launches; synthetic numerical checks are operator tests only."""
import argparse
import importlib.util
import json
import time
import traceback
from pathlib import Path
import numpy as np
import torch

p=argparse.ArgumentParser()
p.add_argument('--op', choices=['deform','dcn','spconv','voxel','voxel_raw'],required=True)
p.add_argument('--output',required=True)
p.add_argument('--repo',required=True)
args=p.parse_args()
report={'op':args.op,'torch':torch.__version__,'torch_file':torch.__file__,'cuda':torch.version.cuda,'pass':False}
t0=time.perf_counter()
try:
    if args.op=='deform':
        from mmcv import _ext
        report['extension_path'] = _ext.__file__
        from mmcv.ops.multi_scale_deform_attn import MultiScaleDeformableAttnFunction, multi_scale_deformable_attn_pytorch
        value=torch.from_numpy(np.arange(32,dtype=np.float32).reshape(1,4,2,4)/32).cuda()
        shapes=torch.tensor([[2,2]],dtype=torch.long,device='cuda')
        starts=torch.tensor([0],dtype=torch.long,device='cuda')
        loc=torch.from_numpy(np.full((1,3,2,1,2,2),0.5,dtype=np.float32)).cuda()
        weights=torch.from_numpy(np.full((1,3,2,1,2),0.5,dtype=np.float32)).cuda()
        out=MultiScaleDeformableAttnFunction.apply(value,shapes,starts,loc,weights,64)
        torch.cuda.synchronize()
        ref=multi_scale_deformable_attn_pytorch(value.cpu(),shapes.cpu(),loc.cpu(),weights.cpu())
        actual=out.detach().cpu().numpy()
        np.testing.assert_allclose(actual,ref.numpy(),rtol=1e-5,atol=1e-6)
    elif args.op=='dcn':
        from mmcv.ops import DeformConv2dPack
        from mmcv import _ext
        report['extension_path'] = _ext.__file__
        layer = DeformConv2dPack(8, 8, 3, padding=1, groups=4, bias=False).eval()
        source = torch.from_numpy(np.arange(8*12*12, dtype=np.float32).reshape(1,8,12,12)/1152)
        with torch.no_grad():
            layer.weight.fill_(1/18.)
            layer.conv_offset.weight.zero_()
            layer.conv_offset.bias.zero_()
            reference = torch.nn.functional.conv2d(source, layer.weight, padding=1, groups=4).numpy()
            actual = layer.cuda()(source.cuda()).cpu().numpy()
        torch.cuda.synchronize()
        np.testing.assert_allclose(actual, reference, rtol=2e-4, atol=2e-5)
        report['scope'] = 'grouped DCN with zero offsets, numerical equality to grouped convolution'
    elif args.op=='spconv':
        import spconv
        import spconv.pytorch as sp
        report['spconv']=spconv.__version__
        report['spconv_package_path']=spconv.__file__
        features=torch.from_numpy(np.ones((3,4),dtype=np.float32)).cuda()
        indices=torch.tensor([[0,1,1,1],[0,1,1,2],[0,1,2,1]],dtype=torch.int32,device='cuda')
        x=sp.SparseConvTensor(features,indices,[4,4,4],1)
        layer=sp.SubMConv3d(4,4,1,bias=False).eval()
        with torch.no_grad():
            layer.weight.fill_(0.25)
            layer=layer.cuda()
            out=layer(x)
        torch.cuda.synchronize()
        actual=out.features.detach().cpu().numpy()
        np.testing.assert_allclose(actual,np.ones((3,4),dtype=np.float32),rtol=1e-5,atol=1e-6)
    else:
        import sys
        sys.path.insert(0,str(Path(args.repo)))
        from ops.voxel_pooling.voxel_pooling import voxel_pooling
        from ops.voxel_pooling import voxel_pooling_ext
        report['extension_path'] = voxel_pooling_ext.__file__
        report['wrapper_path'] = sys.modules['ops.voxel_pooling.voxel_pooling'].__file__
        coords=torch.tensor([[[0,0,0],[0,0,0],[1,1,0]]],dtype=torch.int32,device='cuda')
        features=torch.tensor([[[1.,2.],[3.,4.],[5.,6.]]],device='cuda')
        n=torch.tensor([2,2,1],dtype=torch.int32)  # sizes consumed as CPU scalars
        if args.op=='voxel_raw':
            from ops.voxel_pooling import voxel_pooling_ext
            out=torch.from_numpy(np.zeros((1,2,2,2),dtype=np.float32)).cuda()
            memo=torch.from_numpy(np.full((1,3,3),-1,dtype=np.int32)).cuda()
            voxel_pooling_ext.voxel_pooling_forward_wrapper(1,3,2,2,2,1,coords,features,out,memo)
            out=out.permute(0,3,1,2)
            report['scope']='raw official CUDA extension; wrapper aten allocations bypassed in diagnostic only'
        else:
            out=voxel_pooling(coords,features,n)
        torch.cuda.synchronize()
        actual=out.detach().cpu().numpy()
        ref=np.zeros((1,2,2,2),dtype=np.float32)
        ref[0,:,0,0]=[4,6]
        ref[0,:,1,1]=[5,6]
        np.testing.assert_allclose(actual,ref,rtol=1e-5,atol=1e-6)
    assert np.isfinite(actual).all()
    report.update({'pass':True,'shape':list(actual.shape),'finite':True})
except Exception:
    report['error']=traceback.format_exc()
report['seconds']=time.perf_counter()-t0
Path(args.output).write_text(json.dumps(report,indent=2))
print(json.dumps(report),flush=True)
raise SystemExit(0 if report['pass'] else 1)
