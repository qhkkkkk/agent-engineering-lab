# House Agent

基于 LangGraph 的租房助手：自然语言推荐、人工补充需求、交互式预约、用户偏好记忆。

| 入口 | 链接 |
| --- | --- |
| 完整项目文章 | [README](../README.md) |
| 架构取舍 | [architecture](../docs/architecture.md) |
| 代码详解 | [implementation](../docs/implementation.md) |
| 运行部署 | [quickstart](../docs/quickstart.md) |
| 测试 | [testing](../docs/testing.md) |

公开 [.env](.env) 已清空真实凭据。首次使用复制为 `.env.local` 后填写个人配置；该文件不提交 Git、不进入镜像构建。

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
Copy-Item .env .env.local
```

预约当前生成模拟工单。代码许可证声明见 [LICENSE](LICENSE)。
