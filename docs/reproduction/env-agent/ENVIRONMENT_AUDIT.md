> **2026-10-09 接手更正：本文件下方为上一轮历史审计/原始日志。当前授权、状态和纠正以 [TAKEOVER_STATUS.md](TAKEOVER_STATUS.md)、[COMPATIBILITY_MATRIX.md](COMPATIBILITY_MATRIX.md)、[KNOWN_ISSUES.md](KNOWN_ISSUES.md) 为准。旧文中“仅审计等待决策”“MMCV/spconv必然失败”“全模型数十小时”“必须注销WSL”等结论不再有效；原错误输出保留，不作为当前通过声明。**

# ThinkTwice 环境审计报告（ENVIRONMENT_AUDIT）

- 审计时间：2026-10-09
- 审计对象：`OpenDriveLab/ThinkTwice`（CVPR 2023）本地克隆
- 审计范围：**仅环境与依赖兼容性**。不涉及复现计划、实验设计、模型性能优化。
- 负责人：环境与依赖兼容性 Agent
- 工作目录：`docs/reproduction/env-agent/`（与另一名 Agent 的计划文档隔离）

> 本报告中所有结论均标注证据来源。未实际执行的测试一律标记为「未验证」，不作通过结论。

---

## 一、实测机器信息

以下数据全部来自本机实际命令输出，非假设。

### 1.1 操作系统

| 项目 | 实测值 | 来源命令 |
|---|---|---|
| 产品名 | Windows 11 家庭版（Home） | `Get-CimInstance Win32_OperatingSystem` |
| 版本 | 10.0.26200 | 同上 |
| 构建号 | **26200.9457** | `cmd.exe /c ver` |
| 架构 | 64 位 | `Win32_OperatingSystem.OSArchitecture` |
| 物理内存 | 32 GB（TotalVisibleMemorySize = 32,947,252 KB ≈ 31.4 GiB） | 同上 |
| 当前可用内存 | ≈ 6.4 GB（FreePhysicalMemory = 6,691,428 KB） | 同上 |

注：Windows 11 内部版本号 26200 属于 Windows 11 25H2 / 26H1 分支，远高于 WSL2 与 CARLA 0.9.10 官方文档所针对的系统基线。

### 1.2 GPU

| 项目 | 实测值 | 来源命令 |
|---|---|---|
| GPU 0 | **NVIDIA GeForce RTX 5080 Laptop GPU** | `nvidia-smi` |
| GPU 1 | Intel(R) Graphics（核显） | `Get-CimInstance Win32_VideoController` |
| 显存 | **16303 MiB（≈ 16 GB）** | `nvidia-smi` |
| 驱动版本（NVIDIA 口径） | **595.79** | `nvidia-smi` |
| 驱动版本（WDDM 口径） | 32.0.15.9579 | `Win32_VideoController.DriverVersion` |
| CUDA Driver API 版本 | **13.2** | `nvidia-smi` 右上角 |
| 计算能力 | **(12, 0) → sm_120（Blackwell）** | `torch.cuda.get_device_capability(0)` 实测 |
| 功耗上限 | 175 W | `nvidia-smi` |
| 当前占用 | 0 MiB / 0 %，无运行中进程 | `nvidia-smi` |

**关键点**：RTX 5080 属于 NVIDIA Blackwell 架构，计算能力 **sm_120**。这是本次审计的核心矛盾来源，详见 `COMPATIBILITY_MATRIX.md`。

`Win32_VideoController.AdapterRAM` 报告为 4,293,918,720 字节（≈4 GB），这是 WDDM 的 32 位字段溢出伪值，**不是真实显存**；真实显存以 `nvidia-smi` 的 16303 MiB 为准。

### 1.3 CUDA / 编译工具链（Windows 侧）

| 项目 | 实测值 | 来源命令 |
|---|---|---|
| `nvidia-smi` | 存在，595.79 / CUDA 13.2 | `nvidia-smi` |
| `nvcc` | **未安装**（`command not found`） | `nvcc --version` |
| CUDA Toolkit 目录 | **不存在** | `ls "C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/"` |
| Visual Studio | 存在，版本目录为 `18` | `ls "C:/Program Files/Microsoft Visual Studio/"` |

结论：本机有 **CUDA 驱动**（运行期），但**没有任何 CUDA Toolkit**（编译期）。任何需要编译 CUDA 扩展的步骤都必须先安装 Toolkit。

### 1.4 Python / Conda

| 项目 | 实测值 | 来源命令 |
|---|---|---|
| Conda | **26.1.1**，路径 `C:\Users\Peregrine\miniconda3` | `conda --version` |
| Conda channels | `defaults` | `conda config --show channels` |
| envs_dirs | `C:\Users\Peregrine\miniconda3\envs` 等 | `conda config --show envs_dirs` |
| 系统 Python | 3.13.5（`C:\Users\Peregrine\AppData\Local\Programs\Python\Python313`） | `where.exe python` / `py -0p` |

现有 Conda 环境（**均未被本次审计修改**）：

| 环境名 | Python | PyTorch | CUDA | torch arch_list | GPU 可用 |
|---|---|---|---|---|---|
| `pytorch311` | 3.11.15 | 2.10.0+cu128 | 12.8 | sm_70…sm_90, sm_100, **sm_120** | ✅ 实测可用 |
| `smooth-rl-mujoco` | 3.12.14 | 2.14.0+cu130 | 13.0 | sm_75…sm_90, sm_100, **sm_120** | ✅ 实测可用 |
| `drone-navigation-webcam` | 3.12.13 | 无 torch | — | — | — |

**实测基线验证**（在 `pytorch311` 中执行，只读，未改动该环境）：

