# 测试与验证

[项目文章](../README.md) · [开发问题](engineering-notes.md)

验证日期：2026-10-18。测试按“确定性逻辑、图控制流、传输协议、外部集成”分层组织，避免把一次语法检查当成业务验证。

## 1. 当前测试环境

| 组件 | 版本 |
| --- | --- |
| Python | 3.11.7 |
| Node.js | 24.15.0 |
| LangGraph | 1.2.11 |
| LangChain | 1.4.1 |
| langchain-community | 0.4.2 |
| langchain-openrouter | 0.2.9 |
| Pydantic | 2.12.5 |
| LangGraph CLI | 0.4.36 |

这些是离线验证环境，并非所有依赖组合的兼容矩阵。完整部署通过后应冻结对应依赖与镜像版本。

## 2. Python：11 项离线测试

安装 app 后，在 app 目录执行：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

| 领域 | 覆盖行为 | 对应测试文件 |
| --- | --- | --- |
| 图结构 | 四张实际图可导入和组装 | test_graph_offline.py |
| 路由 | 四类意图映射正确分支 | test_graph_offline.py |
| 状态通道 | reserve 属于内部 channel，不在主图顶层输出中 | test_graph_offline.py |
| 人工等待 | 三个实际预约采集节点依次中断并恢复 | test_graph_offline.py |
| 分次补充 | 先补城市仍等待预算，之后 0 下界保留 | test_graph_offline.py |
| 工具存储 | 两次实际模拟预约写入同一记录的两个摘要 | test_graph_offline.py |
| 数据合并 | 空历史、仅预约历史、0、包络、嵌套列表隔离、JSON、namespace | test_preferences.py |

图测试注入假模型，将数据库构造替换为临时内存 SQLite；中断测试使用内存 Checkpoint/Store。因此不需要真实密钥和数据库，也不会据此得出模型推荐质量结论。

## 3. JavaScript：112 个 SSE 检查

```powershell
node tests/sse.test.cjs
```

覆盖每个字节切分位置、逐字节输入、UTF-8 中文、CRLF/LF/CR、子图事件名、多行 data、心跳与不完整尾帧。前端 JavaScript 另外执行语法检查。

## 4. 文档与配置检查

- 检查相对路径、标题链接与代码入口是否对应。
- 检查 JSON/TOML/YAML 与 Python 语法。
- 渲染检查架构 SVG 的中文和布局。
- 公开 `.env` 不含真实 API Key、密码或带真实口令的 URI。
- `.env.local`、运行缓存与 Python 字节码不打包。
- 数据补充文件保持原样，不做内容处理。

## 5. 集成验证范围

以下仍需要连接实际环境验证：

| 验证对象 | 要观察什么 |
| --- | --- |
| 模型协议 | structured output、tool calling、tool choice、流式事件格式 |
| MySQL 推荐 | 条件符合度、SQL 正确性、结果事实一致性、查询耗时 |
| Docker 运行 | 镜像构建、Agent Server 凭据、PG/Redis 连通与迁移 |
| 前端联调 | 完整找房与预约、中断状态、HTTP 错误、CORS |
| 并发与安全 | 用户授权、幂等、并发更新、SQL 执行限制 |

目前不提供未经测量的准确率、吞吐量或生产可用性指标。最小验收步骤见[运行指南](quickstart.md#7-最小集成验收)。
