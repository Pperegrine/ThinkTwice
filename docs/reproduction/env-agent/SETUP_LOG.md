> **2026-10-09 接手更正：本文件下方为上一轮历史审计/原始日志。当前授权、状态和纠正以 [TAKEOVER_STATUS.md](TAKEOVER_STATUS.md)、[COMPATIBILITY_MATRIX.md](COMPATIBILITY_MATRIX.md)、[KNOWN_ISSUES.md](KNOWN_ISSUES.md) 为准。旧文中“仅审计等待决策”“MMCV/spconv必然失败”“全模型数十小时”“必须注销WSL”等结论不再有效；原错误输出保留，不作为当前通过声明。**

# 环境搭建与测试记录（SETUP_LOG）

- 记录时间：2026-10-09
- 环境负责人：环境与依赖兼容性 Agent
- 原则：**本文件只记录实际执行过的命令与真实输出。未执行的测试一律标记为「未执行」。**

> ⚠️ 阅读提示：本文件中有**一次失败的操作被误判为成功**（S-03），已在记录中如实标注并说明原因。

---

## 一、阶段划分

| 阶段 | 内容 | 状态 |
|---|---|---|
| 阶段一 | 环境审计（只读检查 + 文档/代码分析） | ✅ 完成 |
| 阶段二 | 隔离环境下的兼容性实测 | ✅ 完成（结论为**否定**） |
| 阶段三 | 搭建完整 ThinkTwice 运行栈 | ⛔ **未执行，按约定停止** |

**停止依据**：任务书规定「如果存在严重版本冲突或必须修改模型代码才能继续，请停止扩大修改，提交问题和备选方案，由我决定」。本次实测确认了**严重版本冲突**（见 T-03），因此未继续搭建 OpenMMLab 栈，未下载 CARLA 与 checkpoint，未做任何训练。

---

## 二、审计类命令（只读，未改动系统）

| 编号 | 命令 | 结果摘要 |
|---|---|---|
| S-01 | `wsl.exe -l -v` | `Ubuntu`(Stopped, v2)、`Ubuntu-D`(Stopped, v2) |
| S-02 | `wsl.exe -d Ubuntu -- bash -lc '...'` | ❌ 启动失败：`Wsl/Service/CreateInstance/MountDisk/HCS/ERROR_FILE_NOT_FOUND` |
| S-03 | `wsl.exe --version` | WSL 2.5.7.0 / 内核 6.6.87.1-1 / WSLg 1.0.66 / Direct3D 1.611.1 |
| S-04 | `nvidia-smi` | RTX 5080 Laptop，16303 MiB，驱动 595.79，CUDA 13.2 |
| S-05 | `nvcc --version` | ❌ `command not found` |
| S-06 | `ls "C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/"` | ❌ 目录不存在 |
| S-07 | `conda --version` | conda 26.1.1 |
| S-08 | `conda config --show envs_dirs` | 3 个 envs_dirs（默认 `miniconda3\envs`） |
| S-09 | `where.exe docker` | ❌ 未安装 |
| S-10 | `Get-Service '*docker*'` | ❌ 无返回（无 Docker 服务） |
| S-11 | `df -h` / `Get-Volume` | C: 74.9 GB 可用 / D: 210.2 GB 可用 |
| S-12 | `git rev-parse HEAD` | `e9cf2fc078f6ab8175b1a4929faaa8be55f3aa97` |
| S-13 | `git status --short` | 空（工作区干净） |
| S-14 | `curl` 各镜像站 | pypi/pytorch/openmmlab/github 均 200 |

### S-02 的完整错误输出

```
无法打开 \\?\D:\VirtualMachines\WSL\Ubuntu\ext4.vhdx 进行读写: 系统找不到指定的文件。
错误代码: Wsl/Service/CreateInstance/MountDisk/HCS/ERROR_FILE_NOT_FOUND
```

（`Ubuntu` 发行版报同样错误，路径为 `C:\Users\Peregrine\AppData\Local\wsl\{b175259a-0979-4d32-a4b5-39f0440a5640}\ext4.vhdx`）

**目录实测内容**：两个 `BasePath` 下**只有 `shortcut.ico`（37,207 字节），没有 `ext4.vhdx`**。

**处置**：未做任何修复（`wsl --unregister` 会删除注册项，属于不可逆操作，须由你确认）。

---

## 三、基线验证（在**未改动**的现有环境中执行）

### T-01 `pytorch311` 环境 —— 现代栈在 RTX 5080 上可用

环境：`C:\Users\Peregrine\miniconda3\envs\pytorch311`（**只读调用，未修改该环境**）

```
torch 2.10.0+cu128
device: NVIDIA GeForce RTX 5080 Laptop GPU
capability: (12, 0)
matmul OK, sum= 12958.2031
arch_list: ['sm_70','sm_75','sm_80','sm_86','sm_90','sm_100','sm_120']
```

**结论**：✅ **通过**。GPU 硬件本身完全正常，sm_120 在现代 PyTorch 下可执行 CUDA 运算。**问题不在硬件。**

### T-02 `smooth-rl-mujoco` 环境（仅读取版本信息）

```
Python 3.12.14 / torch 2.14.0+cu130 / arch_list 含 sm_120
```

**结论**：✅ 通过（仅版本查询，未执行运算）。

---

## 四、隔离环境搭建（阶段二）

### S-15 创建隔离 Conda 环境

```bash
conda create -n tt-audit-py37 python=3.7 -y
```

结果：✅ 成功，`Python 3.7.16`。

**隔离性声明**：新环境名为 `tt-audit-py37`，与现有 `pytorch311`、`smooth-rl-mujoco`、`drone-navigation-webcam` 完全独立；**未修改、未卸载、未覆盖任何已有环境**；未触碰系统 PATH 与全局 CUDA 设置。

### S-16 修复 Python 3.7 环境的 SSL 支持

**第一次执行**（记录为 **S-16a，失败**）：

```bash
python -m pip install torch==1.12.1+cu113 torchvision==0.13.1+cu113 \
    --index-url https://download.pytorch.org/whl/cu113
```

实际输出：

```
WARNING: pip is configured with locations that require TLS/SSL, however
         the ssl module in Python is not available.
ERROR: Could not find a version that satisfies the requirement torch==1.12.1+cu113
ERROR: No matching distribution found for torch==1.12.1+cu113
```

（`import ssl` 报 `ImportError: DLL load failed: 找不到指定的模块。`）

> ⚠️ **记录纠错**：该命令通过管道接 `tail` 执行，**shell 报告 `exit code 0` 来自 `tail` 而非 `pip`**，最初被误判为「安装成功」。
> 后续验证 `import torch` 报 `ModuleNotFoundError` 才发现实际失败。
> 教训已记录：**判断安装结果必须验证 `import`，不能只看退出码。**

**修复**：

```bash
conda install -n tt-audit-py37 -c defaults openssl ca-certificates -y
```

结果：✅ `ssl OK: OpenSSL 1.1.0i`。副作用：conda 将 Python 解析为 **3.7.1**。

### S-17 安装 PyTorch 1.12.1+cu113

**第二次执行（S-17a，失败）**：改用 pip 直连 → 触发系统代理错误：