```
torch 2.10.0+cu128
device: NVIDIA GeForce RTX 5080 Laptop GPU
capability: (12, 0)
matmul OK, sum= 12958.2031
arch_list: ['sm_70','sm_75','sm_80','sm_86','sm_90','sm_100','sm_120']
```

即：**本机 GPU 本身完全正常**，现代 PyTorch 栈可以在此 GPU 上正常执行 CUDA 计算。问题不在硬件，在旧软件栈。

### 1.5 Docker

| 项目 | 实测值 | 来源命令 |
|---|---|---|
| `docker` 命令 | **不存在** | `where.exe docker` |
| Docker 服务 | **不存在**（`Get-Service '*docker*','com.docker*'` 无返回） | PowerShell |

结论：**Docker 当前不可用**。是否「需要」Docker 见 `COMPATIBILITY_MATRIX.md` 第七节。

### 1.6 WSL2 —— ⚠️ 当前不可用（严重）

| 项目 | 实测值 | 来源命令 |
|---|---|---|
| WSL 版本 | **2.5.7.0** | `wsl --version` |
| 内核版本 | 6.6.87.1-1 | `wsl --version` |
| WSLg 版本 | 1.0.66 | `wsl --version` |
| Direct3D 版本 | 1.611.1-81528511 | `wsl --version` |
| DXCore 版本 | 10.0.26100.1-240331-1435.ge-release | `wsl --version` |
| 发行版列表 | `Ubuntu`（默认，v2）、`Ubuntu-D`（v2） | `wsl -l -v` |
| 两个发行版状态 | 均为 `Stopped`，且**均无法启动** | `wsl -d Ubuntu -- bash -lc ...` |
| `.wslconfig` | 不存在 | `cat C:/Users/Peregrine/.wslconfig` |

**启动失败的实际错误**（两个发行版完全一致）：

```
无法打开 \\?\D:\VirtualMachines\WSL\Ubuntu\ext4.vhdx 进行读写: 系统找不到指定的文件。
错误代码: Wsl/Service/CreateInstance/MountDisk/HCS/ERROR_FILE_NOT_FOUND
```

`Ubuntu` 分支的等价错误指向 `C:\Users\Peregrine\AppData\Local\wsl\{b175259a-0979-4d32-a4b5-39f0440a5640}\ext4.vhdx`。

注册表中两个发行版的 `BasePath` 确实存在，但**实际目录里只有 `shortcut.ico`，没有 `ext4.vhdx`**：

```
C:\Users\Peregrine\AppData\Local\wsl\{b175259a-...}\  →  仅 shortcut.ico (37207 B)
D:\VirtualMachines\WSL\Ubuntu\                        →  仅 shortcut.ico (37207 B)
D:\VirtualMachines\WSL\Exports\                       →  空目录
```

> **判定：WSL2 Ubuntu 的虚拟磁盘已丢失或被删除/移动，两个发行版目前都无法启动。**
> 这意味着「在 WSL2 中搭建 Linux 环境」这条路**当前受阻于一个与 ThinkTwice 无关的、需要先修复的本地问题**。
> 修复方式（`wsl --unregister` 后重建，或从备份恢复 vhdx）涉及删除注册项，**须由你确认后执行**，本 Agent 未做任何改动。

### 1.7 磁盘空间与文件系统

| 卷 | 文件系统 | 总容量 | 可用 | 使用率 |
|---|---|---|---|---|
| C:（Windows） | NTFS | 381.0 GB | **74.9 GB** | 81 % |
| D: | NTFS | 640.8 GB | **210.2 GB** | 68 % |
| （无盘符卷） | NTFS | 1.24 TB | 77.1 GB | 94 % |

来源：`df -h`（Git Bash）与 `PowerShell Get-Volume`，两者一致。

仓库位于 `D:\Desktop\端到端自动驾驶开源模型调研\ThinkTwice`（D 盘，可用 210 GB）。

参考体量：官方数据集 189K 帧 = **8 TB**，2M 帧 = **85 TB**；CARLA 0.9.10.1 本体 + AdditionalMaps 约 **20 GB 量级**。当前空间**不足以存放完整训练集**，但足够存放 CARLA 本体与 checkpoint。

### 1.8 本地仓库状态

| 项目 | 实测值 |
|---|---|
| HEAD commit | `e9cf2fc078f6ab8175b1a4929faaa8be55f3aa97` |
| commit 信息 | `Update README.md`，2025-07-02 13:32:13 +0800 |
| 分支 | `main` |
| 工作区状态 | **干净**（`git status --short` 无输出） |
| 本地是否已有 checkpoint | **否**，`open_loop_training/ckpt/` 不存在（已被 `.gitignore` 忽略） |
| 本地是否已有数据集 | **否**，`dataset/` 下仅有 `tools/` |
| CARLA 是否已安装 | **否**，`/c/carla`、`/d/carla`、`/mnt/carla` 均不存在，`CARLA_ROOT` 未设置 |

### 1.9 网络可达性（用于后续下载）

| 目标 | HTTP 状态 |
|---|---|
| `pypi.org` | 200 |
| `download.pytorch.org/whl/cu113/` | 200 |
| `download.openmmlab.com` | 200 |
| `github.com` | 200 |
| `carla-releases.s3.eu-west-3.amazonaws.com`（CARLA 0.9.10.1） | 301（重定向，可达） |

外网通畅，下载不是瓶颈。

---

## 二、官方要求的环境（从仓库文档与代码提取）

来源：`README.md`、`docs/INSTALL.md`、`docs/EVAL.md`、`docs/TRAIN.md`、`docs/DATA_PREP.md`、`open_loop_training/setup.py`、`open_loop_training/configs/thinktwice.py`、`scenario_runner/requirements.txt`。

