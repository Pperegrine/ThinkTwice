# 已知问题与处理状态

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

## 2026-10-09 21:24：用户明确短 smoke≥200；smoke11 收尾误判已保存并修正

用户已选择“连续至少200次实时推理和控制，确认车辆与路线进度后保存并结束”，不等待整条1.1km路线。finish_short_smoke.py 首次只读新客户端立即get_actors返回frame0/空actor cache，导致探针AssertionError0；独立只读重复确认收到流快照后255actors/123vehicles/hero200正常。修正为world.wait_for_tick(10)只等待现有评测器时钟，不主动tick；原失败smoke-acceptance.json保留。

smoke11最终完成281次连续原完整五轮推理、312次合法控制，无inference failure，主要五组输出均六级finite；只读定位hero移动33.501m。原results.json/console统计路线2.95039194%，Collision/OutsideLanes/RedLight/Stop/InRoute/Blocked/Timeout均SUCCESS，RouteCompletion为FAILURE（用户选短测主动结束，整路线未完）。原默认stuck机制预热后日志保留，未干预控制。

发现收尾监督器竞争：SIGINT正常停止原ScenarioManager并写完评分后，服务器先退出、evaluator仍在atexit清理，父监督器10秒grace过早SIGTERM，原run.json returncode=-15/server_abort；因此本轮严格short-smoke gate暂记false，未篡改原统计或忽略清理问题。修复只对存在本任务termination.json的计划短测退出给予60秒收尾窗口，意外服务器退出仍10秒。runner内集成>=200自动停止观察器，默认短测200；原run.json保持整路线语义，单独smoke-acceptance.json验收短测。

当前同一已通过的环境启动smoke12-bounded-final，脚本 run_candidate_smoke.ps1 默认已指向实际修复过的Mesa v2 launcher（不再默认旧失败driver）。不扩大完整评测。需确认原evaluator正常return0、独立短测pass与无遗留自身服务进程后交接。


## 2026-10-09 21:41:03 收尾阻塞定位与 v5 复验

smoke12 已完成203次连续实时推理、234次有效控制，移动26.951478m、路线2.3397511599%，但60秒等待仍导致退出-15，短测未通过。原生堆栈 smoke12-cleanup-native-stack.txt 显示 World::GetSettings RPC 等待。原路线上已完成_cleanup，SIGINT绑定引用使析构延迟至服务器atexit关闭之后，析构再次执行_cleanup访问已关闭服务。只延长等待不能解决。独立overlay v5在正常_cleanup末标记完成、每路线重置，只让析构跳过已完成的重复清理；原源码保留。生成命令：WSL ThinkTwice-Focal/ttenv，conda/bin/python scripts/prepare_smoke_overlay.py。v5 SHA256 5d5920e87de69b86e3af89479fc436d014d56fe8f3541f4b56282ab8a87c38b2，diff/manifest 位于 .thinktwice-runtime/launch/20261009-smoke-v5。现运行 run_candidate_smoke.ps1 -RunName 20261009-smoke13-cleanup-final，等待真实200次与正常退出，尚不提前宣告通过。



## 2026-10-09T21:51:07 最终交付验收

用户最终选择的≥200次短闭环已通过：203次连续实时完整推理、234次合法控制、六级全部finite、移动27.304m、路线2.339751%，原评测器return0、无server_abort。最终smoke13-cleanup-final/smoke-acceptance.json pass=true；原整路线run/results状态未完成保留。详见FINAL_ENVIRONMENT_REPORT.md与final-delivery-summary.json。资产完成、CARLA/推理通过、短smoke通过分别记录；未训练、未完整Town05 Long。交接统筹，不再扩大运行。