```
ProxyError('Cannot connect to proxy.', OSError(0, 'Error'))
ERROR: No matching distribution found for torch==1.12.1+cu113
```

原因：pip（urllib）读取了 Windows 系统代理设置，而该代理不可用；`curl` 不走该代理，因此 `curl` 正常。

**第三次执行（S-17b，成功）**：改用 `curl` 下载 wheel，再用 pip 离线安装：

```bash
# 解析真实 URL 后下载（Content-Length 校验：2,143,450,326 字节）
curl -L -C - -o /d/wheels/torch-1.12.1+cu113-cp37-cp37m-win_amd64.whl \
  "https://download.pytorch.org/whl/cu113/torch-1.12.1%2Bcu113-cp37-cp37m-win_amd64.whl"

pip install --no-deps --no-index /d/wheels/torch-1.12.1+cu113-cp37-cp37m-win_amd64.whl
```

结果：✅ `Successfully installed torch-1.12.1+cu113`
（补充：`conda install -n tt-audit-py37 typing_extensions -y` 以补齐依赖）

---

## 五、关键测试：T-03 —— 官方 PyTorch 栈在 RTX 5080 上的实际表现

**这是本次审计最核心的一条实测证据。**

测试脚本 `D:\wheels\tt_test.py`，环境 `tt-audit-py37`，`python -u`（无缓冲），`timeout 180`。

### 实际输出（原文照录）

```
torch: 1.12.1+cu113
built with CUDA: 11.3
compiled arch_list: ['sm_37', 'sm_50', 'sm_60', 'sm_61', 'sm_70', 'sm_75', 'sm_80', 'sm_86', 'compute_37']
STEP1: calling is_available()
is_available(): True
device_count(): 1
UserWarning:
NVIDIA GeForce RTX 5080 Laptop GPU with CUDA capability sm_120 is not compatible
with the current PyTorch installation.
The current PyTorch install supports CUDA capabilities sm_37 sm_50 sm_60 sm_61
sm_70 sm_75 sm_80 sm_86 compute_37.
If you want to use the NVIDIA GeForce RTX 5080 Laptop GPU GPU with PyTorch,
please check the instructions at https://pytorch.org/get-started/locally/
device_name: NVIDIA GeForce RTX 5080 Laptop GPU
capability: (12, 0)
STEP2: launching a CUDA kernel (256x256 matmul)
EXITCODE=124 (124 = timed out)
```

### 结果解读

| 观察 | 结论 |
|---|---|
| `torch 1.12.1+cu113` 可正常 import | 安装本身没问题 |
| `compiled arch_list` 最高只到 **sm_86** | **确认二进制无 sm_120 的 SASS 机器码**（与文档推断一致） |
| 但 arch_list **末尾含 `compute_37`** | ⚠️ **这是关键** —— 存在 PTX，驱动可做 JIT，见 §5.1 |
| PyTorch **自己主动发出警告**，明确写出 `sm_120 is not compatible` | 上游已预期此场景 |
| ⚠️ `is_available()` 返回 **`True`** | **这是陷阱**：不能用 `is_available()` 判断可用性 |
| `device_count() == 1`、`capability == (12, 0)`、设备名可读 | 设备**枚举**正常，说明驱动层没问题 |
| 第一次 kernel 在 **180 秒内**未返回 | 超时（**不是**最终的失败结论，见 §5.1） |

> ⚠️ **记录纠错（第二次）**：最初根据 180 秒超时，我判断为「进程挂死、CUDA 运算失败」。
> **这个结论是错误的。** 放宽到 900 秒后，kernel **实际执行成功了**，只是耗时极长。
> 完整更正见 §5.1。此处保留原始观察，以完整呈现排障过程。

### 5.1 T-03b 结果（900 秒探测）—— **结论更正**

脚本 `D:\wheels\tt_test2.py`，`timeout 900`。**完整输出（原文照录）**：

```
[    0.0s] start
[    0.0s] STEP A: torch.randn(256,256, device="cuda")
  UserWarning: NVIDIA GeForce RTX 5080 Laptop GPU with CUDA capability sm_120
  is not compatible with the current PyTorch installation. ...
  UserWarning: Failed to initialize NumPy ...
[  302.3s]   randn returned (async, no sync yet)
[  302.3s] STEP B: torch.cuda.synchronize() after randn
[  302.3s]   sync OK -> randn kernel actually executed
[  302.3s] STEP C: matmul a @ b
[  479.7s]   matmul issued (async)
[  479.7s]   sync OK -> matmul kernel executed, sum = -4901.5166
[  479.7s] DONE
EXITCODE=0 (124 = timed out at 900s)
```

**结论更正为：kernel 能够执行成功，但慢到不可用。**

| 操作 | 耗时 |
|---|---|
| 第一次 `torch.randn(256,256, device='cuda')` + `synchronize()` | **302.3 s** |
| 第一次 `a @ b`（256×256 矩阵乘）+ `synchronize()` | **177.4 s** |
| 完成同样的运算所需的时间（现代栈 `pytorch311`，同样 256×256） | **< 0.01 s** |

即：**同样的运算慢了约 4~5 个数量级（约 10⁴~10⁵ 倍）**。

**机制解释**

`compiled arch_list` 的末尾是 **`compute_37`**，说明该二进制虽然不含 sm_120 的 SASS，但**内嵌了 compute_37 的 PTX**。
CUDA 驱动可以把 PTX 在运行时 **JIT 编译**为目标架构的机器码 —— 而 PTX 是向前兼容的，因此 **sm_120 上可以跑**。
代价是：把 Kepler 时代（compute_37）的 PTX 在 Blackwell 上 JIT 并执行，效率极差，**首次编译开销以分钟计**。

**这解释了此前观察到的现象**：进程附着 GPU（242 MiB 上下文）、`utilization.gpu = 0 %` —— 因为它绝大部分时间在**做 JIT 编译与初始化，而不是在算**。

> **工程影响（重要，且与之前的表述不同）**：
> 在 RTX 5080 上误用官方栈时，**不会立刻崩溃报错，而是「以分钟级的单算子耗时静默运行」**。
> 这比直接报错**更危险**：它极易被误判为「CARLA 慢」「场景复杂」「显存不足」，从而浪费大量时间。
>
> **判别方法**：本机任何「跑得异常慢」的现象，先执行
> ```bash
> nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv
> ```
> 若**进程已附着 GPU 但利用率长期为 0 %** → 高度怀疑是 CUDA 架构不匹配导致的 JIT 慢速路径，而非真的在计算。

**对项目可行性的影响** —— ⚠️ **此处必须再修正一次**，见 §5.2：该开销是**一次性的**，不是每个算子都慢。

### 5.2 T-03c 基准复测（区分「一次性 JIT 开销」与「每次调用都慢」）

> 这是本次审计中**最重要的一次复测**，它推翻了 §5.1 中「慢到不可用」的初步判断。

脚本 `D:\wheels\tt_bench2.py`，两个环境跑同一份代码，结果对比如下。

#### 官方栈（`tt-audit-py37`：torch 1.12.1+cu113 / py3.7）