### 2.1 官方 `docs/INSTALL.md` 逐条版本要求

| 层 | 组件 | 官方指定版本 | 备注 |
|---|---|---|---|
| OS | Ubuntu（CARLA 官方支持 18.04 / 20.04） | 隐含 | CARLA 只有 Linux 构建 |
| Python | **3.7** | `conda create -n thinktwice python=3.7` | 注释明确「Must be py3.7 required by Carla 9.10」 |
| 深度学习框架 | **PyTorch 1.12.1 / torchvision 0.13.1 / torchaudio 0.12.1** | `cudatoolkit=11.3`，conda 安装 | |
| 编译器 | **gcc-6**（omgarcia channel）+ libgcc + libcxxabi | | 为了编译 CUDA 算子 |
| CUDA | **CUDA 11.3** | `CUDA_HOME` / `LD_LIBRARY_PATH` / `LD_PRELOAD` 手工导出 | 含 `libstdc++.so.6.0.29` |
| 基础库 | **mmcv-full == 1.7.0** | wheel 源 `cu113/torch1.12` | |
| 检测框架 | **mmdet == 2.28.2** | | |
| 分割框架 | **mmsegmentation == 0.30.0** | | |
| 3D 框架 | **mmdetection3d 分支 `1.0`** | 源码编译，注释「Note that 1.1 is incompatible」 | 分支 `1.0` 实际版本号 `1.0.0rc6` |
| 稀疏卷积 | `cumm-cu113`、`spconv-cu113` | | 注释「For fast lidar model」 |
| 编译标志 | `MMCV_WITH_OPS=1 FORCE_CUDA=1 pip install -v -e .` | | 「Must have a GPU」 |
| 仿真器 | **CARLA 0.9.10.1** | `CARLA_0.9.10.1.tar.gz` + `AdditionalMaps_0.9.10.1.tar.gz` | Python egg：`carla-0.9.10-py3.7-linux-x86_64.egg` |
| 其他 | `shapely==1.6.4.post2`（**强制**）、`gym==0.17.2`、`stable-baselines3==0.8.0`、`py_trees==0.8.1`、`opencv-python`、`h5py`、`hydra`、`omegaconf`、`mpi4py`、`matplotlib`、`numba` 等 | | |
| 自定义算子 | `open_loop_training/setup.py develop` | | 「Compile CUDA function for LSS from BEVDepth」 |

**关于 `shapely==1.6.4.post2`**：这不是可选的。上游 issue 中作者指出，更高版本的 shapely 会让 CARLA「神秘地崩溃」；该结论已作为 commit `78e7575`（*Solve CARLA Crash Issue*）写入 `docs/INSTALL.md`。复现时必须锁定。

### 2.2 论文原始环境 vs 官方仓库指定环境

| 维度 | 论文（CVPR 2023）描述 | 官方仓库实际指定 |
|---|---|---|
| 训练硬件 | **16 × A100，训练 4 天**（`docs/TRAIN.md` 原文） | 同左 |
| batch size | A100: 8/GPU（配置注释：3090→2，V100→3，A100→8） | 同左 |
| epoch | 60 | 同左 |
| lr | 1e-4（16 × A100）；少卡建议 3e-5 | 同左 |
| 单卡调试 | `CUDA_VISIBLE_DEVICES=0 python train.py ...` | 支持 |
| 推理/评测 | 未在论文中规定 | py3.7 + torch1.12.1 + cu113 + CARLA 0.9.10.1 |

论文没有给出比仓库更细的软件版本，因此 **「论文原始环境」≈「官方仓库指定环境」**。这一点对我们有利：不存在论文与仓库两套互相矛盾的依赖。

### 2.3 官方文档**遗漏**、但代码实际需要的依赖

这是审计中发现的一个实际缺口，复现时若照抄 `INSTALL.md` 会在 import 阶段失败：

| 缺失项 | 证据 | 后果 |
|---|---|---|
| **mmclassification (mmcls)** | `open_loop_training/code/encoder_decoder_framework.py:17` → `import mmcls.models` | `INSTALL.md` **未列出** mmcls。导入 `encoder_decoder_framework` 时即 `ModuleNotFoundError`。兼容版本为 **mmcls 0.25.0**（对应 mmcv 1.7.0 / py3.7） |
| **numba==0.53.0** | `mmdetection3d` 分支 `1.0` 的 `requirements/runtime.txt` | 由 mmdet3d 带入；numba 0.53 对 numpy 版本敏感 |
| **networkx>=2.2,<2.3** | 同上 | 与 `scenario_runner/requirements.txt` 的 `networkx==2.2` 一致 |
| **trimesh / lyft_dataset_sdk / nuscenes-devkit / plyfile / tensorboard** | 同上 | 由 mmdet3d 带入，部分对 CARLA 流程无用但会被安装 |
| **mmdet3d 分支 `1.0` 的真实版本** | `mmdet3d/version.py` on branch `1.0` → `__version__ = '1.0.0rc6'` | 文档写「1.0」，实际是 **1.0.0rc6**；锁定版本时应记 rc6 |
| 网络访问方式 | `INSTALL.md` h 节用 `wget` 拉 CARLA，i 节用 `git@github.com:`（SSH） | SSH 方式克隆需要配置 SSH key，否则失败 |

---

## 三、代码对 CUDA 扩展的真实依赖（决定兼容性边界）

ThinkTwice 有两个 CUDA 扩展依赖点，二者的性质完全不同：

### 3.1 `voxel_pooling`（仓库自带，可重新编译）

