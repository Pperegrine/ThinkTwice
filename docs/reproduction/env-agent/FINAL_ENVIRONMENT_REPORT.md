# ThinkTwice 最终环境说明

整理日期：2026-10-10。环境身份与验收依据：2026-10-09 最终安装记录及 smoke13；本轮未重新运行环境验证。本文是唯一权威环境说明，旧环境报告的必要信息已合并，排障流水账从 Git 历史恢复。

**短闭环通过，完整路线未完成。** 原 Town05 route16、120背景交通、官方 checkpoint、五轮 refinement 及原控制下，203次连续完整推理、234次控制，输出有限、控制合法，车辆移动27.304m，路线进度2.339751%。达到用户指定≥200次后主动 SIGINT，原评测器保存评分、退出0，独立清理检查通过。原 `results.json` 状态 Failed、`run.json` 整路线 pass=false；独立 `smoke-acceptance.json` 短测 pass=true。不能据此声明完整 Town05 Long、长时稳定性或跨机器兼容已通过。

## 1. 版本、路径与原位保护

所有项目相对路径以 `D:\Desktop\端到端自动驾驶开源模型调研` 为根；本文链接相对于本文。旧栈经本机适配才成功，不能直接用官方旧 wheel 替换最终安装库。

| 项目 | 最终记录 |
|---|---|
| 主机 | RTX5080 Laptop 16GB，SM120；Windows11 build26200.9457，驱动595.79；这是验收时身份 |
| 专用 WSL | `ThinkTwice-Focal`，Ubuntu20.04.5，用户 `ttenv`，GCC9.4；入口显式 `-u ttenv`，发行版默认UID0不能代替 |
| Python | `/opt/thinktwice/conda/bin/python` 3.7.16 |
| 候选包 | `/opt/thinktwice/candidate-site`：Torch1.12.1、torchvision0.13.1、MMCV1.7.0、mmdet3d1.0.0rc6；实际C++ ABI1 |
| 基础依赖 | conda内 NumPy1.20.3、spconv-cu113 2.3.6、cumm-cu113 0.4.11；不混入系统Python |
| CUDA/cuDNN | `/opt/thinktwice/cuda113-ptx` 11.3、`/opt/thinktwice/cudnn832-runtime/lib` 8.3.2 |
| voxel | `/opt/thinktwice/voxel-candidate`，原完整wrapper及匹配ABI1扩展；旧 `/opt/thinktwice/build` 不是当前入口 |
| CARLA | `/opt/thinktwice/carla-0.9.10.1`，API/server `784d9b9f`；实际egg名 `carla-0.9.10-py3.7-linux-x86_64.egg`，不要重命名 |
| 图形驱动 | `/opt/thinktwice/mesa24-triangle-fix-v2/lib/dri/swrast_dri.so`；同时依赖 `mesa24-debug/lib` 的libglapi及 `mesa24/lib` 的libdrm |
| 缓存 | `/opt/thinktwice/cuda-cache`（4GiB上限）、`/opt/thinktwice/torch-cache`、`/home/ttenv/.cache/Python-Eggs`；保留现有内容 |

最终身份：[final-installed-identities.json](evidence/20261009-takeover/final-installed-identities.json)、[relinked-extension-identities.json](evidence/20261009-takeover/relinked-extension-identities.json)。`pip-freeze-final.txt` 是候选安装完成前的历史快照，含旧wheel，**不是最终环境锁文件**，不能直接 `pip install -r` 恢复最终环境。

原模型基准 `e9cf2fc078f6ab8175b1a4929faaa8be55f3aa97`，环境交付提交 `f68807520c0e65c11baa7114c49a234f69206353`。原模型、配置、agent、控制、训练源码未改；本轮只精简新增交付材料。原源码身份见 [final-original-source-check.json](evidence/20261009-takeover/final-original-source-check.json)。

## 2. 推荐入口与门禁

后续验证时，在 Windows 使用全新 RunName：

