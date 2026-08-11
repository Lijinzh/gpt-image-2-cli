# GPT-Image 2 CLI

一个面向 OpenAI 兼容中转站的稳健文生图 CLI。它可以自动读取当前 CC-Switch Codex
供应商，也可以通过环境变量连接任意兼容 API。

项目重点解决旧脚本在大图生成时的几个问题：无法传入横图/竖图尺寸、等待时间太短、
返回大体积 Base64 时缺少校验、只兼容一种响应结构，以及超时后容易误重试并重复计费。

## 特性

- 支持 `1024x1024`、`1536x1024`、`1024x1536`，以及 `square`、`landscape`、
  `portrait` 别名。
- 默认使用 `gpt-image-2`，支持 `quality`、`background` 和一次生成多张图片。
- 自动读取 `~/.cc-switch/cc-switch.db` 中当前 Codex 供应商，不复制、不打印 API Key。
- 也可使用 `GPT_IMAGE_API_BASE` 与 `GPT_IMAGE_API_KEY`，适合 Linux、CI 和其他用户。
- 兼容 `b64_json`、Base64 data URI、HTTP(S) URL、直接图片响应及简单 SSE 响应。
- 生成完成后用 Pillow 验证文件格式和实际像素尺寸，再原子写入目标文件。
- 大图请求默认允许等待 30 分钟，并在等待期间输出心跳。
- 读超时或连接中断后不会自动重试，因为服务端可能已经生成并计费。
- 自动使用 `HTTP_PROXY`、`HTTPS_PROXY` 和系统代理；可用 `--no-proxy` 禁用。

## 安装

需要 Python 3.11+ 和 [uv](https://docs.astral.sh/uv/)。

```powershell
cd C:\Users\admin\Desktop\SomethingElse\gpt-image-2-cli
uv tool install .
gpt-image --version
```

开发模式：

```powershell
uv sync
uv run gpt-image --version
```

## 使用 CC-Switch

先执行不计费检查：

```powershell
gpt-image doctor
gpt-image generate "一辆未来感电动跑车，摄影棚产品照" `
  --size landscape --quality high `
  -o .\artifacts\car.png --dry-run
```

确认后生成横向大图：

```powershell
gpt-image generate "一辆未来感电动跑车，摄影棚产品照" `
  --size 1536x1024 --quality high `
  -o .\artifacts\car.png
```

竖图：

```powershell
gpt-image generate "雨夜中的未来城市街道，电影感构图" `
  --size portrait --quality high `
  -o .\artifacts\city.png
```

从 UTF-8 文件读取长提示词：

```powershell
gpt-image generate --prompt-file .\prompt.txt `
  --size landscape -o .\artifacts\result.png
```

## 不使用 CC-Switch

PowerShell：

```powershell
$env:GPT_IMAGE_API_BASE = "https://relay.example/v1"
$env:GPT_IMAGE_API_KEY = "your-key"
$env:GPT_IMAGE_MODEL = "gpt-image-2"
gpt-image doctor
```

Bash：

```bash
export GPT_IMAGE_API_BASE="https://relay.example/v1"
export GPT_IMAGE_API_KEY="your-key"
export GPT_IMAGE_MODEL="gpt-image-2"
gpt-image doctor
```

为了避免密钥进入 shell 历史，CLI 不提供 `--api-key` 参数。

## 可靠性说明

“请求稳定”和“服务端永不失败”不是一回事。CLI 会尽量兼容常见响应、延长大图等待时间、
验证落盘文件并给出可诊断错误，但无法保证第三方中转站、上游模型或网络永远可用。

如果 POST 请求已经到达服务端后发生读超时，CLI 会明确提示“可能已经计费”，且不会自动
再次提交。确认供应商后台没有生成记录后，再由使用者决定是否重试。

## 与 Cherry Studio 的兼容依据

实现参考了 Cherry Studio 仓库在提交 `d1ffaa82cec263f7e59d7816f29b078f2da6e1f4`
附近的图像模型配置和兼容补丁，采用了以下行为：

- `gpt-image-2` 的生成尺寸包含 `1024x1024`、`1536x1024` 和 `1024x1536`。
- 对 `gpt-image-*` 兼容路由不主动发送 `response_format`；部分实现会以
  `400 Unknown parameter: 'response_format'` 拒绝它。
- 同时接受 Base64 与 HTTP(S) 图片输出，并在下载完成后统一验证。

本项目是独立的 Python 实现，没有复制 Cherry Studio 的大段源码。

## 测试与构建

```powershell
uv run pytest
uv run ruff check .
uv build
```

## 发布建议

仓库不包含任何中转站密钥，可以直接放入 GitHub 私有仓库。确认名称与许可证后，也可以
发布 GitHub Release、源码包和 wheel；如要发布到 PyPI，建议先确认包名是否可用。