- 位置：`open_loop_training/ops/voxel_pooling/src/voxel_pooling_forward_cuda.cu`
- 内容：单个 `atomicAdd` 归约 kernel，**53 行**，只用了 `atomicAdd` 和一个 `__global__` kernel；没有用到任何架构特定指令（无 tensor core、无 WMMA、无 `__hfma`）。
- 调用点：`open_loop_training/code/model_code/backbones/lss.py:14, 632`
- 编译方式：`open_loop_training/setup.py`，使用 `torch.utils.cpp_extension.CUDAExtension`，`cmdclass=BuildExtension`。
- 编译标志包含 `-D__CUDA_NO_HALF_OPERATORS__ -D__CUDA_NO_HALF_CONVERSIONS__ -D__CUDA_NO_HALF2_OPERATORS__`。

**关键判断**：这个 kernel 源码本身**不含任何与架构绑定的东西**，理论上可以在新 CUDA Toolkit 下为 sm_120 重新编译。真正的障碍不在 kernel 源码，而在它注册进的 `torch.utils.cpp_extension` 需要与当前的 PyTorch/CUDA 版本匹配（见 `COMPATIBILITY_MATRIX.md` 第 2.4 节）。

### 3.2 `mmcv._ext` 的 multi-scale deformable attention（来自 mmcv，不可自行重编译）

- 调用点：`open_loop_training/code/model_code/dense_heads/multi_scale_deformable_attn_function.py:24-25`

```python
from mmcv.utils import ext_loader
ext_module = ext_loader.load_ext(
    '_ext', ['ms_deform_attn_backward', 'ms_deform_attn_forward'])
```

- 该文件定义了两个 autograd Function：`MultiScaleDeformableAttnFunction_fp16`（第 45 行起）和 `MultiScaleDeformableAttnFunction_fp32`（第 120 行起）。
- **两者 `forward` 的第一件事就是无条件调用 `ext_module.ms_deform_attn_forward(...)`**，**没有任何纯 PyTorch 回退分支**。

这一点非常重要，必须纠正一个常见误解：

> 该文件第 22 行确实 `from mmcv.ops.multi_scale_deform_attn import multi_scale_deformable_attn_pytorch`，但在整个文件中**该纯 PyTorch 实现从未被调用**（仅被导入）。因此 **无法通过「切到 CPU 版」来绕过 `mmcv_full` 的 CUDA 扩展**。作者自定义 `SpatialCrossAttention` 的目的正是为了走定制的 fp16/fp32 扩展路径。

同时注意 `mmcv.utils.ext_loader` 只在 **`mmcv-full`**（含算子的完整包）中存在；`mmcv` 2.x / `mmcv-lite` 不提供该扩展，会导致 `mmcv-full` 缺失报错。

### 3.3 稀疏卷积（spconv）

- `open_loop_training/code/model_code/backbones/lidarnet.py:12-19`
- `open_loop_training/configs/thinktwice.py` 中 `lidar_encoder` 配置存在（`pts_middle_encoder.type='SparseEncoder_fp32'`）。
- `open_loop_training/code/encoder_decoder_framework.py:56` → `self.lidar_encoder = builder.build_backbone(lidar_encoder)`，且第 244 行在 `forward` 中真实调用。

**结论：闭环评测**（`thinktwice_agent.py`）**也会构建并使用 lidar 分支**（agent 第 340–356 行把 lidar 点云塞进 `result["lidar"]`，第 420–423 行转成 `points`）**。因此 `spconv-cu113` 不是「只为训练服务」的可选项，它是评测路径上的硬依赖。

---

## 四、当前本地状态小结

| 项 | 状态 |
|---|---|
| 仓库 | ✅ 已克隆，commit `e9cf2fc`，工作区干净 |
| GPU 硬件 | ✅ RTX 5080 正常工作，16 GB 显存 |
| 现代 PyTorch 栈 | ✅ 已有两个可用环境（`pytorch311`, `smooth-rl-mujoco`），sm_120 实测可用 |
| 官方软件栈（py3.7 / torch1.12.1 / cu113） | ⚠️ 正在隔离环境 `tt-audit-py37` 中做实测，结果见 `SETUP_LOG.md` |
| WSL2 Ubuntu | ❌ **两个发行版均已损坏，ext4.vhdx 缺失，无法启动** |
| Docker | ❌ 未安装 |
| CUDA Toolkit | ❌ 未安装（仅有驱动） |
| CARLA | ❌ 未安装 |
| checkpoint | ❌ 未下载 |
| 数据集 | ❌ 未下载（官方数据集 8 TB，本机不具备存储条件） |

**当前阶段：阶段一（环境审计）基本完成，阶段二（配置环境）仅进行了隔离环境下的兼容性实测，未搭建完整运行栈。** 未修改官方仓库任何受版本控制的源码或配置。

---

## 五、审计所用命令清单（可复现）

```bash
# 系统与 GPU
cmd.exe /c ver
nvidia-smi
powershell.exe -NoProfile -Command "Get-CimInstance Win32_VideoController | Select Name,DriverVersion"
powershell.exe -NoProfile -Command "Get-CimInstance Win32_OperatingSystem | Select Caption,Version,BuildNumber"
powershell.exe -NoProfile -Command "Get-Volume | Select DriveLetter,FileSystem,SizeRemaining,Size"

# WSL
wsl.exe -l -v
wsl.exe --version
wsl.exe -d Ubuntu -- bash -lc 'uname -r'
powershell.exe -NoProfile -Command "Get-ChildItem 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss'"

# Python / Conda
"C:/Users/Peregrine/miniconda3/Scripts/conda.exe" --version
"C:/Users/Peregrine/miniconda3/Scripts/conda.exe" config --show envs_dirs

# 仓库
git rev-parse HEAD && git status --short

# 网络
curl -sS -o /dev/null -w "%{http_code}" https://download.pytorch.org/whl/cu113/
```

## 2026-10-09 19:10 CARLA实际运行验收通过