```powershell
& 'D:\Desktop\端到端自动驾驶开源模型调研\ThinkTwice\docs\reproduction\env-agent\scripts\run_candidate_smoke.ps1' -RunName 'handoff-short-001'
```

该命令会实际启动短闭环，本轮未执行。默认链路为：`run_candidate_smoke.ps1` → `run_single_route_smoke.py` → v5覆盖层及 `launch_carla_wsl_triangle_fix_v2.sh` → 原agent的观察子类 `thinktwice_observed_agent.py` → `finish_short_smoke.py` 主动短停。采用 `/opt/thinktwice/conda/bin/python`；shell配置由 [activate_candidate.sh](scripts/activate_candidate.sh) 设置候选PYTHONPATH、CUDA/cuDNN、缓存与专用启动器，不改系统默认环境。

入口读取 `evidence/20261009-takeover/` 下9个门禁文件：

- `linux-basics-candidate01.json`
- `candidate-deform-01.json`、`candidate-dcn-01.json`、`candidate-spconv-01.json`、`candidate-voxel-01.json`
- `candidate-lidar-stack02-metadata.json`
- `extensions-candidate-identity01.json`
- `candidate-model-gpu01.json`
- `real-batch-replay01.json`

门禁范围分别为基础依赖/CUDA、实际数值算子、完整LiDAR栈、扩展身份、strict模型加载及真实batch重放。入口**读取既有通过证据并核对当前Torch库SHA**，不等于每次启动前重新执行所有测试。重建环境后需要重新产生匹配身份的门禁，不能沿用旧JSON冒充新环境通过。

真实重放输入固定为 `.thinktwice-runtime/runs/20261009-smoke10-triangle-index-fix/sensor-inference/first-real-batch.pt`，对应 [real-batch-replay01.json](evidence/20261009-takeover/real-batch-replay01.json) 的batch字段。输入39796762B，SHA256 `988f428ea008216ea8ef5156503d5200866491c75c5af3076249fea9ae57a4b1`。恢复后使用 `replay_real_sensor_batch.py`，保留checkpoint OrderedDict `_metadata`，不能用权重置换/转置解决诊断错误。

## 3. 必须保留的补丁与最终库身份

### Torch NVRTC

[source diff](evidence/20261009-takeover/torch-nvrtc-arch-fix.diff) / [修补工具](scripts/build_torch_nvrtc_arch_fix.py)：`/opt/thinktwice/src/pytorch-1.12.1/aten/src/ATen/native/cuda/jit_utils.cpp` 增加 NVRTC11.1–11.3 最大8.6目标判断，使SM120通过compute86 PTX JIT；未修改算子表达式。最终源SHA256 `918011e0818004fc00a3806adaec3ac954f43d85c61c2a5e5aa5d99916255a66`。

| 库/归档 | SHA256与含义 |
|---|---|
| `candidate-site/torch/lib/libtorch_cuda.so`，310286504B | `ce89a629b94ee4847849f180de2ce4b5e6fe56b20c4be360bede046617191c0b`，最终补丁库 |
| `candidate-backups/torch-before-nvrtc-arch-fix/libtorch_cuda.so` | `a238b223a56fb9865fa3f8498a506e73aa6feaf0939317c429a9a1cd4bec06a4`，修补前备份 |
| `src/pytorch-1.12.1/dist/torch-1.12.1-cp37-cp37m-linux_x86_64.whl`，241337019B | `af7c29d1098016808c9f1affee84843a6028123027cea6a1163cdb78fdf8fa0a`，内含修补前库，不能单独恢复最终环境 |

以上路径相对 `/opt/thinktwice`。最终库RUNPATH仍引用 `src/pytorch-1.12.1/build/lib`、`cuda113-ptx/lib`、`cudnn832-link/lib`。Python历史加载记录与单独ldd可能选择不同来源，不能只复制candidate-site后删除构建树。`cudnn832-link/lib/libcudnn.so` 又指向conda基础Torch的cuDNN；基础环境不能按“旧版本”删除。

