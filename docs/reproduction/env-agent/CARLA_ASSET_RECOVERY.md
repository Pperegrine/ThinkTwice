# CARLA 官方资产获取恢复 — 2026-10-09

用户已手动取得项目根 `thinktwice.pth`（515776025 B）。本地SHA256：`6c86b4ad020cb4b5b67d77929d884a878172a5dc56bd8103ff614f68a828d1b5`。ZIP容器可读，1346项；未运行torch.load，尚未验证官方checkpoint关键键/shape，本地hash不等于官方发布hash。

项目根 `carla-0.9.10.zip`（91657994 B）是源码归档，根目录carla-0.9.10，1922项，无服务端shipping binary和.pak地图资源。版本也并非任务固定0.9.10.1。SHA256：`1c40408aedb93c1ca827d119c48730dc6ca6a4b5f76c468a66837c2b899a09b7`。保留文件，未解包/删除。

## 官方替代渠道

CARLA官方文档认可 `carlasim/carla` Docker分发；Docker Hub有 `0.9.10.1` Linux/amd64镜像。[官方Docker说明](https://carla.readthedocs.io/en/0.9.10/build_docker/)，[官方镜像tag清单](https://hub.docker.com/r/carlasim/carla/tags)。不从源码启动UE构建：官方0.9.10构建文档需要UE4.24和独立大资产包，并不能免去资源下载。

Windows和WSL直接访问auth.docker.io均TCP超时。只读查询Windows现有代理配置后，对本次请求显式使用已有 `127.0.0.1:7892`，取得registry manifest成功；没有改全局代理，也未安装Docker Desktop或修改系统/旧WSL。

镜像manifest digest：`sha256:7e715f034941db7b9b11242f3bb3a392b5ed7571614b8acb3b179d712d49451b`。21个层压缩合计4241242034 B（3.9500GiB），另config13730 B。最后CARLA内容层3953272065 B。manifest/headers/config/逐层下载记录位于 `evidence/20261009-carla-assets/`。

下载前D盘剩191507525632 B（178.36GiB）；下载目录项目`.thinktwice-runtime/assets/carla-0.9.10.1-image`；提取目标新WSL `/opt/thinktwice/carla-0.9.10.1`。下载脚本逐层验证官方manifest给出的大小和SHA256，partial单独保存，失败可恢复，不信任未校验文件。

执行：Windows `scripts/fetch_carla_image.py`（只对本次curl显式代理）；完成后Linux `scripts/extract_carla_image.py`，仅提取镜像`home/carla`范围，不运行容器，不写系统根。路径、链接和归档项检查后再提取。提取后的地图/API/依赖还需检查；镜像下载成功不等于CARLA服务端/同步/闭环验收通过。

当前状态：官方镜像层下载中。只恢复本次CARLA资产获取；上一轮完整环境编译仍暂停，旧torch CUDA问题未修复。

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

## 2026-10-09 19:10 CARLA实际运行验收通过

证据：evidence/20261009-carla-release/run10-ue4-compat/{run.json,sync-probe.json,server-console.log}。run/pass=true，probe/pass=true；原egg文件名carla-0.9.10-py3.7-linux-x86_64.egg。客户端/服务端版本均784d9b9f；Town05加载，synchronous_mode=true、fixed_delta_seconds=0.05，连续10tick frame9→18且snapshot frame一致，仿真步长0.05000000074505806秒；末两tick wall约0.16秒。恢复原world设置后主动终止本次进程组；returncode=-15/控制台143属于本次清理，非运行验收失败。无传感器或模型推理结论。

部署局部修复：专用WSL用户ttenv；Mesa24.0.5+/opt/thinktwice/mesa24独立前缀，实际RTX5080加速OpenGL4.6，GLX4.3/4.6上下文通过，详glx-context-mesa24-swrast.json及glxinfo-mesa24.txt。WSLg需swrast DRI入口，实际GALLIUM_DRIVER=d3d12；不代表软件渲染。原系统Mesa21.2.6保留。

原始失败run01/02返回1；独立Mesa但DISPLAY空run03返回139；DISPLAY=:0后RPC可连接，但run06 Town05渲染shader链接失败，随后get_settings超时。通过单独源码gl_link_diagnostic.c诊断（run09）获取精确原错误：vertex shader output out_TEXCOORD0 specifies noperspective interpolation qualifier, but fragment shader input specifies no interpolation qualifier。Mesa24原版00-mesa-defaults.conf已为UE4Editor等应用配置allow_glsl_cross_stage_interpolation_mismatch=true；仅对CARLA进程设此同一选项后run10通过。未改shader源码、默认渲染质量、模型数学/结构/5轮refinement或控制。正式run10无LD_PRELOAD诊断插桩。

原ImportAssets.sh实际导入完成：import-official/official-import.json pass=true，原脚本tar --keep-newer-files，检查无需恢复较新本体资产（0项），Import中压缩包保留。额外libpng16-16/libjpeg-turbo8/libtiff5根据原egg的ldd缺项补齐，原egg已注册专用conda carla.pth，未改名。

重复执行CARLA验收：wsl -d ThinkTwice-Focal -u ttenv，工作目录项目根，使用run10/run.json中的环境变量运行scripts/run_carla_acceptance.py --display :0 --output-dir <新证据目录>。启动包装脚本scripts/launch_carla_wsl.sh仅设置CARLA自身图形环境，不向推理Python全局注入Mesa。原evaluator硬编码DISPLAY空，后续单路线启动需独立部署overlay并记录diff，原agent/控制不改。

当前三项状态：资产获取/解压/导入完成；CARLA运行通过；ThinkTwice闭环未通过。旧torch源码候选wheel仍编译中，MMCV1.7.0候选wheel已含PTX；不能把wheel构建或CPUimport计为CUDA算子通过。


## 2026-10-09T21:51:07 最终交付验收

用户最终选择的≥200次短闭环已通过：203次连续实时完整推理、234次合法控制、六级全部finite、移动27.304m、路线2.339751%，原评测器return0、无server_abort。最终smoke13-cleanup-final/smoke-acceptance.json pass=true；原整路线run/results状态未完成保留。详见FINAL_ENVIRONMENT_REPORT.md与final-delivery-summary.json。资产完成、CARLA/推理通过、短smoke通过分别记录；未训练、未完整Town05 Long。交接统筹，不再扩大运行。