证据：evidence/20261009-carla-release/run10-ue4-compat/{run.json,sync-probe.json,server-console.log}。run/pass=true，probe/pass=true；原egg文件名carla-0.9.10-py3.7-linux-x86_64.egg。客户端/服务端版本均784d9b9f；Town05加载，synchronous_mode=true、fixed_delta_seconds=0.05，连续10tick frame9→18且snapshot frame一致，仿真步长0.05000000074505806秒；末两tick wall约0.16秒。恢复原world设置后主动终止本次进程组；returncode=-15/控制台143属于本次清理，非运行验收失败。无传感器或模型推理结论。

部署局部修复：专用WSL用户ttenv；Mesa24.0.5+/opt/thinktwice/mesa24独立前缀，实际RTX5080加速OpenGL4.6，GLX4.3/4.6上下文通过，详glx-context-mesa24-swrast.json及glxinfo-mesa24.txt。WSLg需swrast DRI入口，实际GALLIUM_DRIVER=d3d12；不代表软件渲染。原系统Mesa21.2.6保留。

原始失败run01/02返回1；独立Mesa但DISPLAY空run03返回139；DISPLAY=:0后RPC可连接，但run06 Town05渲染shader链接失败，随后get_settings超时。通过单独源码gl_link_diagnostic.c诊断（run09）获取精确原错误：vertex shader output out_TEXCOORD0 specifies noperspective interpolation qualifier, but fragment shader input specifies no interpolation qualifier。Mesa24原版00-mesa-defaults.conf已为UE4Editor等应用配置allow_glsl_cross_stage_interpolation_mismatch=true；仅对CARLA进程设此同一选项后run10通过。未改shader源码、默认渲染质量、模型数学/结构/5轮refinement或控制。正式run10无LD_PRELOAD诊断插桩。

原ImportAssets.sh实际导入完成：import-official/official-import.json pass=true，原脚本tar --keep-newer-files，检查无需恢复较新本体资产（0项），Import中压缩包保留。额外libpng16-16/libjpeg-turbo8/libtiff5根据原egg的ldd缺项补齐，原egg已注册专用conda carla.pth，未改名。

重复执行CARLA验收：wsl -d ThinkTwice-Focal -u ttenv，工作目录项目根，使用run10/run.json中的环境变量运行scripts/run_carla_acceptance.py --display :0 --output-dir <新证据目录>。启动包装脚本scripts/launch_carla_wsl.sh仅设置CARLA自身图形环境，不向推理Python全局注入Mesa。原evaluator硬编码DISPLAY空，后续单路线启动需独立部署overlay并记录diff，原agent/控制不改。

当前三项状态：资产获取/解压/导入完成；CARLA运行通过；ThinkTwice闭环未通过。旧torch源码候选wheel仍编译中，MMCV1.7.0候选wheel已含PTX；不能把wheel构建或CPUimport计为CUDA算子通过。

## 2026-10-09 19:33 模型CPU严格匹配、运行导入与候选身份

- model-checkpoint02.json：pass=true，官方配置refine_num=5；CPU模型state_dict与官方checkpoint均1344键，missing=[]、unexpected=[]、shape_mismatches={}，strict加载成功，参数128232121。仅CPU构造/键shape，不代表GPU模型或真实传感器通过。初始化ResNet的fc.weight/fc.bias警告属于去掉分类头的backbone初始化；最终ThinkTwice完整strict加载无缺项。
- 官方ResNet50初始化权重 https://download.pytorch.org/models/resnet50-0676ba61.pth，HTTP200，102530333B，本地SHA256=0676ba61b6795bbe1773cffd859882e5e297624d384b6993f7c9e683e722fb8a；核对官方文件名hash前缀。完整hash用于本地身份，不冒充另行发布的官方完整校验值。项目.thinktwice-runtime/assets/和/opt/thinktwice/torch-cache/hub/checkpoints双份保留；后续设TORCH_HOME=/opt/thinktwice/torch-cache。下载前D盘约151GiB，19:32剩余161925279744B。
- leaderboard-import02/03/04/05失败保留：缺ephem、BENCHMARK环境、诊断sys.path顺序、部署副本future import位置；分别按原requirements/原启动脚本补齐或修正。leaderboard-import06.json：原evaluator、原agent、独立观察subclass全部导入成功，Python3.7部署副本语法通过。py-trees0.8.3、xmlschema1.0.18沿用原requirements；另安装pygame2.1.2、dictor0.1.12、tabulate0.9.0、ephem4.1.5，仅专用环境。安装命令和结果见leaderboard-runtime-install01/02.log。
- 已安装SDK的元数据包含black/flake8/pytest/jupyter等开发依赖；当前pip check不能说完整通过，实际清单见pip-check-1933.txt。导入门槛已通过，但不代表所有声明的训练/开发依赖已安装。
- candidate-identities.json与mmcv-candidate-cuobjdump-list-ptx.txt固定候选身份。MMCV1.7.0 wheel29933890B SHA256=66b3dbbface3bb6297a9d43e97241996c93d9b9e0a57a4e9528b320bf42fba06；_ext.so90428760B SHA256=44f637337f33faa10d37802644e4245463d8d1ebcf41ef1ad1e3a627404b69ca，cuobjdump --list-ptx返回0。仅证明含PTX，不等于算子通过。mmdet3d1.0.0rc6为纯Pythonwheel837901B，SHA256=672c37537c60ec39441ebf4e0da2e84c0fc9023a192510d2a3abd86e9d0f9f5d，不能称为重编CUDA扩展。
- PyTorch build04在19:32推进至5481/5887，已进入CUDA源码，无新增编译错误；保持MAX_JOBS=2，原torch/cuDNN保留，未安装候选torch。候选就绪后才跑基础有限值/NumPy往返/同步冷热计时与算子测试。
- 单路线部署副本现为.thinktwice-runtime/launch/20261009-smoke-v2；旧副本和语法错误保留。原route16 Town05不缩短。evaluator-deployment.diff仅进程图形环境和自有进程清理。scripts/thinktwice_observed_agent.py观察原传感器batch/6级有限值/原返回控制，保存首批真实batch与prediction，不改计算和控制值；尚未运行。模型/agent/配置/控制tracked源码git diff为空。