构建脚本曾导出 `_GLIBCXX_USE_CXX11_ABI=0`，CMake缓存亦记录0，但该版CMake分支未将宏0实际传入GCC9；最终二进制测得**ABI1**。恢复应核对实际Torch及全部扩展ABI、readelf/PTX和数值门禁，不能凭配置名断言ABI0成功。

### Mesa与评测覆盖层

[Mesa累计diff](evidence/20261009-takeover/mesa-triangle-fix-v2.diff)：先运行copy-fix补丁，再index-fix；加入 `nir_split_var_copies`，保留数组/结构deref及原write_mask，不硬写0xf。最终源 `src/mesa-24.0.5/src/gallium/drivers/d3d12/d3d12_nir_passes.c` SHA256 `e4fbc5a5a906e14146b090676805e4eea0fd475b6bf2f47c8bb45a4b899679f3`；最终DRI库111524344B，SHA256 `94410eaf19a0a9aa9de645736ffb6cba0d5b55c265d8e11ad343a6384db8d12b`。保留源备份 `.before-triangle-copy-fix` / `.before-triangle-index-fix` 及成功构建目录。构建JSON中的validation=pending是构建当时快照，后续真实验收看replay及smoke13。

当前launcher使用DISPLAY=:0、D3D12/NVIDIA、`allow_glsl_cross_stage_interpolation_mismatch=true`、v2 DRI及mesa24-debug/mesa24支撑库；GDB仍是当前传递依赖，不能仅凭debug名称删库。

v5覆盖层位于 `.thinktwice-runtime/launch/20261009-smoke-v5/`，评测器SHA256 `5d5920e87de69b86e3af89479fc436d014d56fe8f3541f4b56282ab8a87c38b2`。[prepare_smoke_overlay.py](scripts/prepare_smoke_overlay.py) 从原评测器生成副本：独立进程组替代全局killall、180s就绪探针、初始化tick120s等待、避免正常清理后的重复析构RPC；同步步长仍0.05s。单路线XML保留route16全部waypoints，SHA256 `1475a447c063a3e34b2d84311fc6270e5efb09e9f5c652dbe0fd2cd6c70e4e4e`。观察子类SHA256 `b1aa24eeaf7c0f2f5e4a67d34f09c83b45c7583ec89ca79bccaa7c598acb6b1b`，保留原预测/控制并核对六级有限值。不要移动覆盖层、改路径深度或改原评测器替代副本。

## 4. 恢复顺序（仅供后续恢复，已有环境无需重建）

