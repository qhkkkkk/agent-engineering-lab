# 06 · 从前端到 Agent Server：Thread、Resume 与 SSE

[语法索引](05-python-and-framework.md) · [总目录](../../README.md) · 下一章：[部署](07-deployment.md)

图对象本身不等于网页。这个项目有静态前端、Agent Server 和业务数据源，先把三者的地址与职责分开，再看接口。

## 1. 最短请求链路

```text
house.html → config.js → chat.js
   → POST /threads
   → POST /threads/{thread_id}/runs/stream
   → TextDecoder → SSEParser
   → 回答 / 工具进度 / 人工提示
```

首页房源卡片是展示样例，聊天才请求后端。打开后端根路径看到健康 JSON 不代表打开前端，真正网页是 8080 的 house.html。

## 2. assistant、thread、run 分别是什么

| 对象/参数 | 作用 | 本项目例子 |
| --- | --- | --- |
| assistant_id | 选择注册图或助手配置 | house_agent |
| thread_id | 保存一段对话及执行状态 | 创建 thread 返回的 UUID |
| run | 在 thread 上执行一次图 | 一次普通输入或恢复执行 |
| context.user_id | 应用层偏好分组 | demo-user-001 |

一个 thread 可以有多次 run。运行完成不是删除 thread；新的 thread 可以共享 Store，但不共享旧的待执行位置。

## 3. 普通输入与恢复请求

普通输入：

```json
{
  "assistant_id": "house_agent",
  "input": {"messages": [{"role": "human", "content": "帮我找房"}]},
  "context": {"user_id": "demo-user-001"},
  "stream_mode": ["updates", "messages"],
  "stream_subgraphs": true
}
```

收到中断提示后，继续向同一 thread 发：

```json
{
  "assistant_id": "house_agent",
  "command": {"resume": "太原，500-1500元/月，小店区"},
  "context": {"user_id": "demo-user-001"},
  "stream_mode": ["updates", "messages"],
  "stream_subgraphs": true
}
```

`messages` 必须是复数模式名，`message` 可能直接导致 422。标准 JSON 不接受中文逗号、注释和尾随逗号。完整可复制请求体见[examples](../../examples/README.md)。

## 4. 前端状态为什么这样分

| 变量 | 解决的问题 |
| --- | --- |
| threadId | 发送到正确对话 |
| creating | 多次触发创建时复用一个尚未完成的 Promise |
| busy | 防止一次运行未结束又重复提交 |
| pendingInterrupt | 下一次输入究竟是新消息还是恢复值 |
| rendered | 同一消息的累积文本更新同一气泡 |
| seen | 父/子图重复事件、重复工具事件去重 |

不能从“最后一个 DOM 气泡的 ID”推断业务状态，否则新增错误气泡或进度气泡就可能改变恢复逻辑。

刷新后的 thread 恢复与正在运行的并发提交不是同一问题。当前刷新创建新 thread；更完整客户端应保存 thread ID，并向服务端查询是否仍有 pending interrupt。

## 5. updates、messages、子图事件怎样使用

updates 表达节点状态更新，可观察工具调用与人工中断；messages 表达模型消息流，具体事件包装随服务端协议版本而异。`stream_subgraphs=true` 让客户端收到更细的子图信息。

展示时应过滤回答节点：需求抽取、路由等内部结构化结果不应直接变成面向用户的答案。最终完整 updates 还能作为部分流格式变化时的文本兜底。

工具执行进度说明“执行了什么工具”，不等于展示模型内部推理。接口能流式返回也不代表每个业务阶段都拥有自定义进度事件。

## 6. SSE 帧与网络块为什么必须分层

服务端一条事件可能是：

```text
event: updates|recommended_graph:task
data: {"__interrupt__":[{"id":"demo-interrupt","value":"请补充预算"}]}

```

最后有一个空行才形成完整事件。网络 read 可能把它拆在 event 名、JSON 或中文 UTF-8 字节中间。

解析器分四步：

1. `TextDecoder` 持续解码字节，保留未完成字符。
2. 字符串缓存收集完整行，兼容 CRLF/LF/CR。
3. 保存 event 与多行 data，遇空行形成一帧。
4. JSON.parse 后才交给业务分发。

解析实现：[sse.js](../../app/static/sse.js)。它不直接创建 thread 或操作聊天 DOM，所以可以独立做任意字节切分测试。112 个检查覆盖中文、心跳、多行与尾帧。

## 7. 文本渲染与错误提示

当前使用 textContent 展示用户与模型内容，不把不可信字符串直接作为 HTML 执行。代价是部分 Markdown 符号会原样显示。若加入 Markdown 渲染，应同时引入可靠的 HTML 清洗规则，而不是仅调用解析器。

HTTP 非 2xx、服务端 error 事件、JSON 解析错误和网络中断分属不同层。失败时需要提示当前 API 与 thread 状态，不应一律重建 thread，否则可能丢失待恢复现场。

## 8. 扩展到 custom stream 时怎样设计

后续可在节点中输出“开始读结构、查询完成、等待确认”等结构化进度事件。客户端按事件类型渲染，而不是抓取 print 日志或模型内部文本。

先定义稳定事件结构，例如 type、stage、status 与可公开消息，再接 custom 模式。当前项目主要使用 updates/messages，这项属于后续演进，不能仅因前端有进度框就说已实现全部自定义流协议。