状态：资产完成；CARLA运行通过；CPU模型/权重匹配通过；GPU基础、完整关键算子、真实batch与单路线闭环仍待验收。

### 2026-10-09 19:40 独立旧cuBLAS/cuDNN实际执行通过

probe_blas_cudnn.py用CPU确定值构造输入/权重后拷贝GPU，隔离已知失败的CUDA randn，不改算子数学。base-blas-cudnn01.json：torch1.12.1+cu113、cuDNN8302；32x32 matmul与NumPy参考匹配，首次1.476244296s，十次稳态0.000029399–0.000134528s；1x4x16x16、4→4、3x3卷积与CPU原层参考匹配，首次323.661228499s，十次稳态0.00003429–0.000703617s，均有限值。同步计时，不包含CPU参考比较。首次是现有驱动缓存状态下的进程首次调用，不声称清空缓存后的绝对冷启动。首次卷积期间进程持续CPU工作，ComputeCache由640MiB增长至约1.1GiB，最终成功，不应把这5分钟等待写成“必然失败”或稳态性能。此结果只覆盖两个测试尺寸，不代替aten随机数、deform/完整SparseEncoder/真实模型验收。后续base-blas-cudnn02-cache-retained验证新进程缓存复用。

完整LiDAR栈诊断probe_lidar_stack.py和门槛保护的run_single_route_smoke.py已通过实际Python3.7语法检查，未执行。单路线须非root ttenv、基础/三类算子/完整LiDAR JSON全部通过、候选torch1.12.1路径正确才运行。agent-observation.diff与evaluator-deployment.diff单独保存到launch/20261009-smoke-v2。

## 2026-10-09 20:02 旧Torch候选成品取得，配置意图与实际ABI区分

build06-profiler-header.log构建wheel成功，exit0。/opt/thinktwice/src/pytorch-1.12.1/dist/torch-1.12.1-cp37-cp37m-linux_x86_64.whl，本地SHA256=af7c29d1098016808c9f1affee84843a6028123027cea6a1163cdb78fdf8fa0a；pip install --no-deps --target /opt/thinktwice/candidate-site，原base torch不动，torch-candidate-install01.log。

torch-candidate-identity01.json pass=true：版本1.12.1、CUDA11.3、cuDNN8302，实际torch._C._GLIBCXX_USE_CXX11_ABI=true，即ABI=1。必须修正此前“配置ABI0即成品ABI0”的推断：v1.12.1官方CMakeLists.txt第43–51行对GLIBCXX_USE_CXX11_ABI=0只追加-fabi-version=11，没有-D_GLIBCXX_USE_CXX11_ABI=0，本地GCC9的实际宏仍1。不把CMakeCache意图当实际二进制身份；候选所有Torch扩展统一用实际ABI1重建，原ABI0 wheel/旧扩展保留。框架版本/数学/网络/控制不变。

/proc/self/maps核验七个libtorch/libc10核心库全部从candidate-site/torch/lib加载，无旧核心混载；cuBLAS实际正确Toolkit11.5.1.109、cudart11.3.109、cusparse11.6.0.109。与此前base torch测试可能选用的捆绑库不是同一二进制，必须单独数值验收。linux-basics-candidate01正在以ttenv执行：CPU↔Tensor↔NumPy已通过，warnings=[]，GPU初始化仍在进行，不计GPU通过。

必要扩展已启动：voxel-relink01（exec4618）、mmcv-relink01（候选实际Torch头/ABI/单库、2并发）。待voxel结束后再启动vision，避免超过资源并发。已有wheel与/opt/thinktwice/build保留；新voxel输出/opt/thinktwice/voxel-candidate。候选完整GPU/模型/真batch/闭环尚未通过。

## 2026-10-09 20:12 候选基础CUDA实际通过

linux-basics-candidate01.json三阶段全部pass=true，非root ttenv、候选torch1.12.1、NumPy1.20.3。CPU Tensor↔NumPy0.855904929s、warnings=[]；GPU Tensor↔NumPy精确数值往返通过，首进程GPU初始化计入该阶段554.855849706s。驱动缓存沿用已有内容，不能称清缓存绝对冷态；初始化期间与扩展编译并行，冷启动墙钟含本机资源状态。仍捕获旧torch架构识别警告“sm_120 not compatible … sm_86 compute_86”，但实际PTX路径执行成功，不据警告覆盖测试结果。

有限值/同步计时通过：randn首次2.101862ms，512x512 matmul首次1202.227721ms、10次稳态0.100963–0.751905ms；1x64x64x64、64→64、3x3卷积首次2203.755052ms、10次稳态0.127824–0.43465ms。该段共3.430994147s，NumPy初始化警告无。只代表这些基础操作，仍非模型通过。

三个扩展成品：vision重建wheel SHA256=b9fa66b863328aa9d1cff20d82e0cbff79e2afeb80b726d24781e02ec367bbfd；MMCV重建wheel SHA256=da7d28c618c4c5824f4f4966291dbe1f75969e34513b080c803bfffb86f2a93a。MMCV128项编译/打包已完成，但build包装脚本运行期间被本代理修改，随后shell收尾unexpected EOF while looking for matching quote；原错误保留mmcv-relink01.log，当前bash -n通过，成品zip.testzip全CRC通过。旧候选mmcv及dist-info移至/opt/thinktwice/candidate-backups/mmcv-abi0-split保留，新wheel无依赖安装通过。不是算法/算子运行失败。

