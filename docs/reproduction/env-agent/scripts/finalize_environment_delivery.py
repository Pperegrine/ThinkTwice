"""Write delivery reports only after actual bounded acceptance and clean exit."""
import json
from pathlib import Path
import statistics
import subprocess
from datetime import datetime

root = Path(__file__).resolve().parents[5]
docs = root / 'ThinkTwice/docs/reproduction/env-agent'
run = root / '.thinktwice-runtime/runs/20261009-smoke13-cleanup-final'
accept = json.loads((run / 'smoke-acceptance.json').read_text())
raw = json.loads((run / 'run.json').read_text())
assert accept['pass'] and accept['inference_count'] >= 200
assert raw['returncode'] == 0 and not raw.get('server_abort')
assert not raw.get('failures')
cleanup = json.loads((run / 'cleanup-verification.json').read_text())
assert cleanup['pass'] and not cleanup['remaining_smoke_processes']
assert accept['six_levels_all_finite'] and accept['controls_all_valid']
# The host owns the Git checkout; dedicated WSL cannot resolve its metadata.
# Use the actual host Git check saved immediately before generating this report.
check = json.loads((docs / 'evidence/20261009-takeover/final-original-source-check.json').read_text(encoding='utf-8-sig'))
assert check['pass'] and check['exit_code'] == 0 and not check['output']
data = [json.loads(x) for x in (run / 'sensor-inference/agent-events.jsonl').read_text().splitlines()]
inf = [x for x in data if x['event'] == 'inference']
controls = [x for x in data if x['event'] == 'control']
first = inf[0]
warm = [x['seconds_synchronized'] for x in inf[1:]]
control_ranges = {k: [min(x['values'][k] for x in controls), max(x['values'][k] for x in controls)]
                  for k in ('steer', 'throttle', 'brake')}
identity = json.loads((docs / 'evidence/20261009-takeover/final-installed-identities.json').read_text())
now = datetime.now().isoformat(timespec='seconds')
progress = accept['raw_route_progress_percent'][0]
displacement = accept['ego_displacement_from_route_start_m']
summary = {'scope': accept['scope'], 'pass': True, 'created': now,
           'acceptance': str(run / 'smoke-acceptance.json'),
           'inferences': len(inf), 'controls': len(controls), 'control_ranges': control_ranges,
           'first_live_seconds': first['seconds_synchronized'],
           'subsequent_live_median_seconds': statistics.median(warm),
           'subsequent_live_min_max_seconds': [min(warm), max(warm)],
           'route_progress_percent': progress, 'displacement_m': displacement,
           'simulation_control_seconds': controls[-1]['timestamp'] - controls[0]['timestamp'],
           'raw_evaluator_returncode': raw['returncode'], 'full_route_completed': False,
           'original_model_agent_control_diff_empty': True, 'identity': identity,
           'cleanup': cleanup}