```
[cold] first randn 512x512            :   264651.4 ms     ← 264.7 秒
[cold] first conv2d 64->64 3x3 64x64  :   556168.0 ms     ← 556.2 秒
[warm] conv2d  steady avg             :      0.132 ms
[warm] matmul 512x512 steady avg      :      0.198 ms
[cold] first matmul 1024x1024         :        0.4 ms
[warm] matmul 1024x1024 steady avg    :      0.299 ms
TOTAL WALL TIME: 821.6 s
```

#### 现代栈（`pytorch311`：torch 2.10.0+cu128 / py3.11）—— 对照基线

```
[cold] first randn 512x512            :      177.8 ms
[cold] first conv2d 64->64 3x3 64x64  :      280.3 ms
[warm] conv2d  steady avg             :      0.069 ms
[warm] matmul 512x512 steady avg      :      0.315 ms
[cold] first matmul 1024x1024         :        0.2 ms
[warm] matmul 1024x1024 steady avg    :      0.146 ms
TOTAL WALL TIME: 0.5 s
```

#### 对比

| 操作 | 官方栈 (1.12.1+cu113) | 现代栈 (2.10+cu128) | 倍数 |
|---|---|---|---|
| **冷** randn 512×512 | **264,651 ms** | 177.8 ms | ~1490× 慢 |
| **冷** conv2d 3×3 | **556,168 ms** | 280.3 ms | ~1984× 慢 |
| **热** conv2d | 0.132 ms | 0.069 ms | 1.9× 慢 |
| **热** matmul 512×512 | **0.198 ms** | 0.315 ms | **反而更快** |
| **热** matmul 1024×1024 | 0.299 ms | 0.146 ms | 2.0× 慢 |

**结论（第三次修正，也是最终结论）：**

1. 慢的部分**只有「第一次」** —— 即 CUDA 驱动对该 kernel 做 **JIT 编译**的时刻；
2. **一旦编译完成并进入缓存，性能回到正常水平**（热态与现代栈处于同一量级，多数在 2 倍以内，个别甚至更快）；
3. 因此 §5.1 中「每帧将以小时计、单条路线以年计」的推算**是错的，予以撤销**；
4. 正确的表述是：**官方栈在 RTX 5080 上可以正常速度运行，代价是一次性的、每个新 kernel 约 4.5~9 分钟的 JIT 预热**。

#### 这个「一次性开销」有多大？—— 量级估算（**推算，非实测**）

ThinkTwice 的模型包含 ResNet50、PAFPN、LSS、depth/seg 头、deformable attention、decoder、spconv 等，
**新 kernel 数量以数百计**。按每个新 kernel 首次 JIT 约 **5 分钟**估算：

```
300 个新 kernel × 5 分钟 ≈ 25 小时（首次运行）
```

⚠️ **这是推算值，未经实测**。实际值取决于 kernel 数量与驱动缓存命中情况。
若驱动缓存（Windows 下通常在 `%LOCALAPPDATA%\NVIDIA\ComputeCache`）**能跨进程持久化**，则该代价**只需付出一次**。

#### ⚠️ 但这里有一个此前被忽略的致命前提 —— 见 §5.3

### 5.3 T-04 PyTorch 有 PTX，mmcv **没有**

上一节的结论「JIT 后能正常跑」**只对 PyTorch 自身成立**。我进一步检查了各库是否携带 PTX：

| 库 | 内嵌 PTX 的 `.target sm_XX` | 能否 JIT 到 sm_120 |
|---|---|---|
| `torch_cuda_cu.dll`（PyTorch 核心算子） | **sm_37 × 152** | ✅ **能** |
| `curand64_10.dll`（`randn` 使用） | **sm_86 × 10** | ✅ 能 |
| `cudnn_cnn_infer64_8.dll`（`Conv2d` 使用） | **sm_70 × 81** | ✅ 能 |
| `cublas64_11.dll` / `cusolver64_11.dll` / `cusparse64_11.dll` / `cufft64_10.dll` | 均有 PTX | ✅ 能 |
| **`mmcv/_ext.cpython-37m-x86_64-linux-gnu.so`**（cu113/torch1.12 官方 wheel） | **无 PTX（0 条）**，只有 **compute_86 的 cubin × 957** | ❌ **不能** |

**检测方法**（可复现）：

```python
import re
d = open(so_path, 'rb').read()
print(re.findall(rb'\.target sm_(\d+)', d))   # 有内容 = 含 PTX
print(d.count(b'compute_86'))                  # cubin 的架构标记
```

**这就是最终答案**：

- **PyTorch 层**：因为携带 `compute_37` 等 PTX，**能在 sm_120 上通过 JIT 运行**（首次慢，之后正常）；
- **mmcv 层**：官方 cu113 wheel **完全没有 PTX**，**CUDA 驱动无法 JIT**，
  因此在 sm_120 上会**硬失败**（`no kernel image is available for execution on the device`），**且没有回退路径**；
- 而 mmcv 的 `ms_deform_attn` 扩展**正处于推理关键路径上**（`multi_scale_deformable_attn_function.py` 两个 autograd Function
  的 `forward` 无条件调用它，**没有任何纯 PyTorch 回退**，见 `COMPATIBILITY_MATRIX.md` §2.5）。

**由此产生一条此前未考虑过的候选路线**（**纯属推论，未经验证**）：

> 用 `TORCH_CUDA_ARCH_LIST="8.6+PTX"` **从源码重新编译 mmcv-full 1.7.0 / spconv**，
> 使其携带 compute_86 的 PTX，从而能在 sm_120 上走 JIT 路径。
> 这**不修改 ThinkTwice 的任何源码**，只是换一种方式构建依赖。
> **但**：需要 CUDA 11.3 Toolkit + gcc 6 + 一台能跑 CUDA 11.3 的 GPU 来完成编译（本机均不具备），
> 且编译产物是否能在 sm_120 上正确 JIT **未经验证**。列此仅作为备选思路。

**验证状态声明**：T-04 的**静态检查已完成**（上表为实测）。
但「重新编译 mmcv 后能否在 sm_120 上工作」**未做任何验证**，属推测。

---

## 六、验证阶梯的执行状态

任务书要求逐级验证。实际执行情况如下，**如实标注**：

| 级别 | 验证目标 | 状态 | 说明 |
|---|---|---|---|
| 1 | Python 和基本依赖能够正常导入 | ⚠️ **部分通过** | Python 3.7.1 与 torch 1.12.1 可 import；但该环境的 SSL/代理问题需要额外修复 |
| 2 | **PyTorch 能识别 GPU，并在当前架构执行简单 CUDA 运算** | ⚠️ **勉强通过，但实际不可用** | 见 T-03/T-03b：设备可识别（`is_available()==True`、capability 正确）；**运算最终能执行成功，但 256×256 的 `randn` 耗时 302 s、矩阵乘耗时 177 s**（现代栈 <0.01 s）。技术上「跑得动」，工程上**完全不可用** |
| 3 | OpenMMLab 模块与 CUDA 扩展正确加载 | ⛔ **未执行** | 级别 2 已失败，按约定停止，不再扩大改动 |
| 4 | ThinkTwice 必要模块能够导入 | ⛔ **未执行** | 同上 |
| 5 | 模型初始化与 checkpoint 加载可行 | ⛔ **未执行** | 同上；且 checkpoint 尚未下载 |

