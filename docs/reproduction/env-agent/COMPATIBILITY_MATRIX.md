# ThinkTwice 环境兼容性矩阵

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

## 2026-10-09 21:02：完整符号定位 D3D12 三角带聚合复制；局部候选修复

smoke08-full-mesa-debug 触发 SIGABRT，准确断言 ../src/compiler/nir/nir_lower_var_copies.c:85 emit_deref_copy_load_store: glsl_type_is_vector_or_scalar(dst_deref->type)。完整链：d3d12_select_shader_variants→select_shader_variant(GEOMETRY,triangle_strip=1)→d3d12_lower_triangle_strip:776→nir_lower_var_copies。这纠正此前仅凭release近似cold符号归属nir_lower_wpos的推断，不再基于该误定位修复。

源码审查：三角带转换生成聚合输出复制，结尾直接lower_var_copies，后者明确只接受最终标量/向量。最小候选在其前加入同版本已有标准 nir_split_var_copies pass，分解复制再lower，保留三角带重排/着色器表达意图。属于本地部署图形驱动修复，不冒称上游patch；没有改CARLA shader、原agent、模型数学/结构、五轮或控制。

build_mesa_triangle_copy_fix.py 保留原源文件 .c.before-triangle-copy-fix、原mesa24与mesa24-debug安装；增量重编复制 /opt/thinktwice/mesa24-triangle-fix/lib/dri/swrast_dri.so。精确diff：evidence/20261009-takeover/mesa-triangle-copy-fix.diff；前后source SHA及候选库hash/bytes：mesa-triangle-copy-fix-build.json；构建日志mesa-triangle-copy-fix-build01.log。smoke09-triangle-copy-fix已启动真实路线验证，构建成功不等于运行/闭环通过。

## 2026-10-09 21:11：真实 batch 全模型重放通过；实时闭环 smoke11

smoke10 在step31原forward中已通过图像/LiDAR并到decoder transform_fpn_feats，但 spatial_shapes.prod(1) 触发 nvrtc: invalid value for --gpu-architecture。旧 torch1.12.1 jit_utils.cpp 的 codegenOutputQuery 仅识别NVRTC11.0，11.3走未知版本分支，错误按真实SM120请求SASS。原始完整堆栈及JIT代码保存在smoke10 console.log/agent-events.jsonl；不是已成功完整推理。

局部框架部署修复：仅为NVRTC11.1–11.3指定最高8.6；原代码已有dev超过max时compile_to_sass=false，因此自然使用compute86 PTX。未改模型表达式或operator公式。build_torch_nvrtc_arch_fix.py 仅增量jit_utils.cpp.o+libtorch_cuda.so，原lib备份candidate-backups/torch-before-nvrtc-arch-fix，原源码.cpp.before-nvrtc-arch-fix。新库310286504B，SHA ce89a629b94ee4847849f180de2ce4b5e6fe56b20c4be360bede046617191c0b。源码diff/manifest/buildlog均保存在本目录evidence。

real-batch-replay01.json 实际通过：prod整数结果[6,20]；原官方1344键strict、五轮、保存的真实sensor batch SHA988f428ea008216ea8ef5156503d5200866491c75c5af3076249fea9ae57a4b1；两次完整forward的五组主要输出均六级finite，pred_wp[1,6,4,2]；同步耗时首次4.83s、第二次0.34s（既有缓存，不称空缓存冷态）。离线真实batch重放不能替代实时控制闭环。

runner新增--replay必需门禁，要求重放pass/refine5且hash匹配当前libtorch_cuda，旧8项gate作为基线保留。smoke11-real-loop已启动原route16实时闭环，服务器图形v2候选，路线/默认控制/背景交通120不变。尚须最终结果验收。


## 2026-10-09T21:51:07 最终交付验收

用户最终选择的≥200次短闭环已通过：203次连续实时完整推理、234次合法控制、六级全部finite、移动27.304m、路线2.339751%，原评测器return0、无server_abort。最终smoke13-cleanup-final/smoke-acceptance.json pass=true；原整路线run/results状态未完成保留。详见FINAL_ENVIRONMENT_REPORT.md与final-delivery-summary.json。资产完成、CARLA/推理通过、短smoke通过分别记录；未训练、未完整Town05 Long。交接统筹，不再扩大运行。
