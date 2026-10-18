# 最小 API 请求：可复制到 Apifox

[返回文章](../README.md) · [启动手册](../docs/quickstart.md)

先保证后端已经启动。这里以 `http://127.0.0.1:8002` 为例，2024/8001/8003 模式应替换端口。请求均使用 `Content-Type: application/json`。

## 1. 创建 thread

```http
POST http://127.0.0.1:8002/threads
Content-Type: application/json

{}
```

记下响应中的 `thread_id`。下面 URL 中的 `{thread_id}` 是占位符，要换成这个真实值。

## 2. 普通运行

```http
POST http://127.0.0.1:8002/threads/{thread_id}/runs/stream
Content-Type: application/json
```

Body 使用 [02-run.json](02-run.json)。它故意不给城市和预算，便于观察中断。服务端以 SSE 返回事件，不是一次普通 JSON 回包。

若该演示用户已经有历史预算，缺失项可能比第一次少；换全新的演示 user_id 可观察首次使用路径。

## 3. 恢复需求中断

URL 仍是**同一个 thread** 的 runs/stream。Body 改成 [03-resume-budget.json](03-resume-budget.json)。不要把它当普通消息放进 `input.messages`。

## 4. 推荐结束，拒绝继续预约

如果收到“是否需要预约”的新中断，继续用同一 URL，Body 改成 [04-resume-no-booking.json](04-resume-no-booking.json)。

直接预约的普通请求见 [05-run-reservation.json](05-run-reservation.json)，建议新建一个 thread 测试。之后收到标题、电话、身份证提示时，每次将对应虚构值放进 `command.resume`。

## 看哪些事件

| 内容 | 看什么 |
| --- | --- |
| `metadata` | 运行标识等元数据 |
| `updates` 或带子图命名空间的 updates | 节点更新、工具请求/结果、中断 |
| `__interrupt__` | 提示值与中断 ID；重复父/子图事件需要去重 |
| `messages/...` | 目标回答节点的流式消息 |
| `error` | 服务端执行错误；同时看后端日志 |

`messages` 必须是复数；`stream_subgraphs: true` 请求包含子图事件。同一输入的实际回复文字、工具次数和房源内容依赖模型与数据，不提供虚构的固定输出结果。