**明确声明：级别 3、4、5 未执行任何测试，因此不存在任何关于它们的「通过」结论。**

---

## 七、对仓库的改动情况

| 项目 | 状态 |
|---|---|
| 受版本控制的官方源码 | **未修改任何一行** |
| 官方配置文件 | **未修改** |
| `docs/reproduction/` 下**其他 Agent 的计划文档** | **未创建、未读取、未修改**（该目录在本次工作开始时不存在） |
| 本次新增文件 | 仅 `docs/reproduction/env-agent/` 下 4 份报告（本 Agent 的职责范围） |
| 本地新增的仓库外文件 | `D:\wheels\`（torch wheel 与测试脚本）、Conda 环境 `tt-audit-py37` |
| `git status` | 仅显示上述 4 份新增 Markdown（untracked），无 modified/deleted |

**未经批准未执行的操作**（按约定全部暂缓）：修改官方源码、运行全量训练、下载完整数据集、下载 CARLA 资产、使用来源不明的预编译 wheel、恢复/删除 WSL 发行版。

---

## 八、清理建议（供你决定，本 Agent 未执行）

| 对象 | 大小 | 建议 |
|---|---|---|
| `D:\wheels\torch-1.12.1+cu113-cp37-cp37m-win_amd64.whl` | **2.14 GB** | 若确认真机路线为 A（换机器），可删除回收空间 |
| Conda 环境 `tt-audit-py37` | ~1.5 GB | 证据留存用，可保留；删除命令：`conda env remove -n tt-audit-py37` |
| `D:\wheels\tt_test.py`、`tt_test2.py` | <10 KB | 建议保留作为证据 |

**均未执行任何删除操作。**

---

## 九、后续更新

- **T-03b（900 秒长探测）**：见下方追加记录。


## 本轮实际推进（2026-10-09，接手授权更新）

完整命令与输出：evidence/20261009-takeover/linux-bootstrap.log、install-ops.log、voxel-build*.log、toolkit-*.log、torch-clone.log、torch-submodules.log。可重跑脚本位于 scripts/。手动执行要先确认现有prefix/下载状态，不能覆盖已有环境。

1. 核对HEAD/status、9份规划、4份环境报告及HANDOVER、父级/仓库AGENTS；规划仅只读，hash保存planning-hashes.json。
2. 下载校验官方Ubuntu Base后 `wsl --import ThinkTwice-Focal <项目>/.thinktwice-runtime/wsl-focal <rootfs> --version 2`，成功；旧WSL登记及默认Ubuntu保持。
3. 新WSL apt-get update/install build-essential git binutils curl ca-certificates unzip libgl1 libglib2.0-0 libgomp1；隔离安装Miniconda3-py37_23.1.0-1，Python3.7.16。
4. bootstrap_linux.sh固定pip24.0/setuptools59.5.0/NumPy1.20.3，安装torch1.12.1+cu113、vision0.13.1+cu113；linux-basics.json：两种转换通过，randn失败no kernel image。
5. NVIDIA单一cuda-11.3.1 channel，独立cuda113-ptx prefix：nvcc/cuobjdump11.3.122、cudart11.3.109、nvrtc11.3.122、thrust11.3.109、NVTX及数学库。精确URL见cuda113-explicit.txt。首次混入13.x的prefix保留弃用。
6. cuobjdump --list-ptx/--list-elf/--dump-ptx检查原MMCV ELF；715 cubin、无列出的PTX。尝试--all提示unknown option，原始错误mmcv-list-ptx-all.txt保留，不能把该命令exit0作为检查通过。
7. spconv-cu1132.3.6/cumm-cu1130.4.11安装；初版诊断GPU fill先失败，改为CPU建输入再复制GPU后最小SubMConv3d通过193.423s；初版与修订版JSON分别保留。
8. 官方voxel源码复制到/opt/thinktwice/build（无源码改动）；CUDA_HOME=cuda113-ptx TORCH_CUDA_ARCH_LIST=8.6+PTX MAX_JOBS=2 python setup.py build_ext --inplace。初次缺cusparse.h，安装同版libcusparse等后成功；正式工具列PTX。raw kernel数值/finite通过0.922s，不代表含aten分配的完整wrapper或LSS通过。
9. 旧PyTorch源码git clone超时；官方codeload包成功，固定gitlink子模块下载部分成功；eigen超时。尚未执行torch编译。cuDNN8302官方NVIDIA GitLab头文件已取得。
10. 用户要求手动取得资产后再继续。停止已核对命令的Windows诊断PID27368和WSL子模块下载器PID14及直接子curl，保留环境/partial文件。未启动CARLA、模型、训练或全评测。

## 2026-10-09 恢复：B2 同版本发布包

此前“镜像下载中/环境编译暂停”为历史状态，已被本节更新。用户手动下载目录 `D:\Download`；两个原文件保留，隔离副本在项目 `.thinktwice-runtime/assets/carla-0.9.10.1-release`。旧Docker下载已停止，已有层保留。

| 文件 | 精确字节数 | 本地SHA256（不声称官方校验值） |
|---|---:|---|
| CARLA_0.9.10.1.tar.gz | 3956990664 | c441c35528c767962e781000ab61600aaa1fa0c2d1bd148effccdb9bab38d583 |
| AdditionalMaps_0.9.10.1.tar.gz | 1823090196 | b64b1d7b92090de99913c7a221984d54c4c462275b4d727e8cd4a20dc529646c |

URL为 `https://carla-releases.s3.us-east-005.backblazeb2.com/Linux/` 加对应文件名。参照 https://github.com/autonomousvision/transfuser/blob/2022/setup_carla.sh 。首次HEAD均200、支持bytes Range；随后重复保存maps响应头时发生curl28连接超时，不推翻用户已成功取得文件及本地校验。server-headers.txt保存本体200响应。此次无需再次下载；不触碰浏览器partial。

压缩包合计5780080860B；开始前D盘175.95GiB，预留50GiB，复制两个包后D盘179380367360B可用。WSL虚拟df的943GiB只是虚拟上限，实际受D盘约束。

执行 `python scripts/stage_carla_archives.py --source D:\Download`（脚本路径相对此报告目录），读取两次SHA并对比原件/副本。Windows基础python输出Failed to find real location提示但脚本完成且JSON/哈希一致，此提示不计为安装基础依赖通过。

地图归档只读检查：12737项，未压缩4155966167B，路径均以CarlaUE4开头，应按上述上游脚本解压覆盖到本次新安装根目录，无需重命名egg。完整gzip/tar及链接检查由deploy_carla_release.py执行，结果见evidence/20261009-carla-release/deploy.json；只有pass=true才计部署完成。

新WSL新增非root用户ttenv，安装mesa-utils、libvulkan1、libomp5、libsdl2-2.0-0及依赖（新增13.8MB，0升级）。实际glxinfo显示D3D12 NVIDIA RTX5080 Laptop、Mesa21.2.6、OpenGL core3.3；仅确认图形API身份，不预判CARLA启动通过。probe_carla_sync.py保留原egg名，连接22123、Town05、同步0.05s连续10tick，最后恢复设置；不代替传感器推理/闭环验收。

