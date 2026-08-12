# AGENTS.md

本文件适用于整个仓库。修改子目录中的代码、测试、文档或工作流时，都应遵守以下约定。

## 项目目标

GPT-Image 2 CLI 是一个 Python 3.11+ 命令行工具，通过 OpenAI 兼容 API 和
CC-Switch 调用 GPT-Image 模型。项目保持轻量、可审计，并支持 Linux、macOS 和 Windows。

优先完成边界清晰的小改动。不要为单一需求引入服务层、依赖注入框架、插件系统或不必要的
异步抽象。

## 开发命令

依赖和命令统一通过仓库锁定的 `uv` 环境运行：

```powershell
uv sync --frozen
uv run --frozen pytest
uv run --frozen ruff check .
uv build
uv run --frozen python -m gpt_image_cli --help
```

提交代码前，至少运行与改动直接相关的测试。影响 CLI、打包、更新器或发布流程时，应运行上面
的完整测试、Ruff 和构建命令。

## 代码边界

- `src/gpt_image_cli/cli.py`：参数解析、命令编排和终端输出。
- `src/gpt_image_cli/config.py`：环境变量和只读 CC-Switch 配置解析。
- `src/gpt_image_cli/models.py`：请求验证和跨模块数据结构。
- `src/gpt_image_cli/client.py`：HTTP 请求、超时、代理和下载传输。
- `src/gpt_image_cli/responses.py`：兼容不同 API 响应格式。
- `src/gpt_image_cli/image_io.py`：图片验证和原子写入。
- `src/gpt_image_cli/updater.py`：版本检查、Release 校验和延迟自更新。
- `tests/`：行为测试；新增或修复行为时同步补充测试。
- `docs/`：GitHub Pages 静态站点和公开文档。
- `scripts/`：构建、Release 清单、镜像同步及公开渠道验证脚本。

不要把网络传输、文件写入或配置探测重新塞进 `cli.py`。优先扩展现有聚焦模块，而不是建立
新的通用抽象层。

## CLI 与跨平台要求

- 所有用户功能都要考虑 Linux、macOS 和 Windows。
- 不依赖 Bash、PowerShell 或特定平台路径，除非代码明确按平台分支。
- 用户输出保持简洁；`--json` 输出必须是稳定、可解析的 JSON，不能混入提示文本。
- 不破坏现有命令、参数、退出码和环境变量，除非需求明确要求不兼容变更。
- 生成图片和状态文件时使用安全写入方式，不覆盖无关用户文件。

## 自动更新规则

- 更新包只能来自配置允许的 GitHub、Gitee 或 GitCode Release。
- 安装前必须校验仓库、版本、标签、文件名、文件大小和 SHA-256。
- 不得在 CLI 仍运行时直接替换当前 `uv tool` 环境。更新应在当前命令退出后由独立助手安装。
- Windows 后台助手必须隐藏运行，并验证 Linux/macOS 的等价流程。
- 非 `uv tool` 安装不得擅自覆盖，应提示用户通过原包管理器更新。
- `--json`、CI 或非交互调用不能产生额外自动更新提示或破坏机器可读输出。

## 安全与隐私

- 不读取、提交或输出真实 API Key、Token、Cookie、Authorization Header、CC-Switch 数据库、
  `.env`、用户请求元数据或生成图片。
- 示例只能使用明显的假凭据；真实配置只通过环境变量或用户本机只读配置获得。
- 错误信息和调试日志必须清理凭据与敏感路径。
- 修改代理、下载或更新代码时，保留 HTTPS、来源限制和摘要验证，不增加跳过校验的后门参数。

## 版本与发布

- `pyproject.toml` 与 `src/gpt_image_cli/__init__.py` 的版本必须一致。
- `uv.lock` 必须与 `pyproject.toml` 同步。
- 版本 `X.Y.Z` 对应标签 `vX.Y.Z`。
- `latest.json` 必须由 `scripts/build_release_manifest.py` 生成，不得手工填写大小或摘要。
- 发布后验证 GitHub Release 的 wheel、`latest.json`、文件大小和 SHA-256；配置了凭据时，还要
  验证 Gitee 与 GitCode 镜像资产完全一致。
- 本地构建成功不代表发布成功；必须检查 GitHub Actions 的完整 Linux、macOS、Windows 矩阵
  和公开 Release 资产。

## Git 工作方式

- 保留用户已有和无关的工作区改动，不使用破坏性重置或强制推送。
- 暂存时明确列出属于当前任务的文件，避免默认 `git add -A`。
- 默认分支开发使用 `codex/<description>` 分支。
- 推送或发布前先获取远端状态；双向同步后验证本地 HEAD、`origin/main`、标签和工作区状态。
- 提交信息保持简短，描述实际结果。

## 文档

- 面向用户的公开文档以简体中文优先，命令、参数名和代码标识保持原样。
- CLI 行为、安装方式、环境变量或更新机制变化时，同步更新 `README.md`、示例和相关测试。
- 不在文档中承诺未经公开渠道或真实环境验证的能力。