1. 递归克隆外层及子模块，保留项目层级，恢复Windows本地资产和专用WSL。Git不含Linux安装环境、VHD、库、缓存或完整run。首选另行备份完整专用发行版；本轮不导出镜像。恢复用新发行版名/目录，不覆盖现有ThinkTwice-Focal；若改变项目根或WSL名，先审阅全部固定引用。
2. 专用Ubuntu20.04/Python3.7环境：审阅 `bootstrap_linux.sh`；需要编译工具、binutils、OpenGL/SDL/Vulkan/OMP库、egg的PNG/JPEG/TIFF库及GDB。`install_scientific_runtime.py` 与 `fetch_large_py37_wheels.py` 保存旧Python依赖安装方法；源码与wheel以现有manifest/版本记录核对，不盲装现代最新版。
3. 隔离CUDA11.3与cuDNN8.3.2，使用现有精确包manifest；早期混入CUDA13的 `/opt/thinktwice/cuda-11.3` 不是成功prefix。CUDA profiler头文件曾需从 `cuda-nvprof-11.3.111-h95a27d4_0.tar.bz2`（SHA256 `1134b9349cab226cdac422e4b77adce03ca4daf431a6348d347539818bf27cb5`）仅提取 `include/cuda_profiler_api.h` 和 `include/cudaProfiler.h` 至cuda113-ptx缺失处，不整包覆盖。
4. `fetch_torch_submodules.py` 恢复固定gitlink的第三方源码；`build_torch112_ptx.sh` 建Torch/vision基础，随后 `build_torch_nvrtc_arch_fix.py` 局部重编重链接最终库。保留原备份及绝对RUNPATH依赖；旧wheel不足以恢复最终补丁。
5. `prepare_relink_sources.py`、`build_candidate_extension.sh`、`install_relinked_mmcv.py` 恢复匹配候选Torch的voxel/MMCV，`build_mmdet3d_rc6_ptx.sh` 恢复固定mmdet3d源码。使用现有安装记录核对vision与所有扩展ABI1，不使用已淘汰ABI0安装链。
6. Mesa24.0.5：`build_mesa24_d3d12.sh` → `build_mesa24_debug.sh` → `build_mesa_triangle_copy_fix.py` → `build_mesa_triangle_index_fix.py`。需要同版源码、独立DirectX-Headers1.611.0/libdrm2.4.120、PKG_CONFIG_PATH、Mesa构建venv（Meson1.3.2/Mako1.3.5）及XCB开发依赖。不能只装最终DRI而遗漏支撑库；源包和本机身份清单仍保存在本地资产/历史取证记录中。
7. `stage_carla_archives.py` → `deploy_carla_release.py` → `import_carla_maps_official.py`：核验现有0.9.10.1归档，独立解压并调用原ImportAssets.sh；保持egg原名和conda `carla.pth` 绝对指向。根 `carla-0.9.10.zip` 是源码ZIP，不是运行时；已废弃的Docker抓取路线不作为恢复方案。
8. 恢复checkpoint、ResNet缓存、v5覆盖层、smoke10输入和smoke13证据；核对实际包路径/库SHA，再按基础→算子→LiDAR→strict模型→真实重放产生新门禁，最后用推荐入口做短闭环。不将旧门禁直接认作新安装验收。恢复工具包含固定目标与防覆盖断言，须逐步审阅，不是可批量重跑的一键安装器。

关键外部资产（均不提交Git，本地SHA只证明身份，不代表官方签名）：

| 原位资产 | 字节数 / SHA256 |
|---|---|
| 根 `thinktwice.pth` | 515776025 / `6c86b4ad020cb4b5b67d77929d884a878172a5dc56bd8103ff614f68a828d1b5` |
| `.thinktwice-runtime/assets/resnet50-0676ba61.pth` 与WSL torch-cache副本 | 102530333 / `0676ba61b6795bbe1773cffd859882e5e297624d384b6993f7c9e683e722fb8a` |
| `.thinktwice-runtime/assets/carla-0.9.10.1-release/CARLA_0.9.10.1.tar.gz` | 3956990664 / `c441c35528c767962e781000ab61600aaa1fa0c2d1bd148effccdb9bab38d583` |
| 同目录 `AdditionalMaps_0.9.10.1.tar.gz` | 1823090196 / `b64b1d7b92090de99913c7a221984d54c4c462275b4d727e8cd4a20dc529646c` |

D:\Download原下载、所有 `/opt/thinktwice` 库/构建目录、CUDA/Mesa/ResNet缓存、checkpoint、CARLA/地图、WSL镜像、v5、smoke10、smoke13本轮均不清理。

## 5. 保留工具及职责（33个）

路径均在 `scripts/`。当前运行链及其传递依赖保持原字节；恢复工具即使当前启动不调用，也不因此删除。

