# ThinkTwice 隔离环境交付报告

更新：2026-10-09T21:51:07（本地）。**用户确认的短闭环 smoke 已通过；未完成整条路线或完整 Town05 Long 评测。**

## 实际验收结果

最终运行 `.thinktwice-runtime/runs/20261009-smoke13-cleanup-final`。使用原始 Town05 route16、原场景及120背景交通、官方 checkpoint、完整5轮 refinement 和原控制。

- 连续 **203 次**实时完整推理、**234 次**控制返回；推理step连续，全部输出有限，控制范围全部合法，无模型/传感器异常。
- 自车从路线起点移动 **27.304m**；原评测器记录路线进度 **2.339751%**。
- 用户选定“至少200次推理后结束”，由本任务向自己的原评测器发送 SIGINT，原停止流程写出评分并清理；评测器退出码 **0**，无监督器强制中止。
- 原 `results.json` 的路线状态为 `['Failed']`，RouteCompletion未满100%；原始状态和 `run.json` 的整路线pass=false均保留。**独立 `smoke-acceptance.json` 的短测pass=true**，不冒充整路线通过。
- 实时首个forward同步耗时 7.979560s，后续中位数 0.401091s，范围 0.361350–0.539494s；已有缓存，非空缓存冷启动或整系统FPS。
- 控制最小/最大：`{"steer": [-0.03787636756896973, 0.08677995204925537], "throttle": [0.0, 0.6000000238418579], "brake": [0.0, 0.0]}`。
- 退出后的独立进程核验通过，无本次CARLA/评测器/监督器/停止器残留；项目卷可用 273231343616B。见cleanup-verification.json。

