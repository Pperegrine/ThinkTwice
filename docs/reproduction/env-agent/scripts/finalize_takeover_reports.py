from pathlib import Path
import shutil

base=Path(__file__).resolve().parents[1]
ev=base/'evidence'/'20261009-takeover'
for name in ['HANDOVER.md','COMPATIBILITY_MATRIX.md','KNOWN_ISSUES.md','ENVIRONMENT_AUDIT.md','SETUP_LOG.md']:
    snapshot=ev/(name+'.before-takeover')
    if not snapshot.exists(): shutil.copy2(str(base/name),str(snapshot))

(base/'COMPATIBILITY_MATRIX.md').write_text('''# ThinkTwice 环境兼容性矩阵

更新：2026-10-09。替代上一轮未经算子执行支持的“最终判定”。原文保留于 evidence/20261009-takeover/*.before-takeover。

## 平台、版本与真实测试范围

| 环境 | 版本/产物 | 实际结论 |
|---|---|---|
| Windows旧隔离审计环境 | Python3.7.1、torch1.12.1+cu113 | 继承T-03c的randn/conv/mm冷热测量；新CPU/GPU Tensor↔NumPy转换通过；新完整计时被用户暂停 |
| Linux专用WSL ThinkTwice-Focal | Ubuntu20.04.5、Python3.7.16、torch1.12.1+cu113、vision0.13.1+cu113、NumPy1.20.3 | CPU/GPU复制往返通过；randn实际失败：no kernel image。Linux wheel不能继承Windows DLL的PTX结论 |
| MMCV官方既有wheel | mmcv-full1.7.0，cp37 manylinux1 ELF；身份见TAKEOVER_STATUS | cuobjdump11.3列出715个cubin、未列PTX。实际deform调用在内部aten zeros失败，目标attention kernel尚未隔离验收 |
| spconv/cumm | spconv-cu1132.3.6、cumm-cu1130.4.11 | SubMConv3d(4,4,kernel1)数值与finite通过，shape[3,4]，首调用约193.42s；不代表完整SparseEncoder通过 |
| 官方voxel_pooling | CUDA11.3.122、gcc9.4、8.6+PTX，源码不变 | 编译成功，cuobjdump列PTX；raw kernel执行及归约参考值通过，shape[1,2,2,2]，约0.922s。包装层含aten zeros_like等，完整包装层仍待基础torch修复 |
| 现代Windows用户环境 | 继承旧审计信息 | 未改动；不作为ThinkTwice环境交付 |
| CARLA0.9.10.1 | 未获取服务端 | 官方S3/CDN下载失败，API/地图/渲染/时钟未验 |

精确版本见 pip-freeze-final.txt、cuda113-explicit.txt；新Toolkit为 /opt/thinktwice/cuda113-ptx。前次 /opt/thinktwice/cuda-11.3 混入CUDA13开发包，已弃用并保留日志，不用于构建。

## 冷/热态边界

旧T-03c：Windows torch1.12.1首randn264651.4ms、首conv556168.0ms；热conv0.132ms、热mm512为0.198ms、热mm1024为0.299ms。保留为原报告历史观测，不是本轮重跑结果。原脚本未明确清空驱动缓存，不能严格称为cache-cold。不能从几个首调用推算所有kernel分钟级或模型需数十小时，也不能保证跨进程缓存一直有效。

## 路线与成本（估算，非承诺）

| 路线 | 时间/资源 | 当前动作 |
|---|---|---|
| 可访问旧栈Linux GPU | 约1–2工作日；单GPU及足够显存，建议空闲100GB以上以容纳包/解包/日志 | 优先，但用户确认暂无 |
| 本机5080独立WSL、旧框架带PTX重编 | 约2–5工作日，当前WSL约15GiB RAM+4GiB swap；构建需额外磁盘 | 已建立平台、编译并执行voxel raw；Linux旧torch本体仍需重编，不只MMCV |
| 整套现代框架迁移 | 多日到周级；需接口和数值回归 | 不启动。只有旧框架路线明确阻塞后，单独提交具体范围 |
| CARLA与推理分离 | 额外服务端、网络、启动配置验证 | 单独判断，不替代推理CUDA验证 |

## 撤回的旧推论

- 字符串未找到.target不证明无PTX；正式cuobjdump和实际执行优先，绑定具体文件hash。
- 无sm_120 SASS不等于不能通过PTX执行；CUDA11.3不能生成sm_120 SASS，但能生成compute86 PTX，voxel原始kernel已验证可在5080执行。
- 不再把spconv与MMCV合并判失败，spconv最小算子已有正面证据。
- 不因缺sm_89直接排除4090/4080：cubin兼容规则取决于major/minor，仍需逐算子验证。
- 相同旧栈与旧GPU也不能凭配置承诺位级一致或100%原样通过；真实模型/闭环才是验收。

机制依据：[NVIDIA Blackwell Compatibility Guide](https://docs.nvidia.com/cuda/archive/12.8.0/blackwell-compatibility-guide/index.html)。行为保持：官方数学、网络、5轮refinement和默认控制不改。当前无可用模型环境交付。
''',encoding='utf-8')