relinked-extension-identities.json及三个正式cuobjdump文件记录新voxel/MMCV/vision各自hash/PTX/DT_NEEDED，均无libtorch_cuda_cu/cpp依赖。extensions-candidate-identity01.json实际导入通过且所有libtorch/libc10均候选路径，无旧核心混载。仍只是import/身份验收。已按deform→spconv→voxel顺序逐进程运行candidate-operator-gates01.log，真实结果待各JSON返回。

## 2026-10-09 20:17 四类局部CUDA算子实际通过

候选同一Torch/ABI1、实际重链接扩展：candidate-deform-01.json pass=true，MMCV MultiScaleDeformableAttnFunction原包装与CPU参考一致，shape[1,3,8]有限；candidate-spconv-01.json pass=true，spconv2.3.6最小SubMConv3d(k1)与确定值参考一致，shape[3,4]；candidate-voxel-01.json pass=true，原voxel_pooling完整Python包装（含原GPU aten初始化）与求和参考一致，shape[1,2,2,2]，不再仅raw内核；candidate-dcn-01.json pass=true，原MMCV DeformConv2dPack groups4零offset与CPU标准分组卷积一致，shape[1,8,12,12]。

各探针总墙钟deform20.719696s、spconv98.751484s、voxel3.550637s、DCN9.628254s，含进程首次加载/import/数值对照；不是每次算子稳态延迟。分别记录真实Torch/扩展路径，spconv不与MMCV文件身份合并判断。此处只覆盖局部算子，不等于完整SparseEncoder或原模型。完整官方LiDAR配置+strict子权重的synthetic forward已启动candidate-lidar-stack01，含原voxelization/SparseEncoder/SECOND/FPN，两次调用分别计时/shape/finite。尚不计完整LiDAR通过。

## 2026-10-09 20:26 完整LiDAR、GPU模型通过；单路线已启动

candidate-lidar-stack01失败发生在诊断子权重加载，并非CUDA：本代理用普通dict提取子权重丢失_metadata，触发mmdet3d原spconv加载钩子的旧格式permute。lidar-checkpoint-metadata.json确认原state_dict为OrderedDict、1026条metadata，conv_input.0原version2、原权重[16,3,3,3,5]。修复仅诊断脚本：OrderedDict子权重原样保留127条对应metadata，权重值/轴不动。原MMCV正式load_checkpoint在checkpoint.py650–656行保留metadata，原agent不需修复。

candidate-lidar-stack02-metadata.json通过：210个LiDAR子权重strict加载；官方完整voxelization/SparseEncoder/SECOND/FPN对synthetic[1,12000,5]两次实际前向，输出[1,512,84,84]均有限，首次4.424193895s、第二次0.045304717s。不是实际传感器输入，不外推全模型性能。

candidate-model-gpu01.json通过：最终候选torch1.12.1 ABI1构造官方完整模型，全部1344键shape完全一致，strict加载成功，128232121参数均cuda:0、refine_num5；未做forward。leaderboard-import-candidate01原评测器/原agent/观察subclass导入和overlay Python3.7语法通过。系统无ss（原错误保留工具记录），改用ttenv对22023/22033瞬时独占TCP bind后释放，两端口空闲。D盘启动前153263751168B（142.7GiB）剩余。官方源码tracked diff为空。

run_single_route_smoke.py实际门槛包括basics/deform/DCN/spconv/voxel/完整LiDAR/二进制identity/GPUmodel全部pass，torch路径必须候选，模型refine5及全部参数cuda:0；使用ttenv、专用缓存、独立Mesa CARLA启动包装。只执行原routes_town05_long.xml的route16（单条、原样、不缩短），traffic场景沿用all_towns_traffic_scenarios_no256.json，默认seed/控制/20Hz不变。部署diff和观察addition diff在launch/20261009-smoke-v2；原agent/模型/配置不动。

单路线20:26启动到.thinktwice-runtime/runs/20261009-smoke01，console.log/results.json/run.json及sensor-inference/agent-events.jsonl保留；首个真实batch和prediction各保存一次，原agent默认SAVE_PATH图像/metadata也保留。supervisor日志evidence/20261009-takeover/smoke01-supervisor.log。此刻未取得真实batch/路线通过结论，不能称环境完成。

## 2026-10-09 20:33 单路线01失败、CARLA原生崩溃诊断

.thinktwice-runtime/runs/20261009-smoke01/保留console.log/results.json/run.json/termination.json及sensor-inference/agent-events.jsonl。原agent setup已完成官方GPU权重加载、refine5与原传感器配置；仅setup事件，无真实sensor batch/inference/control，inference_calls0、sensor_gatefalse、route_records/progress空。CARLA在Town05同步加载后的原场景初始化阶段Signal11/Segmentation fault，随后Scenario7 setup RPC10000ms超时。不能说模型推理失败（尚未运行），也不能把先前API/Town05/10tick通过外推有车辆/场景/传感器均通过。

核对本次Popen server PID85已Z、shippingPID93已退出后，仅SIGTERM仍等待原6000s RPC的自有evaluator PID37；supervisor记录returncode-15、passfalse。原native错误/自己的计划终止因果分开，termination.json说明。旧WSL/其他进程不操作。

