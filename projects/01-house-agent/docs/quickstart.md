# 运行与部署

[项目文章](../README.md) · [实现详解](implementation.md) · [问题排查](engineering-notes.md)

本文使用 Windows PowerShell。前端和后端是两个进程：前端默认 8080，Docker API 默认映射到 8002。没有远程服务器也可以在本机运行。

## 1. 环境准备

| 组件 | 用途 |
| --- | --- |
| Python 3.11 | 安装依赖、开发模式、静态前端服务 |
| 可用的模型账号 | OpenRouter API，模型需支持结构化输出和工具调用 |
| MySQL | 业务查询数据源 |
| Docker Desktop | 容器化后端；开发模式本身不要求 Docker |
| PostgreSQL / Redis | 独立 Agent Server 的外部运行依赖 |
| Node.js | 可选，只用于 SSE 离线测试 |

数据补充：[bitehouse_prd.sql](../data/bitehouse_prd.sql)。

在仓库根目录打开 PowerShell：

```powershell
Set-Location .\projects\01-house-agent\app
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
Copy-Item .env .env.local
notepad .env.local
```

`.env` 是已脱敏的公开配置，`.env.local` 保存自己的真实值。已有个人配置时不要重复复制覆盖。Git 忽略 `.env.local`，Docker 构建也不将它放进镜像，运行时单独注入。

## 2. 填写个人配置

| 配置项 | 填写内容 |
| --- | --- |
| `OPENAI_API_KEY` | OpenRouter 的真实 API Key，仍使用 OpenAI 兼容接口变量名 |
| `OPENAI_BASE_URL` | 当前为 `https://openrouter.ai/api/v1` |
| `LLM_MODEL` | 当前为 `openai/gpt-4o-mini` |
| `DB_HOST/PORT/USER/PASSWORD/NAME` | 实际 MySQL 连接信息，密码填原始值 |
| `DATABASE_URI` | PostgreSQL URI，把 `REPLACE_ME` 换成实际口令 |
| `REDIS_URI` | Redis URI，把 `REPLACE_ME` 换成实际口令 |
| `LANGSMITH_API_KEY` | 所选 Agent Server 方式要求时，填写具备相应权限的密钥 |
| `LANGSMITH_TRACING` | 公开配置默认 false；需要追踪时自行启用并配置账号 |

URI 内的密码含 `@ / : # %` 等字符时，需要对密码部分 URL 编码。`DB_PASSWORD` 则不预编码，因为代码通过 `URL.create` 构造连接。

模型初始化顺序为：进程环境变量 → `.env.local` → 公开 `.env`。同一配置项不会被后加载文件随意覆盖。

## 3. 方式一：Docker Compose，后端 8002

### 启动依赖

打开 Docker Desktop，等待引擎就绪。查看已有服务：

```powershell
docker ps -a
```

本项目 Compose 只管理 API，不自动创建 MySQL、PostgreSQL、Redis。已有依赖是 Docker 容器时，按实际名字启动。若使用如下命名：

```powershell
docker start postgres-sql redis-6380
```

MySQL 若安装为 Windows 服务，启动对应本机服务；它不会出现在 `docker ps` 中。

### 核对连接方向

```text
API 容器 → host.docker.internal:3306 → Windows MySQL
API 容器 → host.docker.internal:5432 → 已映射 PostgreSQL
API 容器 → host.docker.internal:6380 → 已映射 Redis
```

[compose.yaml](../app/compose.yaml)会将 API 的 `DB_HOST` 覆盖为 `host.docker.internal`。如果数据库在同一 Docker 网络，则改为相应服务名和容器端口，不要照搬宿主机映射。

### 构建并运行

在 `app` 目录执行：

```powershell
.\.venv\Scripts\langgraph.exe dockerfile -c langgraph.json Dockerfile
docker compose up -d --build
docker compose ps
docker compose logs --tail 100 langgraph-api
Invoke-RestMethod http://127.0.0.1:8002/ok
```

服务器要求的账号权限和许可与选用版本有关。基础镜像和依赖需要在集成环境验证后固定，避免浮动版本带来的不可预期升级。

### 修改配置如何生效