checkpoint CPU torch.load成功，state_dict1344键，元数据见evidence/20261009-takeover/checkpoint-cpu-metadata.json；不计模型匹配或推理通过。旧torch CUDA no kernel image阻塞仍保留。

## 2026-10-09 断点续配（18:50附近，运行中）

- 用户确认恢复配置；无残留CARLA/编译进程，专用WSL和已下载资产保留。CARLA解压校验deploy.json pass=true；本体+地图未压缩合计12235755540B，egg保持0.9.10原名。
- 旧PyTorch固定57项子模块现全部通过，Eigen官方GitLab固定gitlink通过Windows既有显式代理取得，sha256=0c8c490764f9c2a793133491adca0cd073b73e0bde965c68cbe58d91b5ed4261。诊断脚本已验证归档完整性并保留无效partial；修正重复解压已有合法NCCL符号链接时resolve先后顺序误判。
- 源码重编启用CUDA11.3、cuDNN8.3.2.44、compute86 PTX、ABI=0；CUDA11.3外部cudnn链接目录/opt/thinktwice/cudnn832-link/lib，不改原wheel。关闭分布式训练通信组件USE_DISTRIBUTED/NCCL/GLOO/MPI/TENSORPIPE，BUILD_TEST=0、USE_KINETO=0；保留模型数学、网络和控制源码不动。只构建wheel，不自动安装覆盖。
- 中断遗留53个无效/零字节.o，导致protobuf链接缺符号；全部路径记录evidence/20261009-takeover/interrupted-objects.json，原件改名为.o.interrupted保留，已恢复增量构建。build03失败原始日志保留；当前build04-clean-invalid.log。此前build01 cuDNN误检测OFF已主动停止；build02及以后cuDNN=1、ABI=0，不能使用build01产物做验收。
- CARLA run01 DISPLAY空、run02 DISPLAY=:0+仅日志参数均RPC前返回1；证据evidence/20261009-carla-release/run0*/。ldd未列缺失库。strace保留。真实GLX上下文探针3.3成功、4.3和4.6失败（X error165），见glx-context-before.json；原配置目标GLSL_430，支持需补齐，尚不声称已证明全部启动退出原因。
- 局部解决方案：Mesa24.0.5源码来自https://archive.mesa3d.org/mesa-24.0.5.tar.xz，20096384B，SHA256=38cc245ca8faa3c69da6d2687f8906377001f63365348a62cc6f7fafb1e8c018，与https://docs.mesa3d.org/relnotes/24.0.5.html官方值一致。构建D3D12 OpenGL后端到/opt/thinktwice/mesa24，系统Mesa21.2.6保留；只对后续CARLA启动设置库路径，不伪造GL版本。
- 固定DirectX-Headers v1.611.0（微软官方codeload，423078B，sha256=edb8b52b1379f841df5d0d5e11dde08e0c3912508179fb3711f163382e88865c）；libdrm2.4.120（官方dri.freedesktop.org，479564B，sha256=3bf55363f76c7250946441ab51d3a6cc0ae518055c0ff017324ab76cdefb327a）已独立构建安装至mesa24，不升级系统libdrm。此两hash仅本地身份。Mesa构建工具独立venv Python3.8，meson1.3.2、mako1.3.5；据真实配置错误补齐XCB开发依赖，原始失败日志mesa24-build01/02/03均保存；当前build04。
- 基础CPU导入：numpy1.20.3、cv2 5.0.0、mmcv1.7.0、torch1.12.1+cu113成功；pip check无冲突。不代替CUDA验收。
- 已固定官方mmdetection3d 1.0分支commit47285b3f1e9dba358e98fcd12e523cfd0769c876，真实版本1.0.0rc6。源码8499380B，SHA256=1d1ac7b6bf12d7873b61109ba8441922ba80551d4ce30170e3b64ea72df84034；位于/opt/thinktwice/src/mmdetection3d-47285b3f1e9dba358e98fcd12e523cfd0769c876，尚未构建安装。

本节为运行中断点，不计环境任务完成。资产获取/解压完成；CARLA运行未通过；ThinkTwice真实传感器与闭环未通过。根九份规划不改。后续先看编译进程和日志，避免重复启动编译。

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

### 2026-10-09 19:42 驱动缓存与新进程复核

base-blas-cudnn02-cache-retained.json全部通过：缓存保留的新进程卷积首次1.96756725s，十次后续0.00005175–0.000492033s；matmul首次11.290600254s，十次后续0.000034694–0.000148663s。各算子首次加载成本并不一致，不可概括重启后全部很快，也不可直接由这些小尺寸外推模型吞吐。原/root/.nv/ComputeCache保留，复制约1018MiB到独立/opt/thinktwice/cuda-cache并仅对此新目录chown ttenv:ttenv，供真实运行用户复用；后续进程CUDA_CACHE_PATH指向此目录、CUDA_CACHE_MAXSIZE=4294967296。NVIDIA官方环境变量说明允许4GiB上限、旧binary可因容量被逐出：https://docs.nvidia.com/cuda/cuda-programming-guide/05-appendices/environment-variables.html 。不设CUDA_FORCE_PTX_JIT、不清旧缓存，不改模型或默认控制。第三次base-blas-cudnn03验证ttenv+新缓存。

### 2026-10-09 19:44 非root运行库与门槛准备

base-blas-cudnn03-ttenv-cache4g.json全部通过，命令为wsl -d ThinkTwice-Focal -u ttenv，env LANG/LC_ALL=C.UTF-8 CUDA_CACHE_PATH=/opt/thinktwice/cuda-cache CUDA_CACHE_MAXSIZE=4294967296，专用conda Python执行probe_blas_cudnn.py。matmul首次8.001913546s，conv首次1.903651786s；各10次稳态与参考均通过。缓存是从root保留复制后复用，不标记清缓存冷态。正式推理可使用ttenv，无需回退root。

后续直接行动：继续观察build04，不启动第二个torch编译。wheel完成后在candidate-site安装--no-deps；全部候选诊断以ttenv、上述4GiB缓存、PYTHONPATH=/opt/thinktwice/candidate-site执行，新JSON。probe_basics.py（含Tensor↔NumPy及warning记录）→probe_ops.py deform/spconv/voxel（--repo /opt/thinktwice/build）→probe_lidar_stack.py完整原配置LiDAR/strict子权重→真实batch与route16。run_single_route_smoke.py要求显式传入上述5份通过JSON且候选torch路径正确，输出新独立目录；未具备门槛前不会启动路线。

### 2026-10-09 19:45 增量构建并发调整

本次cuDNN诊断已结束，15.7GiB WSL可用内存余量足够；只将build_torch112_ptx.sh的MAX_JOBS改为允许外部设置、默认仍2。对确认cmdline为本任务ninja -j2 install的PID1461发送SIGINT，build04在5568/5887后正常记录ninja: build stopped: interrupted by user，exit1是本代理为并发调整的计划中断，非源码编译失败。无WSL停止、无删除对象。随后env MAX_JOBS=4运行同一脚本进行增量恢复，日志torch112-ptx-build05-j4.log，活动exec session94649。编译目标compute86+PTX/cuDNN1/ABI0均不变，不运行第二份构建。