(base/'KNOWN_ISSUES.md').write_text('''# 已知问题与处理状态

更新：2026-10-09。原始历史报告保存在 evidence/20261009-takeover/，以本轮实际范围为准。

| ID | 确切问题 | 已尝试/下一行动 |
|---|---|---|
| KI-01 | 旧Ubuntu/Ubuntu-D登记路径无VHDX | 可读D盘/用户目录未发现备份，拒绝访问目录留档；不删除旧发行版。已独立创建ThinkTwice-Focal且启动成功，平台阻塞已绕过 |
| KI-02 | Linux torch1.12.1+cu113 randn失败no kernel image | libtorch_cuda_cu.so的cuobjdump未列PTX；准备v1.12.1官方源码重编8.6+PTX。Windows测试不可外推 |
| KI-03 | 首次初始化/JIT耗时与稳态混淆 | 撤回“每帧小时级”等推算；旧T-03c冷/热分开保留。本轮Windows复测用户暂停，不能标计时通过 |
| KI-04 | MMCV预编译及完整sparse链尚未通过 | 正式检查具体MMCV ELF；deform内部torch zeros失败，仍需修复torch后重测。spconv最小算子实际通过，不能再合并判失败 |
| KI-05 | 文档遗漏mmcls等运行依赖 | 尚未安装完整OpenMMLab/mmdet3d；候选mmcls0.25.0需运行确认 |
| KI-06 | mmdet3d 1.0分支应固定commit | 尚未取源码并pin，不把分支号当已验版本 |
| KI-07 | 网络/沙箱/代理 | 沙箱DNS/WSL注册查询受限时用受审查的沙箱外工具；新WSL apt/PyPI可达；GitHub git超时，官方codeload成功 |
| KI-08 | NumPy初始化警告 | 旧Windows环境缺NumPy；项目内wheel解包+PYTHONPATH修复，Windows和Linux CPU/GPU转换实测通过。Windows旧env本身未修改 |
| KI-09 | CUDA编译Toolkit | 已在新WSL独立安装精确11.3工具及库；首次未pin子包误混CUDA13开发库，弃用原prefix，改用单一官方11.3.1源的cuda113-ptx。voxel缺cusparse.h已补库解决 |
| KI-10 | CARLA包无法获取 | 官方release的S3/CDN403，Windows与WSL均复核；等待用户手动下载官方Linux0.9.10.1及地图包，不升级版本绕过 |
| KI-11 | 训练数据 | 本任务无需也不下载训练集；不是推理阻塞 |
| KI-12 | 官方checkpoint尚未获取 | DriveTCP超时，百度页面可到但需m5di提取后下载；用户将手动操作 |
| KI-13 | GPU枚举不能验收CUDA | 新Linux复制成功而randn失败即反例；不能强制要求sm120出现在arch_list，否则错误拒绝PTX路线 |
| KI-14 | 16GiB显存下模型与CARLA共存 | 模型/服务端尚未启动，未测峰值，不能声称足够或一定OOM |
| KI-15 | PyTorch源码子模块不完整 | gitHTTPS超时；官方v1.12.1源码包成功，固定gitlink子模块下载部分成功，eigen GitLab连接超时；用户暂停时停止下载器，manifest保留 |

用户最新指示：先手动取得文件再继续。当前所有长时间验证/下载已暂停，环境与资产不清理。基础torch重编尚未开始，模型导入/构造/checkpoint、CARLA/API/地图、真实batch及单路线均未通过。
''',encoding='utf-8')

notice='''> **2026-10-09 接手更正：本文件下方为上一轮历史审计/原始日志。当前授权、状态和纠正以 [TAKEOVER_STATUS.md](TAKEOVER_STATUS.md)、[COMPATIBILITY_MATRIX.md](COMPATIBILITY_MATRIX.md)、[KNOWN_ISSUES.md](KNOWN_ISSUES.md) 为准。旧文中“仅审计等待决策”“MMCV/spconv必然失败”“全模型数十小时”“必须注销WSL”等结论不再有效；原错误输出保留，不作为当前通过声明。**

'''
for name in ['ENVIRONMENT_AUDIT.md','SETUP_LOG.md']:
    old=(base/name).read_text(encoding='utf-8')
    (base/name).write_text(notice+old,encoding='utf-8')

with (base/'SETUP_LOG.md').open('a',encoding='utf-8') as f:
    f.write('''

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
''')

