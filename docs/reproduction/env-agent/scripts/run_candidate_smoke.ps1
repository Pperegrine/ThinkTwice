param(
    [Parameter(Mandatory=$true)][string]$RunName,
    [string]$Launcher='launch_carla_wsl_triangle_fix_v2.sh'
)
$ErrorActionPreference='Stop'
if ($RunName -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Use a simple unique run name' }
$projectRoot=(Resolve-Path (Join-Path $PSScriptRoot '../../../../../')).Path
$ev='ThinkTwice/docs/reproduction/env-agent/evidence/20261009-takeover/'
$env:WSL_UTF8='1'
$wslArgs=@('-d','ThinkTwice-Focal','-u','ttenv','--cd',$projectRoot,'--exec','/usr/bin/env',
    'LANG=C.UTF-8','LC_ALL=C.UTF-8','PYTHONPATH=/opt/thinktwice/candidate-site',
    'LD_LIBRARY_PATH=/opt/thinktwice/cudnn832-runtime/lib:/opt/thinktwice/cuda113-ptx/lib',
    'CUDA_CACHE_PATH=/opt/thinktwice/cuda-cache','CUDA_CACHE_MAXSIZE=4294967296',
    '/opt/thinktwice/conda/bin/python','ThinkTwice/docs/reproduction/env-agent/scripts/run_single_route_smoke.py',
    '--output-dir',('.thinktwice-runtime/runs/'+$RunName),
    '--carla-launcher',('ThinkTwice/docs/reproduction/env-agent/scripts/'+$Launcher),
    '--basics',($ev+'linux-basics-candidate01.json'),'--deform',($ev+'candidate-deform-01.json'),
    '--dcn',($ev+'candidate-dcn-01.json'),'--spconv',($ev+'candidate-spconv-01.json'),
    '--voxel',($ev+'candidate-voxel-01.json'),'--lidar',($ev+'candidate-lidar-stack02-metadata.json'),
    '--identity',($ev+'extensions-candidate-identity01.json'),'--model',($ev+'candidate-model-gpu01.json'),
    '--replay',($ev+'real-batch-replay01.json'))
Push-Location $projectRoot
try {
    # Expected WSL proxy notice may arrive on stderr; preserve it as evidence.
    $ErrorActionPreference='Continue'
    & wsl @wslArgs > ($ev+$RunName+'-supervisor.log') 2>&1
    $runExit=$LASTEXITCODE
} finally { Pop-Location }
exit $runExit
