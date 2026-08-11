# Security Policy

## API Key handling

GPT-Image 2 CLI 不内置、上传或共享 API Key。Key 仅在运行时从当前用户的环境变量或本机
CC-Switch 数据库读取，并用于构造发往所选 API 地址的 Authorization Header。

请不要在公开 Issue、Pull Request、日志、截图或生成产物中粘贴真实 Key。如果怀疑 Key
已经泄露，请先在对应供应商处立即撤销或轮换，然后再报告问题。

## Reporting a vulnerability

请优先通过 GitHub 仓库的私密安全报告功能提交可复现信息。报告中使用占位凭据，并说明：

- 受影响版本或提交；
- 重现步骤；
- 可能泄露的数据范围；
- 建议修复方式（如有）。

普通兼容性问题可以使用公开 Issue，但必须先清理 Token、Cookie、请求签名、用户路径和
供应商后台信息。
