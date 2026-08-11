# Contributing

感谢你改进 GPT-Image 2 CLI。这个项目刻意保持轻量：优先提交边界清晰、带测试的小改动，
不要为单一实现引入大型框架或无必要的异步层。

## 开发环境

需要 Python 3.11+ 和 [uv](https://docs.astral.sh/uv/)。

```powershell
git clone https://github.com/Lijinzh/gpt-image-2-cli.git
cd gpt-image-2-cli
uv sync --frozen
uv run pytest
uv run ruff check .
uv build
```

提交前请确认：

- 新行为有对应测试。
- `uv.lock` 与 `pyproject.toml` 保持一致。
- 没有提交 `.env`、CC-Switch 数据库、生成图片、请求元数据或任何真实凭据。
- 错误信息不会输出 API Key 或完整 Authorization Header。

## 模块边界

- `cli.py` 只负责参数解析、命令编排和终端输出。
- `config.py` 负责解析环境变量和只读 CC-Switch 配置。
- `models.py` 负责请求验证和跨模块数据结构。
- `responses.py` 负责兼容响应解析，不执行网络请求。
- `client.py` 负责 HTTP 传输、超时和下载。
- `image_io.py` 负责验证和原子写入图片。

涉及兼容性行为时，请在 Pull Request 中附上目标 API 的响应样例，但必须移除 Key、Token、
Cookie、用户路径及其他隐私信息。
