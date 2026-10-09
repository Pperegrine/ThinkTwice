# 环境交付的版本控制边界

2026-10-09 本地整理：保留原模型/agent/控制源码及 Git 历史，新增环境文档、全部小型工具脚本、Torch NVRTC 与 Mesa 源码补丁。启动脚本的门禁 JSON 一并保留；历史诊断状态以 FINAL_ENVIRONMENT_REPORT.md 和最终短测摘要为准。

`evidence/` 使用显式文件允许列表：提交小型 JSON（小于 64 KiB）、源码 diff、最终包清单及必要 CUDA/链接身份文本。原始日志、strace、PTX/ELF 长转储、旧报告备份和大型安装输出保留在磁盘但忽略。新增需要发布的证据须先审核，再修改允许列表。脚本中公开下载服务的临时 token 在运行时获取，没有提交凭据值。

`evidence/20261009-smoke13-summary/` 是从外层 `.thinktwice-runtime/runs/20261009-smoke13-cleanup-final/` 原样复制的小型最终验收 JSON；原始运行目录不移动。包括原 results/run 和独立短测 acceptance，明确保留“短测通过、整路线未完成”的区别。该目录的来源清单记录复制前后哈希。

`evidence/20261009-smoke-v5/` 原样保存现有覆盖层的 evaluator diff、观察插桩 diff、manifest 和原单路线 XML；生成脚本在 `scripts/prepare_smoke_overlay.py`。运行时生成的覆盖层仍在外层忽略目录。没有将依赖二进制、模型权重或真实传感器输入纳入提交。

当前运行环境位于独立 WSL `/opt/thinktwice`；代码仓库不是环境镜像。恢复须结合 FINAL_ENVIRONMENT_REPORT.md、最终库身份及外部资产备份，保留当前旧栈 ABI、补丁和候选目录隔离。脚本中的专用发行版名称、绝对路径及历史 evidence 路径需要按目标机审阅。本次仅本地提交，未运行任何脚本、构建或评测。