### 2026-10-09 19:50 动态链接边界核验与必要重链接范围

readelf -d实际确认旧wheel下构建的MMCV、voxel及torchvision扩展DT_NEEDED均引用libtorch_cuda_cu.so/libtorch_cuda_cpp.so；本次源码Torch的CMakeCache为BUILD_SPLIT_CUDA=OFF（单libtorch_cuda.so）。因此既有候选MMCV含PTX仍不能直接作为最终二进制使用，须基于候选Torch重编/链接这三个原版本扩展，避免LD_LIBRARY_PATH暴露旧Torch造成混载。固定torch1.12.1、vision0.13.1、MMCV1.7.0，非现代框架迁移，无模型数学/结构/控制改动。

官方vision v0.13.1 source取得：HTTP200，9241179B，本地SHA256=c32fab734e62c7744dadeb82f7510ff58cc3bca1189d17b16aa99b08afc42249，URL https://codeload.github.com/pytorch/vision/tar.gz/refs/tags/v0.13.1 。初次sandbox连接HTTP000失败，授权网络重试成功，记录torchvision-source.json。MMCV沿用既有官方归档。relink-sources.json与relink-source-preparation.log记录新源码/opt/thinktwice/src/relink-{mmcv,vision,voxel}；上游MMCV文档有合法内部相对链接，归一化后严格限制仍在归档根，不因“有链接”一概判坏。

已原样复制旧cuDNN七个版本库到/opt/thinktwice/cudnn832-runtime/lib，原torch不动，逐文件SHA256见cudnn832-runtime-sha256.txt。后续LD_LIBRARY_PATH仅新cuDNN目录+正确Toolkit lib，不包含旧torch/lib；候选torch导入后还需/proc/self/maps核验无旧Torch混载。必要扩展统一build_candidate_extension.sh，PYTHONPATH=candidate-site、8.6+PTX、默认2并发；未启动，等待候选torch安装。新voxel输出/opt/thinktwice/voxel-candidate，探针通过THINKTWICE_VOXEL_ROOT选择，不改官方源码。

19:50 build05推进76/320（重新计数的剩余任务），四并发内存仍充足，未新增编译错误；cuSPARSE弃用提示属于编译warning，非失败。

### 2026-10-09 19:58 build05真实失败及同版头文件修复

build05在307/320的torch/csrc/cuda/shared/cudart.cpp.o失败：fatal error: cuda_profiler_api.h: No such file or directory；ninja: build stopped: subcommand failed。原日志完整保存，不称编译通过。build/lib/libtorch_cuda.so及libtorch_cuda_linalg.so此前已成功链接。

官方NVIDIA package元数据查询：api.anaconda.org/package/nvidia/cuda-nvprof；同CUDA11.3.1 label对应11.3.111 h95a27d4_0。下载URL https://conda.anaconda.org/nvidia/label/cuda-11.3.1/linux-64/cuda-nvprof-11.3.111-h95a27d4_0.tar.bz2 ，HTTP200，4494686B；官方元数据MD5=702e57a3a3a018d3f2c76570e2843821核对通过（未发布SHA字段）。本地SHA256=1134b9349cab226cdac422e4b77adce03ca4daf431a6348d347539818bf27cb5用于身份。bzip2 -t通过；确认两个目标均不存在后，仅提取include/cuda_profiler_api.h与include/cudaProfiler.h到cuda113-ptx，不安装nvprof可执行文件、不改PyTorch源码/版本。头文件hash和命令见cuda113-profiler-header-repair.log。官方11.3.1 profiler说明要求该头文件：https://docs.nvidia.com/cuda/archive/11.3.1/profiler-users-guide/index.html 。

同配置MAX_JOBS=4增量续编build06-profiler-header.log，exec session60698；未启动重复构建。JPEG/PNG开发依赖在专用WSL补齐，vision-image-dev-install.log保存命令结果。candidate-source动态链接核验脚本audit_loaded_candidate.py已准备：实际/proc/self/maps只允许候选路径的libtorch/libc10，防止混载；这仍是二进制/import门槛，不替代数值测试。

## 2026-10-09 20:02 旧Torch候选成品取得，配置意图与实际ABI区分

build06-profiler-header.log构建wheel成功，exit0。/opt/thinktwice/src/pytorch-1.12.1/dist/torch-1.12.1-cp37-cp37m-linux_x86_64.whl，本地SHA256=af7c29d1098016808c9f1affee84843a6028123027cea6a1163cdb78fdf8fa0a；pip install --no-deps --target /opt/thinktwice/candidate-site，原base torch不动，torch-candidate-install01.log。

torch-candidate-identity01.json pass=true：版本1.12.1、CUDA11.3、cuDNN8302，实际torch._C._GLIBCXX_USE_CXX11_ABI=true，即ABI=1。必须修正此前“配置ABI0即成品ABI0”的推断：v1.12.1官方CMakeLists.txt第43–51行对GLIBCXX_USE_CXX11_ABI=0只追加-fabi-version=11，没有-D_GLIBCXX_USE_CXX11_ABI=0，本地GCC9的实际宏仍1。不把CMakeCache意图当实际二进制身份；候选所有Torch扩展统一用实际ABI1重建，原ABI0 wheel/旧扩展保留。框架版本/数学/网络/控制不变。

/proc/self/maps核验七个libtorch/libc10核心库全部从candidate-site/torch/lib加载，无旧核心混载；cuBLAS实际正确Toolkit11.5.1.109、cudart11.3.109、cusparse11.6.0.109。与此前base torch测试可能选用的捆绑库不是同一二进制，必须单独数值验收。linux-basics-candidate01正在以ttenv执行：CPU↔Tensor↔NumPy已通过，warnings=[]，GPU初始化仍在进行，不计GPU通过。

必要扩展已启动：voxel-relink01（exec4618）、mmcv-relink01（候选实际Torch头/ABI/单库、2并发）。待voxel结束后再启动vision，避免超过资源并发。已有wheel与/opt/thinktwice/build保留；新voxel输出/opt/thinktwice/voxel-candidate。候选完整GPU/模型/真batch/闭环尚未通过。

### 2026-10-09 20:04 候选PTX身份与原始voxel重链接完成

torch-candidate-cuda-identity.txt记录wheel精确字节数、主库SHA256；torch-candidate-cuobjdump-list-ptx.txt正式cuobjdump列出PTX，不代替执行。voxel-relink01编译/链接实际成功，随后脚本错误假设ops根有__init__.py而复制失败；原仓库此根是命名空间包，无该文件。已将复制改为仅源文件存在才复制，voxel-relink02-wrapper-copy.log增量执行通过，未改官方源文件。新扩展/opt/thinktwice/voxel-candidate，链接-ltorch_cuda、编译宏_GLIBCXX_USE_CXX11_ABI=1；原ABI0/split扩展在/opt/thinktwice/build保留。MMCV exec12332、vision exec37868继续各2并发重建，均已实测编译命令ABI1。

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

## 2026-10-09 20:45：恢复断点与 CARLA RPC readiness