| 阶梯 | 真实结果与证据 |
|---|---|
| 1 Python/依赖/NumPy | Python3.7.16、NumPy1.20.3，CPU/GPU Tensor↔NumPy数值往返通过，无NumPy初始化警告；linux-basics-candidate01.json |
| 2 基础CUDA | randn/mm/conv有限值与同步冷热分开计时通过；首次GPU初始化554.856s，已保留当时缓存/并行构建条件；同上JSON |
| 3 关键算子 | voxel完整wrapper、deformable attention、DCN、spconv实际数值测试通过；candidate-*-01.json。完整官方LiDAR栈[1,512,84,84]有限；candidate-lidar-stack02-metadata.json |
| 4 模型与权重 | 官方1344/1344键/shape strict、128232121参数cuda:0、refine_num5；candidate-model-gpu01.json。NVRTC修复后真实batch连续两次全forward通过；real-batch-replay01.json |
| 5 CARLA | 原0.9.10.1，API/server784d9b9f，Town05/sync0.05/10tick基础通过；最终真实场景/传感器/120交通通过 |
| 6 真实batch | 最终实时203次；pred_wp[1,6,4,2]，mu/sigma[1,6,2]，future_mu/sigma[1,6,3,2]，全部六级有限；agent-events.jsonl及首batch/prediction.pt |
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
& '.\ThinkTwice\docs\reproduction\env-agent\scripts\run_candidate_smoke.ps1' -RunName 'smoke-next-unique'
```

该入口默认原route16、自动≥200次停止、强制检查已通过门禁与当前Torch库hash一致的真实batch重放。完整实际命令、门禁文件SHA和环境路径见最终run.json。WSL交互环境可source `scripts/activate_candidate.sh`；只影响当前专用shell。

## 单独记录的部署修复

1. 独立Mesa24/OpenGL D3D12启动：DISPLAY=:0、UE4插值兼容开关，不替换系统Mesa。真实场景触发D3D12三角带聚合复制错误；全符号断言定位后加入标准nir_split_var_copies，并保留原store的数组/结构索引及write_mask。`mesa-triangle-fix-v2.diff`、build.json保留原源与库身份。没有改CARLA shader、地图或渲染质量档位。
2. Torch1.12.1旧Jiterator不认识新设备，向NVRTC11.3传sm120失败。只将NVRTC11.1–11.3的最高目标限定compute86 PTX；算子表达式不变。`torch-nvrtc-arch-fix.diff`；旧candidate库和源码备份保留。当前libtorch_cuda SHA `ce89a629b94ee4847849f180de2ce4b5e6fe56b20c4be360bede046617191c0b`。原构建wheel是修复前基线，当前库身份以final-installed-identities.json为准。
3. 部署overlay v5：专用服务器启动、只回收自身进程组、短超时RPC就绪检查、两处初始化tick墙钟等待120秒（仿真步长仍0.05）。原评测/模型/agent/control源未编辑；diff与manifest在launch/20261009-smoke-v5。
4. 观察子类记录真实输入/输出与控制，原返回值不改。短测SIGINT后给正常清理60秒窗口；smoke11/12表明单纯延长等待无效；原生堆栈证实析构重复访问已关闭服务器。v5仅在正常清理已完成时跳过析构的重复RPC，每路线重置标记；失败和探针空快照记录保留。

## 资产、失败记录与后续边界

CARLA本体3956990664B、地图1823090196B，已校验精确大小、gzip/tar完整性和本地SHA256，完成独立解压及原ImportAssets.sh导入；D:\Download原下载保留。checkpoint与ResNet初始化缓存已取得，无训练数据。详见CARLA_ASSET_RECOVERY.md与既有asset manifest。所有本地hash仅固定文件身份，不冒称官方发布校验。

- 本体本地SHA256：c441c35528c767962e781000ab61600aaa1fa0c2d1bd148effccdb9bab38d583。
- 附加地图本地SHA256：b64b1d7b92090de99913c7a221984d54c4c462275b4d727e8cd4a20dc529646c。

smoke01–10的native crash/NVRTC错误、smoke11收尾误判及局部解决方案均保留在各run目录与SETUP_LOG.md。曾丢checkpoint._metadata的诊断脚本已修正，未置换权重。T-04字符串扫描不作为无PTX结论，正式readelf/cuobjdump与实际算子分开记录，spconv独立验收。

保留局限：SM120架构警告仍显示，但实际PTX执行已通过上述范围；Mesa候选带断言/GDB，完整长时稳定性/吞吐未验；SDK pip check仅遗留未用的开发/测试依赖，不声称全包依赖检查零警告。

**下一步交接统筹安排完整Town05 Long；本Agent不继续扩大评测、训练或抖动消融。当前没有阻塞短测交付的额外资源或管理员授权。**

## 交接补充：本轮做了哪些工作

本节于2026-10-09按用户要求补充。这里的“环境跑通”指：在本机RTX5080 Laptop的独立Linux环境中，官方checkpoint实际完成关键CUDA算子、真实CARLA传感器输入、原agent推理和车辆闭环控制，并通过用户指定的短测范围。它不代表已验收完整路线、完整Town05 Long或20Hz墙钟实时性能。最终控制覆盖的仿真时长约11.65秒；同步仿真允许等待推理，0.05秒仿真步长不能解释为每秒完成20次实际推理。

| 工作 | 实际完成内容 |
|---|---|
| 接手续核 | 读取交接、环境报告和项目规划，复用现有安装资产、构建和诊断结果；修正仅凭字符串扫描判断无PTX等旧结论 |
| 隔离平台 | 在专用ThinkTwice-Focal中推进Ubuntu20.04/Python3.7旧栈；保留Ubuntu、Ubuntu-D和Windows默认环境；未进行整套现代框架迁移 |
| 旧依赖兼容 | 源码构建Torch1.12.1及匹配扩展，统一实际C++ ABI1；将voxel/MMCV/vision链接到同一候选Torch；隔离CUDA11.3与cuDNN8.3.2运行库，避免旧/新库混载 |
| 逐层验证 | 验证NumPy往返、基础CUDA、voxel、deformable attention、DCN、spconv、完整LiDAR栈、完整模型及官方checkpoint；构造成功与实际forward分别记录 |
| 模型资产 | 复用项目根thinktwice.pth；严格核对1344键与shape；保留checkpoint元数据，解决诊断脚本丢失_metadata导致的误判；取得原模型所需ResNet初始化缓存 |
| CARLA资产 | 复用D:\Download的0.9.10.1本体和附加地图，核对大小/本地SHA、归档完整性，独立解压并运行原ImportAssets.sh；保留原egg文件名 |
| 图形兼容 | 建立独立Mesa24 D3D12路径；定位UE4着色器插值兼容问题和真实场景的native crash；通过同版本符号/断言定位后实施局部图形驱动补丁 |
| 真实闭环 | 接通原agent真实摄像头/LiDAR等传感器，保存首batch和预测；完成203次连续推理、234次控制及车辆/路线推进确认 |
| 收尾与交付 | 根据原生堆栈修复析构重复RPC；评分保存后正常退出0，核验进程无残留；保留所有失败run、局部尝试和最终证据 |

## 交接补充：代码与构建改动清单

### A. ThinkTwice原始模型、agent与控制

原仓库基准HEAD为 `e9cf2fc078f6ab8175b1a4929faaa8be55f3aa97`。交付时宿主Git状态仅显示新增 `docs/reproduction/`；原有跟踪代码无修改。检查命令与结果保存在 `evidence/20261009-takeover/final-original-source-check.json`。

模型数学、网络结构、原配置、官方权重、五轮refinement、原agent传感器定义和控制规则未修改。没有降低refinement次数、转置/替换checkpoint权重、运行训练或更改项目根九份规划文档。原 `leaderboard/leaderboard/leaderboard_evaluator.py` 也保留原文件；实际执行的是下面单独生成的副本。

### B. 隔离环境里的两个依赖源码补丁

这些改动位于专用WSL的 `/opt/thinktwice`，不会体现在ThinkTwice仓库Git diff中，因此交接必须同时保留源码diff与已安装库身份。

| 补丁 | 原因与准确改动 | 文件与复现脚本 |
|---|---|---|
| Torch NVRTC目标选择 | 真实batch在spatial_shapes.prod处触发NVRTC不接受sm120。只在旧jit_utils.cpp目标判断中增加NVRTC11.1–11.3最高8.6分支，沿用原逻辑对更新设备生成compute86 PTX；未改算子表达式 | WSL源码 `/opt/thinktwice/src/pytorch-1.12.1/aten/src/ATen/native/cuda/jit_utils.cpp`；`evidence/20261009-takeover/torch-nvrtc-arch-fix.diff`；`scripts/build_torch_nvrtc_arch_fix.py` |
| Mesa D3D12三角带处理 | 真实场景触发聚合复制断言；加入标准nir_split_var_copies，在重写输出store时保留原数组/结构deref路径及write_mask。修复驱动内的复制/索引处理，未编辑CARLA shader或模型 | WSL源码 `/opt/thinktwice/src/mesa-24.0.5/src/gallium/drivers/d3d12/d3d12_nir_passes.c`；`evidence/20261009-takeover/mesa-triangle-fix-v2.diff`；依次对应 `scripts/build_mesa_triangle_copy_fix.py`、`scripts/build_mesa_triangle_index_fix.py` |

Torch只重编受影响的C++对象并重新链接候选libtorch_cuda；已安装库身份以final-installed-identities.json为准。原构建wheel未包含后加的NVRTC补丁，不能只凭该wheel恢复最终环境。旧库备份为 `/opt/thinktwice/candidate-backups/torch-before-nvrtc-arch-fix/libtorch_cuda.so`，旧源备份带 `.before-nvrtc-arch-fix` 后缀。

Mesa原源备份带 `.before-triangle-copy-fix` 后缀，原mesa24/mesa24-debug及第一版候选库均保留。当前候选库是 `/opt/thinktwice/mesa24-triangle-fix-v2/lib/dri/swrast_dri.so`，本地SHA256为 `94410eaf19a0a9aa9de645736ffb6cba0d5b55c265d8e11ad343a6384db8d12b`；不是已宣称合入上游的补丁。

两份build.json中的runtime_validation=pending是“刚构建完成、尚未运行”的历史快照，刻意保留；后续验收应读real-batch-replay01.json与最终smoke13的smoke-acceptance.json，而非把历史pending理解为当前仍未验证。

MMCV/torchvision/voxel另有重新编译和链接，但未修改其算子源码公式。voxel使用原setup.py和ops的独立源码副本，见relink-sources.json；正式readelf/cuobjdump结果见relinked-extension-identities.json，实际数值执行另见candidate算子JSON。

### C. 单独生成的评测启动覆盖层

实际入口文件为项目根 `.thinktwice-runtime/launch/20261009-smoke-v5/leaderboard_evaluator_wsl.py`。由 `scripts/prepare_smoke_overlay.py` 从原评测器生成，逐行diff在同目录 `evaluator-deployment.diff`，身份与范围在manifest.json。覆盖层SHA256为 `5d5920e87de69b86e3af89479fc436d014d56fe8f3541f4b56282ab8a87c38b2`。

具体修改：

1. 将硬编码的DISPLAY空启动命令改为调用本任务的进程级图形启动脚本；用参数列表启动并创建独立进程组。
2. 替换全局killall为只回收本评测器启动的CARLA进程组，避免干扰其他环境。
3. 用最长180秒的独立短连接就绪探针替代固定启动sleep；原正式客户端在服务就绪后创建。
4. 两处初始化world.tick增加120秒墙钟等待额度；同步模式与0.05秒仿真步长不变。
5. 每路线重置清理完成标记，正常_cleanup完成后设置标记；析构仅在尚未完成清理时再调用_cleanup，避免服务器已关闭后的重复RPC。正常路线清理流程仍执行。

同目录routes_town05_single.xml只从官方routes_town05_long.xml选取原route16，保留其全部原waypoints，没有压短/改写路线。达到200次后停止由监督脚本完成，而不是将路线伪装成已经完成。

### D. 新增启动、诊断和验收脚本

以下路径均相对于 `ThinkTwice/docs/reproduction/env-agent/`；这些是本任务的工具文件。

| 文件/组 | 用途与行为影响 |
|---|---|
| `scripts/activate_candidate.sh` | 为当前专用WSL shell设置候选包、CUDA/cuDNN与缓存路径，不改系统默认Python |
| `scripts/run_candidate_smoke.ps1` | Windows统一入口，选择ThinkTwice-Focal/ttenv和已验证门禁，要求全新运行目录 |
| `scripts/run_single_route_smoke.py` | 启动原路线/原场景，保留官方权重和配置；监测自身CARLA状态并保存run.json；默认短测200次 |
| `scripts/launch_carla_wsl_triangle_fix_v2.sh` | 仅给CARLA设置DISPLAY、独立Mesa DRI/D3D12和插值兼容选项；当前保留GDB/断言诊断能力 |
| `scripts/thinktwice_observed_agent.py` | 原agent的观察子类，调用原setup/run_step/forward；断言五轮、六级有限值与控制范围；保存首真实batch/预测并逐步记录，返回原预测/原control |
| `scripts/finish_short_smoke.py` | 观察推理达到阈值后，以只读客户端确认Town05、自车与位移；仅向本次评测器发SIGINT，经原停止流程保存评分；生成独立短测验收JSON |
| `scripts/replay_real_sensor_batch.py` | 重放已保存真实batch，strict加载带_metadata的官方checkpoint并验证两次完整forward；不改权重 |
| `scripts/probe_*.py`、`audit_loaded_candidate.py` | 分层诊断依赖、CUDA、算子、模型、CARLA及实际加载库；成功范围以各自证据为准 |
| `scripts/build_*.sh/.py`、`prepare_relink_sources.py`、`install_relinked_mmcv.py` | 保存旧栈构建、依赖补丁、扩展重链接的执行方法；已有成功安装无需重新全量构建 |
| `scripts/stage_carla_archives.py`、`deploy_carla_release.py`、`import_carla_maps_official.py` | 复用下载文件、大小/哈希/归档检查、独立部署及调用原地图导入方式 |
| `scripts/capture_final_environment.py`、`verify_final_cleanup.py` | 保存最终库身份，检查测试结束后无相关进程残留；当前verify脚本固定本次最终run |
| `scripts/finalize_environment_delivery.py` | 依据本次最终run生成初版交付文档，属于本次证据整理工具；不要盲目重跑覆盖本节人工补充 |

观察插桩增加了CUDA同步、有限值检查和日志开销，因此上述耗时不等同于无插桩性能。旧失败launcher、旧overlay和旧报告生成脚本为审计保留，不是当前推荐入口。

## 交接补充：接手者直接使用的方法

Windows下可从任意目录调用绝对路径入口，使用全新RunName，例如：

```powershell
& 'D:\Desktop\端到端自动驾驶开源模型调研\ThinkTwice\docs\reproduction\env-agent\scripts\run_candidate_smoke.ps1' -RunName 'handoff-short-001'
```

该命令会再次运行同范围短测；本次报告整理未重新启动评测。不要把重跑诊断或重新全量编译作为接手的前提。

查看最终结果时按以下顺序读取项目根中的文件：

1. `.thinktwice-runtime/runs/20261009-smoke13-cleanup-final/smoke-acceptance.json`：短测pass=true、次数、位移、输出/控制检查、退出0。
2. 同目录 `results.json`、`run.json`：原评分及真实命令；主动短停导致整路线状态Failed，原样保留。
3. 同目录 `termination.json`、`cleanup-verification.json`、`console.log`：主动终止原因、进程清理及原始控制台。
4. 同目录的 `sensor-inference/` 下：`agent-events.jsonl`、`first-real-batch.pt`、`first-real-prediction.pt`：输入/输出shape、逐次有限值、控制和真实快照。
5. `ThinkTwice/docs/reproduction/env-agent/evidence/20261009-takeover/final-installed-identities.json`、`final-delivery-summary.json`及两份源码diff：恢复环境时的版本/二进制身份和补丁依据。

交接时应保留项目 `.thinktwice-runtime` 资产/运行目录、env-agent文档脚本和专用WSL里的 `/opt/thinktwice`。项目文件夹本身不包含完整Linux已安装环境；迁移到另一台机器需要另行迁移该专用环境或按构建记录恢复。无需因此修改/删除原有WSL。

当前没有遗留运行进程需要继续等待。下一步由统筹决定完整Town05 Long及长时稳定性验证；扩展评测前保留当前已通过环境与本次证据，使用新的输出目录。