| 文件 | 保留原因 |
|---|---|
| activate_candidate.sh | 专用shell环境与当前库/缓存路径 |
| run_candidate_smoke.ps1 | 推荐Windows入口与9个门禁 |
| run_single_route_smoke.py | 监督器、真实库身份核对与运行参数 |
| launch_carla_wsl_triangle_fix_v2.sh | 最终Mesa/GDB/CARLA启动 |
| thinktwice_observed_agent.py | 原agent观察与有限值/控制检查 |
| finish_short_smoke.py | 短停、原清理及独立验收 |
| prepare_smoke_overlay.py | 恢复v5及单路线XML |
| replay_real_sensor_batch.py | 真实输入重放门禁 |
| bootstrap_linux.sh | 专用基础环境恢复 |
| install_scientific_runtime.py | Python3.7科学依赖 |
| fetch_large_py37_wheels.py | 离线依赖取得 |
| fetch_torch_submodules.py | 固定Torch子模块源码 |
| build_torch112_ptx.sh | Torch/vision基础PTX构建 |
| build_torch_nvrtc_arch_fix.py | 最终NVRTC补丁与重链接 |
| prepare_relink_sources.py | 独立voxel/MMCV重链接源码 |
| build_candidate_extension.sh | 候选ABI扩展构建 |
| install_relinked_mmcv.py | 安装匹配候选的MMCV |
| build_mmdet3d_rc6_ptx.sh | 固定mmdet3d恢复 |
| build_mesa24_d3d12.sh | Mesa及独立依赖基础 |
| build_mesa24_debug.sh | 当前支撑库及补丁构建前提 |
| build_mesa_triangle_copy_fix.py | 第一阶段必需补丁 |
| build_mesa_triangle_index_fix.py | 最终累计补丁 |
| stage_carla_archives.py | 本体/地图来源与哈希核验 |
| deploy_carla_release.py | CARLA独立部署 |
| import_carla_maps_official.py | 原地图导入流程 |
| probe_basics.py | 基础依赖/CUDA恢复门禁 |
| probe_ops.py | 实际算子恢复门禁 |
| probe_lidar_stack.py | 完整LiDAR与metadata验证 |
| probe_model_checkpoint.py | strict模型/设备验证 |
| audit_loaded_candidate.py | 实际加载库审计 |
| record_relinked_binaries.py | 扩展readelf/PTX身份记录 |
| capture_final_environment.py | 最终安装库哈希采集 |
| verify_final_cleanup.py | 新run结束后的进程清理检查 |

身份采集工具要求显式新输出：capture使用 `--output`，record使用 `--output-dir`，cleanup使用 `--run-dir` 与 `--output`，拒绝覆盖历史证据。诊断默认voxel根为最终 `voxel-candidate`，仍支持THINKTWICE_VOXEL_ROOT显式覆盖。

## 6. 验收证据、现存问题与路径约束

最终原始证据位于项目根 `.thinktwice-runtime/runs/20261009-smoke13-cleanup-final/`：按 `smoke-acceptance.json` → `results.json`/`run.json` → `termination.json`/`cleanup-verification.json`/`console.log` → `sensor-inference/` 的events及首batch/预测读取。Git中的 [final-delivery-summary.json](evidence/20261009-takeover/final-delivery-summary.json) 是必要摘要，不能代替原始run。

模型strict加载1344键、128232121参数，refine_num=5，输出六级。最终实时首forward7.979560s、后续中位0.401091s（0.361350–0.539494s），已有缓存且观察插桩有CUDA同步/日志开销，不是20Hz或无插桩吞吐证明。历史首次GPU初始化554.856s不代表稳态性能，也不承诺新机器冷启动时间。完整路线、长时运行、空缓存及迁移后结果仍待验证；本轮不运行评测。

固定引用包括：入口的WSL名/用户/9门禁；脚本 `parents[5]` 和shell向上五层定位项目根；v5的具体launch路径；真实batch默认路径；conda carla.pth/egg路径；Torch RUNPATH与cuDNN软链；CARLA launcher的Mesa前缀。移动报告目录中的scripts/evidence、运行目录或 `/opt/thinktwice` 会影响这些入口。本文/README可以编辑内容，但不应随意移动其相邻工具和门禁。

研究规划中的早期环境表是有日期的历史判断，不取代本文。精简前资产盘点位于外层 `docs/reproduction/asset-audit/20261010/`，其原始JSON/GZ与验证记录是整理前快照；本次删除和保护核验记录追加在原ASSET_AUDIT中。未清理未明确依赖的原始日志、证据、缓存与构建树。