旧栈基础、四类 CUDA 算子、完整 LiDAR 栈和 GPU 完整模型 strict 已全部通过，见更新 HANDOVER。smoke02 的 client native stack 深入35帧确认 GetInstanceTM→GetServerVersion→rpc::client::wait_conn；独立只读客户端能连接，地图仍 Town03，不能误判为已进入路线。主动 SIGINT 自己 inferior88 保存 gdb stacks，监督器回收 evaluator37，run.json pass=false。没有新的 SIGSEGV。

prepare_smoke_overlay.py 生成独立 v3，新增短超时新客户端 RPC readiness（2s，每次重建，总180s），runner --host=127.0.0.1。脚本 ET.tostring(xml_declaration=...) 在 Python3.7 不支持，改 ElementTree.write(BytesIO)，路线字节 SHA 不变1475a447c063a3e34b2d84311fc6270e5efb09e9f5c652dbe0fd2cd6c70e4e4e。v3 evaluator hash ffb6af75f2ed9a899df6e253d519233cd9990ac5d8e00edcc8aa8d5b2b2a1570。原源码未改。

已启动 .thinktwice-runtime/runs/20261009-smoke03-gdb-ready，完整命令/门禁写run.json，监督器日志 evidence/20261009-takeover/smoke03-supervisor.log。保留全部前次失败运行。当前继续捕获原场景加载 SIGSEGV，尚不能计真实传感器或闭环通过。

## 2026-10-09 20:47：Traffic Manager 独立初始化通过；smoke04 启动

smoke03-gdb-ready 的 RPC readiness 已通过，但首次 world.tick 默认10秒墙钟超时，结果 Failed - Simulation crashed、0%路线、0推理；没有 native SIGSEGV。不能将这次超时写成新崩溃。

独立 .thinktwice-runtime/runs/20261009-tm01-gdb 在同样原版本、原图形启动器、gdb下，实际复现原顺序 get_trafficmanager→set_sync(False)→load_world(Town05)→world_sync0.05→reset_all_traffic_lights→TM_sync(True)→seed2023→world.tick(120)，连续10tick全部通过、设置恢复。证据该目录sync-probe.json/run.json/server-console.log。客户端快照堆栈tm01-client-stack.txt取于中间初始化，最终已成功，不能据中间等待判死。

部署 v4 仅将 evaluator 内两处初始化 world.tick 的墙钟等待改120秒，仿真步长0.05、场景和控制不变；独立diff与manifest保留在launch/20261009-smoke-v4，hash673132db8c2811c093973500c62030675164a214f1faa9ade1973eb048d94a81。smoke04-gdb-tick120正在运行，完整命令和8项gate保存在run.json；不并行重复启动。

## 2026-10-09 20:52：CARLA native crash 已精确归属图形编译线程

smoke04-gdb-tick120 顺利通过RPC/官方agent加载/Town05/Seed2023/IS_EVAL，但场景设置时 Thread38 CarlaUE4:gdrv0 SIGSEGV。原生PC在 /opt/thinktwice/mesa24/lib/dri/swrast_dri.so 的 nir_lower_wpos_ytransform.cold，偏移0x58e02；objdump指令 mov 0x20,%eax，随后ud2，证明空地址读取。非 CUDA模型推理栈；尚无sensor inference。全部72线程堆栈保存于该run console.log，run.json pass=false、inference_calls0。不能因为文件入口叫swrast_dri.so就称软件渲染，此DRI实际选择D3D12 NVIDIA后端，见既有renderer证据。

先构建相同Mesa24.0.5单文件诊断：build_mesa_nir_diagnostic.py 从原ninja取得精确编译命令，仅 nir_lower_wpos_ytransform.c 增加-g/-O1/-fno-omit-frame-pointer，重新链接并复制 /opt/thinktwice/mesa24-nir-debug/lib/dri/swrast_dri.so。安装的mesa24发布版完全保留，无源码diff。build01因PATH缺ninja失败并保留，build02加conda/bin后成功。文件身份与完整命令记录manifest及mesa-nir-diagnostic-build02.log。

smoke05-nir-debug 使用独立诊断DRI路径/同一原路线启动，目的是确认NULL读的源码位置再局部修复，不盲目升级框架。可重复启动入口新增 scripts/run_candidate_smoke.ps1 -RunName <全新名称> -Launcher <启动器>，所有旧run保留，原模型与控制未修改。

## 2026-10-09 20:57：单文件调试不足，保留原始证据继续定位

smoke05复现同PC，但build02的Ninja依赖解析重新使用release参数覆盖手工debug对象，故没有有效符号；已纠正此前诊断构建成功的含义。build03独立build-nir-debug.ninja保留指定单文件-g/-O1，readelf证实DWARF，复制到mesa24-nir-debug-v2。smoke06仍在同绝对偏移0x58e02崩溃，但就近符号变为nir_opt_access.cold，无法据此认定nir_lower_wpos_ytransform具体行；没有实施猜测性源码修复。

已启动同版本Mesa24.0.5完整debugoptimized构建（独立build-d3d12-debug、prefix mesa24-debug），保持发布版安装。日志mesa24-full-debug-build01.log。另以原发布版、仅MESA_SHADER_CACHE_DISABLE=true执行smoke07-no-gl-cache，原磁盘缓存及CUDA缓存不删。两个诊断均不改模型/控制或CARLA资源。仍未真实传感器或闭环通过。

## 2026-10-09 21:02：完整符号定位 D3D12 三角带聚合复制；局部候选修复

smoke08-full-mesa-debug 触发 SIGABRT，准确断言 ../src/compiler/nir/nir_lower_var_copies.c:85 emit_deref_copy_load_store: glsl_type_is_vector_or_scalar(dst_deref->type)。完整链：d3d12_select_shader_variants→select_shader_variant(GEOMETRY,triangle_strip=1)→d3d12_lower_triangle_strip:776→nir_lower_var_copies。这纠正此前仅凭release近似cold符号归属nir_lower_wpos的推断，不再基于该误定位修复。

源码审查：三角带转换生成聚合输出复制，结尾直接lower_var_copies，后者明确只接受最终标量/向量。最小候选在其前加入同版本已有标准 nir_split_var_copies pass，分解复制再lower，保留三角带重排/着色器表达意图。属于本地部署图形驱动修复，不冒称上游patch；没有改CARLA shader、原agent、模型数学/结构、五轮或控制。

build_mesa_triangle_copy_fix.py 保留原源文件 .c.before-triangle-copy-fix、原mesa24与mesa24-debug安装；增量重编复制 /opt/thinktwice/mesa24-triangle-fix/lib/dri/swrast_dri.so。精确diff：evidence/20261009-takeover/mesa-triangle-copy-fix.diff；前后source SHA及候选库hash/bytes：mesa-triangle-copy-fix-build.json；构建日志mesa-triangle-copy-fix-build01.log。smoke09-triangle-copy-fix已启动真实路线验证，构建成功不等于运行/闭环通过。

## 2026-10-09 21:05：第二处三角带数组处理修复；smoke10

smoke09 第一处 aggregate-copy 断言已越过，但随后 nir_validate_shader(after nir_split_var_copies) 在 glsl_base_type_get_bit_size 报 unknown base type。源码证明 lower_triangle_strip_store 只构建 tmp_output[vertex_index]，未保留原 store_deref 在原输出数组内的元素索引，导致数组类型直接store标量。未禁用断言或跳过几何处理。