(docs / 'evidence/20261009-takeover/final-delivery-summary.json').write_text(json.dumps(summary, indent=2))
report = f'''# ThinkTwice 隔离环境交付报告

更新：{now}（本地）。**用户确认的短闭环 smoke 已通过；未完成整条路线或完整 Town05 Long 评测。**

## 实际验收结果

最终运行 `.thinktwice-runtime/runs/20261009-smoke13-cleanup-final`。使用原始 Town05 route16、原场景及120背景交通、官方 checkpoint、完整5轮 refinement 和原控制。

- 连续 **{len(inf)} 次**实时完整推理、**{len(controls)} 次**控制返回；推理step连续，全部输出有限，控制范围全部合法，无模型/传感器异常。
- 自车从路线起点移动 **{displacement:.3f}m**；原评测器记录路线进度 **{progress:.6f}%**。
- 用户选定“至少200次推理后结束”，由本任务向自己的原评测器发送 SIGINT，原停止流程写出评分并清理；评测器退出码 **0**，无监督器强制中止。
- 原 `results.json` 的路线状态为 `{accept['raw_full_route_statuses']}`，RouteCompletion未满100%；原始状态和 `run.json` 的整路线pass=false均保留。**独立 `smoke-acceptance.json` 的短测pass=true**，不冒充整路线通过。
- 实时首个forward同步耗时 {first['seconds_synchronized']:.6f}s，后续中位数 {statistics.median(warm):.6f}s，范围 {min(warm):.6f}–{max(warm):.6f}s；已有缓存，非空缓存冷启动或整系统FPS。
- 控制最小/最大：`{json.dumps(control_ranges)}`。
- 退出后的独立进程核验通过，无本次CARLA/评测器/监督器/停止器残留；项目卷可用 {cleanup['project_volume_available_bytes']}B。见cleanup-verification.json。

| 阶梯 | 真实结果与证据 |
|---|---|
| 1 Python/依赖/NumPy | Python3.7.16、NumPy1.20.3，CPU/GPU Tensor↔NumPy数值往返通过，无NumPy初始化警告；linux-basics-candidate01.json |
| 2 基础CUDA | randn/mm/conv有限值与同步冷热分开计时通过；首次GPU初始化554.856s，已保留当时缓存/并行构建条件；同上JSON |
| 3 关键算子 | voxel完整wrapper、deformable attention、DCN、spconv实际数值测试通过；candidate-*-01.json。完整官方LiDAR栈[1,512,84,84]有限；candidate-lidar-stack02-metadata.json |
| 4 模型与权重 | 官方1344/1344键/shape strict、128232121参数cuda:0、refine_num5；candidate-model-gpu01.json。NVRTC修复后真实batch连续两次全forward通过；real-batch-replay01.json |
| 5 CARLA | 原0.9.10.1，API/server784d9b9f，Town05/sync0.05/10tick基础通过；最终真实场景/传感器/120交通通过 |
| 6 真实batch | 最终实时{len(inf)}次；pred_wp[1,6,4,2]，mu/sigma[1,6,2]，future_mu/sigma[1,6,3,2]，全部六级有限；agent-events.jsonl及首batch/prediction.pt |
| 7 单路线短闭环 | 按用户明确的≥200次范围通过；原评分JSON、控制台、进度和主动终止原因齐备；smoke-acceptance.json/termination.json |

## 可运行环境与入口

仅使用独立 WSL `ThinkTwice-Focal` / 非root用户 `ttenv`。旧Windows项目、原Ubuntu/Ubuntu-D、默认WSL、下载文件均保留。

| 项目 | 当前值 |
|---|---|
| Python | /opt/thinktwice/conda/bin/python，3.7.16 |
| 推理包 | /opt/thinktwice/candidate-site；torch1.12.1、vision0.13.1、MMCV1.7.0、mmdet3d1.0.0rc6、spconv2.3.6；统一实际ABI1 |
| CUDA/cuDNN | /opt/thinktwice/cuda113-ptx，11.3；独立cudnn832-runtime/lib |
| 原voxel | /opt/thinktwice/voxel-candidate；不要混入旧ABI0的/opt/thinktwice/build |
| 缓存 | CUDA_CACHE_PATH=/opt/thinktwice/cuda-cache，MAXSIZE=4294967296；TORCH_HOME=/opt/thinktwice/torch-cache |
| CARLA | /opt/thinktwice/carla-0.9.10.1；原egg carla-0.9.10-py3.7-linux-x86_64.egg未改名 |
| 图形库 | /opt/thinktwice/mesa24-triangle-fix-v2/lib/dri，原Mesa24.0.5局部修复；仅服务器设置图形库路径 |

从Windows项目根重做同范围短测（每次用全新RunName，保留已有运行）：

```powershell
& '.\\ThinkTwice\\docs\\reproduction\\env-agent\\scripts\\run_candidate_smoke.ps1' -RunName 'smoke-next-unique'
```

该入口默认原route16、自动≥200次停止、强制检查已通过门禁与当前Torch库hash一致的真实batch重放。完整实际命令、门禁文件SHA和环境路径见最终run.json。WSL交互环境可source `scripts/activate_candidate.sh`；只影响当前专用shell。

## 单独记录的部署修复

1. 独立Mesa24/OpenGL D3D12启动：DISPLAY=:0、UE4插值兼容开关，不替换系统Mesa。真实场景触发D3D12三角带聚合复制错误；全符号断言定位后加入标准nir_split_var_copies，并保留原store的数组/结构索引及write_mask。`mesa-triangle-fix-v2.diff`、build.json保留原源与库身份。没有改CARLA shader、地图或渲染质量档位。
2. Torch1.12.1旧Jiterator不认识新设备，向NVRTC11.3传sm120失败。只将NVRTC11.1–11.3的最高目标限定compute86 PTX；算子表达式不变。`torch-nvrtc-arch-fix.diff`；旧candidate库和源码备份保留。当前libtorch_cuda SHA `ce89a629b94ee4847849f180de2ce4b5e6fe56b20c4be360bede046617191c0b`。原构建wheel是修复前基线，当前库身份以final-installed-identities.json为准。
3. 部署overlay v5：专用服务器启动、只回收自身进程组、短超时RPC就绪检查、两处初始化tick墙钟等待120秒（仿真步长仍0.05）。原评测/模型/agent/control源未编辑；diff与manifest在launch/20261009-smoke-v5。
4. 观察子类记录真实输入/输出与控制，原返回值不改。短测SIGINT后给正常清理60秒窗口；smoke11/12表明单纯延长等待无效；原生堆栈证实析构重复访问已关闭服务器。v5仅在正常清理已完成时跳过析构的重复RPC，每路线重置标记；失败和探针空快照记录保留。

## 资产、失败记录与后续边界

CARLA本体3956990664B、地图1823090196B，已校验精确大小、gzip/tar完整性和本地SHA256，完成独立解压及原ImportAssets.sh导入；D:\\Download原下载保留。checkpoint与ResNet初始化缓存已取得，无训练数据。详见CARLA_ASSET_RECOVERY.md与既有asset manifest。所有本地hash仅固定文件身份，不冒称官方发布校验。

- 本体本地SHA256：c441c35528c767962e781000ab61600aaa1fa0c2d1bd148effccdb9bab38d583。
- 附加地图本地SHA256：b64b1d7b92090de99913c7a221984d54c4c462275b4d727e8cd4a20dc529646c。

smoke01–10的native crash/NVRTC错误、smoke11收尾误判及局部解决方案均保留在各run目录与SETUP_LOG.md。曾丢checkpoint._metadata的诊断脚本已修正，未置换权重。T-04字符串扫描不作为无PTX结论，正式readelf/cuobjdump与实际算子分开记录，spconv独立验收。

保留局限：SM120架构警告仍显示，但实际PTX执行已通过上述范围；Mesa候选带断言/GDB，完整长时稳定性/吞吐未验；SDK pip check仅遗留未用的开发/测试依赖，不声称全包依赖检查零警告。

**下一步交接统筹安排完整Town05 Long；本Agent不继续扩大评测、训练或抖动消融。当前没有阻塞短测交付的额外资源或管理员授权。**
'''
(docs / 'FINAL_ENVIRONMENT_REPORT.md').write_text(report, encoding='utf-8')
handover = f'''# ThinkTwice 环境任务交接 — {now}

**已完成用户最终确认的单路线短 smoke（≥200次），未跑完整路线或完整Town05 Long。**

先读 [FINAL_ENVIRONMENT_REPORT.md](FINAL_ENVIRONMENT_REPORT.md)，再读最终 `.thinktwice-runtime/runs/20261009-smoke13-cleanup-final/smoke-acceptance.json`（pass=true）与原 `results.json` / `run.json` / `termination.json`。原整路线记录仍为未完成，不能将其改写为完整评测通过。

- 最终{len(inf)}次连续实时推理、{len(controls)}次合法控制，官方模型1344键strict、完整五轮/六级有限；原控制不变。
- Town05真实摄像头/LiDAR/IMU/API/同步与背景交通通过，自车移动{displacement:.3f}m、路线进度{progress:.6f}%。按用户选择短测主动SIGINT，原评测器退出0，清理竞争已实际复验通过。
- 独立ThinkTwice-Focal/ttenv，Python3.7.16。推理必须PYTHONPATH candidate-site+voxel-candidate；实际Torch ABI1、CUDA11.3 compute86 PTX。不要混用原base torch/lib或旧ABI0 voxel。
- 最终Torch库含NVRTC目标局部修复；最终CARLA图形库为mesa24-triangle-fix-v2。精确source diff、备份、库SHA与命令在报告/证据。原模型、agent、控制源码git diff为空。
- Windows原项目、旧WSL/默认设置、原下载、原torch/Mesa安装及所有失败run均保留。项目根九份规划未修改。
- 重做同范围短测入口：scripts/run_candidate_smoke.ps1 -RunName <全新名称>，默认修复过的图形launcher，自动至少200次后结束。不要运行旧失败launcher或覆盖现有run。
- 当前无本任务训练/评测需继续启动。下一行动由统筹安排完整Town05 Long；勿自行扩大训练、完整评测或抖动消融。

详细历史：SETUP_LOG.md、TAKEOVER_STATUS.md、KNOWN_ISSUES.md。旧段落均为当时状态，以最终报告和真实JSON为当前结论。
'''
(docs / 'HANDOVER.md').write_text(handover, encoding='utf-8')
final_note = f'''\n\n## {now} 最终交付验收\n\n用户最终选择的≥200次短闭环已通过：{len(inf)}次连续实时完整推理、{len(controls)}次合法控制、六级全部finite、移动{displacement:.3f}m、路线{progress:.6f}%，原评测器return0、无server_abort。最终smoke13-cleanup-final/smoke-acceptance.json pass=true；原整路线run/results状态未完成保留。详见FINAL_ENVIRONMENT_REPORT.md与final-delivery-summary.json。资产完成、CARLA/推理通过、短smoke通过分别记录；未训练、未完整Town05 Long。交接统筹，不再扩大运行。\n'''
for name in ('SETUP_LOG.md', 'TAKEOVER_STATUS.md', 'ENVIRONMENT_AUDIT.md', 'COMPATIBILITY_MATRIX.md', 'KNOWN_ISSUES.md', 'CARLA_ASSET_RECOVERY.md'):
    with (docs / name).open('a', encoding='utf-8') as f:
        f.write(final_note)
print(json.dumps(summary, indent=2), flush=True)