| 情况 | 操作 |
| --- | --- |
| 仅改 `.env.local` | `docker compose up -d --force-recreate` |
| 改 Python 或依赖 | `docker compose up -d --build` |
| 改 `langgraph.json` | 重新生成 Dockerfile，再 build/up |
| 改本机前端配置 | 刷新前端页面 |

`docker restart` 使用旧容器创建配置，不等于重新读取新的 env_file。

暂停：`docker compose stop`。恢复：`docker compose start`。移除本文件管理的 API 容器：`docker compose down`。外部数据库不由本 Compose 文件管理。

## 4. 方式二：开发服务器，后端 2024

只需要模型和 MySQL 业务连接即可调试，不要求额外手动配置 PG/Redis：

```powershell
.\.venv\Scripts\langgraph.exe dev --host 127.0.0.1 --port 2024 --no-browser
```

保留窗口，在另一个 PowerShell 窗口检查：

```powershell
Invoke-RestMethod http://127.0.0.1:2024/ok
```

图注册入口为 `house_agent`，其他三个入口用于局部调试。需要 Studio 时使用启动日志提供的连接地址。

退出时在服务窗口按 Ctrl+C。开发运行目录 `.langgraph_api` 不提交 Git，也不等价于独立 Docker 服务的 PostgreSQL 数据。

## 5. 前端：单独启动 8080

在另一个 PowerShell 窗口进入 `app` 目录：

```powershell
notepad .\static\config.js
```

`apiBase` 对应当前后端：

```javascript
window.HOUSE_CONFIG = {
  apiBase: "http://127.0.0.1:8002",
  assistantId: "house_agent",
  userId: "demo-user-001"
};
```

如果使用 dev，将端口改为 2024。随后运行：

```powershell
.\.venv\Scripts\python.exe -m http.server 8080 --bind 127.0.0.1 --directory static
```

浏览器访问 **[http://127.0.0.1:8080/house.html](http://127.0.0.1:8080/house.html)**，点击浮动聊天气泡。

API 根路径返回健康 JSON，不是聊天界面。若 8080 页面正常、API 请求失败，分别检查 config.js、后端日志与浏览器 Network；CORS 与端口拒绝连接属于不同问题。

## 6. 其他启动方式

### 手动运行镜像，后端 8001

```powershell
.\.venv\Scripts\langgraph.exe build -t house-agent-image
docker run --name house-agent-manual --env-file .env.local -e DB_HOST=host.docker.internal -p 127.0.0.1:8001:8000 house-agent-image
```

前台运行保留日志窗口；停止按 Ctrl+C，或另开窗口执行 `docker stop house-agent-manual`。同名容器以后用 `docker start -a house-agent-manual` 启动，run 用来创建新容器。

### CLI 管理 Docker 栈，后端 8003

```powershell
.\.venv\Scripts\langgraph.exe up --port 8003
```

CLI 管理其生成的服务栈。辅助数据库是否新建或复用由当前版本与参数决定，不要假定它自动共享已有偏好。初次调试一次选择一种后端，避免把多个不同运行时的数据混在一起。

## 7. 最小集成验收

1. API 健康响应正常。
2. 发送模糊需求，出现补充条件提示。
3. 补城市和预算，确认恢复原 thread，看到工具结果与推荐回答。
4. 推荐后输入“不需要”，本轮结束。
5. 独立测试预约，使用虚构资料，确认写入后可查询。
6. 新 thread 保持同 user_id，确认偏好能够复用。

健康检查只验证可达性，模型与查询需要沿这条路径进一步验收。前端刷新会新建 thread，当前不自动接回之前的中断。

## 8. 下次开机

采用 Compose 8002 时：

1. 打开 Docker Desktop，启动自己的 MySQL、PostgreSQL 和 Redis。
2. 在 `app` 目录打开 PowerShell：

```powershell
docker compose up -d
docker compose ps
Invoke-RestMethod http://127.0.0.1:8002/ok
.\.venv\Scripts\python.exe -m http.server 8080 --bind 127.0.0.1 --directory static
```

3. 浏览器打开 8080 的 house.html。

代码和配置没改时不必每次重建镜像。PyCharm/VS Code 用于编辑，Apifox 用于测接口，都不是网页必须依赖的运行进程。