局部v2保留原deref root以下全部数组/结构索引（标准 nir_deref_path + nir_build_deref_follower），同时保留原 nir_intrinsic_write_mask，不再硬编码0xf。继续包含标准复制拆分。精确diff mesa-triangle-fix-v2.diff 与库身份 mesa-triangle-fix-v2-build.json；原始源及第一候选分别备份，原mesa24/mesa24-debug安装保留。新库 /opt/thinktwice/mesa24-triangle-fix-v2/lib/dri/swrast_dri.so，build_mesa_triangle_index_fix.py 增量成功。此修改仅纠正图形驱动变换对原shader输出的保留，不修改CARLA原shader或模型/control。

smoke10-triangle-index-fix 当前运行中，仍须原route16、真实sensor六级finite与控制及最终结果JSON验收。旧失败全部保留。

## 2026-10-09 21:07：真实传感器已接通，首个 batch 正在完整推理

smoke10-triangle-index-fix 已越过所有此前native crash位置，完成 Town05、同步/seed2023、原Town05Long单route16场景和amount=120背景交通，进入Running the route。原agent真实sensor输入事件已记录；默认历史积累step0–30的原控制返回均finite/range valid，未改预热时长。first-real-batch.pt 已保存39796762B，当前原 forward_inference 首次执行尚未返回。不能提前计六级输出或闭环通过。

图形驱动v2已支持原场景运行到传感器和模型入口，后续仍须持续验证，不能由此称完整CARLA路线已通过。所有精确日志/事件保存在 .thinktwice-runtime/runs/20261009-smoke10-triangle-index-fix。

## 2026-10-09 21:11：真实 batch 全模型重放通过；实时闭环 smoke11

smoke10 在step31原forward中已通过图像/LiDAR并到decoder transform_fpn_feats，但 spatial_shapes.prod(1) 触发 nvrtc: invalid value for --gpu-architecture。旧 torch1.12.1 jit_utils.cpp 的 codegenOutputQuery 仅识别NVRTC11.0，11.3走未知版本分支，错误按真实SM120请求SASS。原始完整堆栈及JIT代码保存在smoke10 console.log/agent-events.jsonl；不是已成功完整推理。

局部框架部署修复：仅为NVRTC11.1–11.3指定最高8.6；原代码已有dev超过max时compile_to_sass=false，因此自然使用compute86 PTX。未改模型表达式或operator公式。build_torch_nvrtc_arch_fix.py 仅增量jit_utils.cpp.o+libtorch_cuda.so，原lib备份candidate-backups/torch-before-nvrtc-arch-fix，原源码.cpp.before-nvrtc-arch-fix。新库310286504B，SHA ce89a629b94ee4847849f180de2ce4b5e6fe56b20c4be360bede046617191c0b。源码diff/manifest/buildlog均保存在本目录evidence。

real-batch-replay01.json 实际通过：prod整数结果[6,20]；原官方1344键strict、五轮、保存的真实sensor batch SHA988f428ea008216ea8ef5156503d5200866491c75c5af3076249fea9ae57a4b1；两次完整forward的五组主要输出均六级finite，pred_wp[1,6,4,2]；同步耗时首次4.83s、第二次0.34s（既有缓存，不称空缓存冷态）。离线真实batch重放不能替代实时控制闭环。

runner新增--replay必需门禁，要求重放pass/refine5且hash匹配当前libtorch_cuda，旧8项gate作为基线保留。smoke11-real-loop已启动原route16实时闭环，服务器图形v2候选，路线/默认控制/背景交通120不变。尚须最终结果验收。

## 2026-10-09 21:24：用户明确短 smoke≥200；smoke11 收尾误判已保存并修正

用户已选择“连续至少200次实时推理和控制，确认车辆与路线进度后保存并结束”，不等待整条1.1km路线。finish_short_smoke.py 首次只读新客户端立即get_actors返回frame0/空actor cache，导致探针AssertionError0；独立只读重复确认收到流快照后255actors/123vehicles/hero200正常。修正为world.wait_for_tick(10)只等待现有评测器时钟，不主动tick；原失败smoke-acceptance.json保留。

smoke11最终完成281次连续原完整五轮推理、312次合法控制，无inference failure，主要五组输出均六级finite；只读定位hero移动33.501m。原results.json/console统计路线2.95039194%，Collision/OutsideLanes/RedLight/Stop/InRoute/Blocked/Timeout均SUCCESS，RouteCompletion为FAILURE（用户选短测主动结束，整路线未完）。原默认stuck机制预热后日志保留，未干预控制。

发现收尾监督器竞争：SIGINT正常停止原ScenarioManager并写完评分后，服务器先退出、evaluator仍在atexit清理，父监督器10秒grace过早SIGTERM，原run.json returncode=-15/server_abort；因此本轮严格short-smoke gate暂记false，未篡改原统计或忽略清理问题。修复只对存在本任务termination.json的计划短测退出给予60秒收尾窗口，意外服务器退出仍10秒。runner内集成>=200自动停止观察器，默认短测200；原run.json保持整路线语义，单独smoke-acceptance.json验收短测。

当前同一已通过的环境启动smoke12-bounded-final，脚本 run_candidate_smoke.ps1 默认已指向实际修复过的Mesa v2 launcher（不再默认旧失败driver）。不扩大完整评测。需确认原evaluator正常return0、独立短测pass与无遗留自身服务进程后交接。


## 2026-10-09 21:41:03 收尾阻塞定位与 v5 复验

smoke12 已完成203次连续实时推理、234次有效控制，移动26.951478m、路线2.3397511599%，但60秒等待仍导致退出-15，短测未通过。原生堆栈 smoke12-cleanup-native-stack.txt 显示 World::GetSettings RPC 等待。原路线上已完成_cleanup，SIGINT绑定引用使析构延迟至服务器atexit关闭之后，析构再次执行_cleanup访问已关闭服务。只延长等待不能解决。独立overlay v5在正常_cleanup末标记完成、每路线重置，只让析构跳过已完成的重复清理；原源码保留。生成命令：WSL ThinkTwice-Focal/ttenv，conda/bin/python scripts/prepare_smoke_overlay.py。v5 SHA256 5d5920e87de69b86e3af89479fc436d014d56fe8f3541f4b56282ab8a87c38b2，diff/manifest 位于 .thinktwice-runtime/launch/20261009-smoke-v5。现运行 run_candidate_smoke.ps1 -RunName 20261009-smoke13-cleanup-final，等待真实200次与正常退出，尚不提前宣告通过。



## 2026-10-09T21:51:07 最终交付验收

用户最终选择的≥200次短闭环已通过：203次连续实时完整推理、234次合法控制、六级全部finite、移动27.304m、路线2.339751%，原评测器return0、无server_abort。最终smoke13-cleanup-final/smoke-acceptance.json pass=true；原整路线run/results状态未完成保留。详见FINAL_ENVIRONMENT_REPORT.md与final-delivery-summary.json。资产完成、CARLA/推理通过、短smoke通过分别记录；未训练、未完整Town05 Long。交接统筹，不再扩大运行。