(base/'HANDOVER.md').write_text('''# ThinkTwice 环境任务交接 — 2026-10-09

**状态：按用户要求暂停，等手动下载官方资产；环境搭建未完成。** 当前详细报告：[TAKEOVER_STATUS.md](TAKEOVER_STATUS.md)。用户授权新专用环境安装/重编，但不改模型数学、结构、完整5轮和默认控制；不改项目根九份规划。后续先检查本目录最新日志，不重复硬件审计。

## 当前保存状态

- 旧Windows项目/环境和Ubuntu、Ubuntu-D保留。默认WSL仍Ubuntu。
- 独立WSL `ThinkTwice-Focal`（Ubuntu20.04.5），VHDX位于项目`.thinktwice-runtime/wsl-focal`。
- Python `/opt/thinktwice/conda/bin/python`：3.7.16，torch1.12.1+cu113，vision0.13.1+cu113，NumPy1.20.3。
- 正确Toolkit `/opt/thinktwice/cuda113-ptx`；早先 `/opt/thinktwice/cuda-11.3` 混入新版开发子包，弃用保留。
- 原始官方voxel构建 `/opt/thinktwice/build`；官方torch源码 `/opt/thinktwice/src/pytorch-1.12.1`，子模块尚不全，未开始torch编译。
- 证据 `evidence/20261009-takeover/`，部分子模块归档和manifest在 `/opt/thinktwice/assets/submodules`。
- 长时间诊断/下载已停止；无训练、模型/配置/控制源码diff。

## 七级验收

| 级别 | 确切结果 |
|---|---|
| 1 | Windows/Linux CPU↔Tensor↔CUDA↔NumPy数值往返通过；完整基础运行依赖未齐 |
| 2 | 历史Windows局部冷热数据保留；本轮Linux randn失败no kernel image；本轮Windows新finite/计时被用户暂停，不能计通过 |
| 3 | spconv最小SubMConv3d通过；voxel raw原始CUDA归约通过；MMCV实际调用在内部torch zeros失败；完整SparseEncoder/voxel wrapper/deform kernel均未通过 |
| 4 | ThinkTwice导入/构造/官方checkpoint键shape未验 |
| 5 | CARLA/API/地图同步未验 |
| 6 | 原agent真实sensor batch六级输出/控制未验 |
| 7 | 单路线连续闭环JSON、路线进度/终态未验 |

## 纠正上一轮结论

Windows旧torch有局部成功，不代表Linux wheel能运行；两者二进制不同。MMCV字符串扫描不足以定论，已增加hash和cuobjdump；实际调用仍先受torch zeros阻塞。spconv此前未测却被合并判死，现已有最小算子通过。旧WSL无需删除也能独立建新平台。CUDA11.3的compute86 PTX已在5080运行voxel raw，不能说重编“绝不可能”。

## 继续所需最小资源与下一行动

用户正在手动取得官方ThinkTwice checkpoint、CARLA0.9.10.1 Linux本体、同版AdditionalMaps，建议放项目`.thinktwice-runtime/assets/manual`，保留文件名，不解压。Drive连接超时、官方CARLA S3/CDN403已实测；不使用不明第三方包。

文件取得后先核对来源/大小/SHA256和空间，然后恢复旧torch源码子模块（eigen GitLab超时未解决），以8.6+PTX构建旧框架。首条环境诊断命令：

```powershell
$env:WSL_UTF8='1'
wsl -d ThinkTwice-Focal --cd '/mnt/d/Desktop/端到端自动驾驶开源模型调研' --exec /opt/thinktwice/conda/bin/python ThinkTwice/docs/reproduction/env-agent/scripts/probe_basics.py ThinkTwice/docs/reproduction/env-agent/evidence/20261009-takeover/linux-basics-resume.json
```

未修复torch前预期仍失败，不能盲重跑当修复。新的测试run_id/JSON不得覆盖现有原始错误。恢复子模块脚本有未完成下载需检查（存在的tar须先验证完整性），不得无条件把partial归档当完整文件。之后依次基础CUDA→关键算子→模型/权重→CARLA→真batch→单路线smoke。单路线通过即交接，不扩大Town05 Long。
''',encoding='utf-8')

with (base/'TAKEOVER_STATUS.md').open('a',encoding='utf-8') as f:
    f.write('''

## 暂停时最终更正（优先于上方过程快照）

用户要求“获得本地文件之后我们再继续推进”，已暂停。Linux旧torch已安装但randn实际失败no kernel image；转换通过。spconv最小稀疏卷积通过193.423s，voxel raw原始CUDA内核通过0.922s，具体JSON见HANDOVER。MMCV调用先在aten zeros失败，不能声称目标kernel已隔离通过/失败。正确Toolkit为cuda113-ptx；原cuda-11.3 prefix的未pin子包混入CUDA13，保留弃用。旧torch源码官方归档/部分子模块、同版cuDNN头文件保留；torch尚未开始编译。模型/权重/CARLA/真实batch/单路线均未验。已保存所有环境报告原文快照并重写过强结论。
''')