必要原生诊断：专用WSL apt-get install --no-install-recommends gdb9.2（日志carla-gdb-install.log）；launch_carla_wsl_gdb.sh保持与正式图形环境相同，仅gdb --batch运行同一shipping binary/CarlaUE4参数，SIGSEGV时thread apply all bt12和info sharedlibrary。不改CARLA源码/资源/质量/场景、模型或控制。单路线02到.thinktwice-runtime/runs/20261009-smoke02-gdb已启动，supervisor日志smoke02-supervisor.log。

部署监督器新增：只确认本evaluator直接子进程的server PID，检测其退出/Z后给予10秒正常清理宽限；仍等待时结束自有evaluator并保存server_abort，避免100分钟无意义RPC等待。仅失败后清理策略，无正常控制/模型/仿真步长改动。当前准确状态：资产完成；基础CARLA/API/Town05/同步通过；真实route场景初始化失败；模型CUDA和完整LiDAR/关键算子通过；真实batch与闭环未通过。

## 2026-10-09 20:52：CARLA native crash 已精确归属图形编译线程

smoke04-gdb-tick120 顺利通过RPC/官方agent加载/Town05/Seed2023/IS_EVAL，但场景设置时 Thread38 CarlaUE4:gdrv0 SIGSEGV。原生PC在 /opt/thinktwice/mesa24/lib/dri/swrast_dri.so 的 nir_lower_wpos_ytransform.cold，偏移0x58e02；objdump指令 mov 0x20,%eax，随后ud2，证明空地址读取。非 CUDA模型推理栈；尚无sensor inference。全部72线程堆栈保存于该run console.log，run.json pass=false、inference_calls0。不能因为文件入口叫swrast_dri.so就称软件渲染，此DRI实际选择D3D12 NVIDIA后端，见既有renderer证据。

先构建相同Mesa24.0.5单文件诊断：build_mesa_nir_diagnostic.py 从原ninja取得精确编译命令，仅 nir_lower_wpos_ytransform.c 增加-g/-O1/-fno-omit-frame-pointer，重新链接并复制 /opt/thinktwice/mesa24-nir-debug/lib/dri/swrast_dri.so。安装的mesa24发布版完全保留，无源码diff。build01因PATH缺ninja失败并保留，build02加conda/bin后成功。文件身份与完整命令记录manifest及mesa-nir-diagnostic-build02.log。

smoke05-nir-debug 使用独立诊断DRI路径/同一原路线启动，目的是确认NULL读的源码位置再局部修复，不盲目升级框架。可重复启动入口新增 scripts/run_candidate_smoke.ps1 -RunName <全新名称> -Launcher <启动器>，所有旧run保留，原模型与控制未修改。

## 2026-10-09 21:07：真实传感器已接通，首个 batch 正在完整推理

smoke10-triangle-index-fix 已越过所有此前native crash位置，完成 Town05、同步/seed2023、原Town05Long单route16场景和amount=120背景交通，进入Running the route。原agent真实sensor输入事件已记录；默认历史积累step0–30的原控制返回均finite/range valid，未改预热时长。first-real-batch.pt 已保存39796762B，当前原 forward_inference 首次执行尚未返回。不能提前计六级输出或闭环通过。

图形驱动v2已支持原场景运行到传感器和模型入口，后续仍须持续验证，不能由此称完整CARLA路线已通过。所有精确日志/事件保存在 .thinktwice-runtime/runs/20261009-smoke10-triangle-index-fix。

## 2026-10-09 21:11：真实 batch 全模型重放通过；实时闭环 smoke11

smoke10 在step31原forward中已通过图像/LiDAR并到decoder transform_fpn_feats，但 spatial_shapes.prod(1) 触发 nvrtc: invalid value for --gpu-architecture。旧 torch1.12.1 jit_utils.cpp 的 codegenOutputQuery 仅识别NVRTC11.0，11.3走未知版本分支，错误按真实SM120请求SASS。原始完整堆栈及JIT代码保存在smoke10 console.log/agent-events.jsonl；不是已成功完整推理。

局部框架部署修复：仅为NVRTC11.1–11.3指定最高8.6；原代码已有dev超过max时compile_to_sass=false，因此自然使用compute86 PTX。未改模型表达式或operator公式。build_torch_nvrtc_arch_fix.py 仅增量jit_utils.cpp.o+libtorch_cuda.so，原lib备份candidate-backups/torch-before-nvrtc-arch-fix，原源码.cpp.before-nvrtc-arch-fix。新库310286504B，SHA ce89a629b94ee4847849f180de2ce4b5e6fe56b20c4be360bede046617191c0b。源码diff/manifest/buildlog均保存在本目录evidence。

real-batch-replay01.json 实际通过：prod整数结果[6,20]；原官方1344键strict、五轮、保存的真实sensor batch SHA988f428ea008216ea8ef5156503d5200866491c75c5af3076249fea9ae57a4b1；两次完整forward的五组主要输出均六级finite，pred_wp[1,6,4,2]；同步耗时首次4.83s、第二次0.34s（既有缓存，不称空缓存冷态）。离线真实batch重放不能替代实时控制闭环。

runner新增--replay必需门禁，要求重放pass/refine5且hash匹配当前libtorch_cuda，旧8项gate作为基线保留。smoke11-real-loop已启动原route16实时闭环，服务器图形v2候选，路线/默认控制/背景交通120不变。尚须最终结果验收。


## 2026-10-09T21:51:07 最终交付验收

用户最终选择的≥200次短闭环已通过：203次连续实时完整推理、234次合法控制、六级全部finite、移动27.304m、路线2.339751%，原评测器return0、无server_abort。最终smoke13-cleanup-final/smoke-acceptance.json pass=true；原整路线run/results状态未完成保留。详见FINAL_ENVIRONMENT_REPORT.md与final-delivery-summary.json。资产完成、CARLA/推理通过、短smoke通过分别记录；未训练、未完整Town05 Long。交接统筹，不再扩大运行。
