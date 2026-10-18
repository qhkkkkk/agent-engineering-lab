# 项目讲解与技术追问

[项目文章](../README.md) · [架构](architecture.md) · [实现](implementation.md)

## 1. 90 秒项目介绍

这个项目是一个基于 LangGraph 的智能租房助手，围绕推荐、追问、预约和偏好查询组织完整对话流程。

架构上，主图先加载用户偏好，再识别意图并分流。推荐子图通过结构化输出提取需求，缺条件时中断等待用户，条件完整后按取结构、生成 SQL、检查、执行的流程查询。预约子图顺序采集字段，再通过工具生成模拟工单和保存摘要。

项目重点在状态管理：Checkpoint 负责原 thread 的暂停恢复，Store 负责新会话复用用户偏好；消息更新则通过 reducer 维护工具请求与结果配对。前端采用 REST/SSE，需要正确处理跨网络数据块的事件解析。

当前已覆盖控制流与存储合并的离线测试，真实订单、认证与 SQL 强约束是下一阶段工程化方向。

这段介绍只描述现有代码。没有实测的线上规模、准确率或性能数据，不应添加到介绍中。

## 2. 三个值得展开讲的技术点

### 技术点一：可恢复的人机交互

讲清楚“缺信息 → interrupt → Checkpoint → 同 thread resume → 节点重放”的全过程，并能解释为何不能在中断前随意放订单等副作用。

对应代码：`collect_user_info`、`get_title/get_phone/get_id`、前端 `pendingInterrupt`。

### 技术点二：SQL 工具循环中的消息一致性

不仅讲“用了 SQL Agent”，还要讲工具调用如何执行，为什么检查节点替换旧 AIMessage，以及消息 ID 与调用 ID 的区别。

对应代码：`generate_query`、`check_query`、`run_query_node`、MessagesState。

### 技术点三：长期记忆的数据契约

讲清 namespace、key、value，为什么新增和更新使用不同 key 规则，为什么 Pydantic 对象要先变成 JSON 值，以及为什么区间包络不同于最新偏好。

对应代码：`get_store_info`、`generate_orders`、`preferences.py`。

## 3. 高频追问

<details>
<summary>为什么不用一个大提示词把全部流程做完？</summary>

单次生成很难保证必要字段补齐、工具执行顺序与可恢复等待。图把确定性约束写到代码，模型保留语言理解和局部决策空间。代价是维护 State 与拓扑，因此需要按业务复杂度选择，而不是所有场景都使用图。
</details>

<details>
<summary>子图是不是多个独立 Agent？</summary>

子图首先是流程模块。它可以包含普通函数、人工输入、模型节点和工具执行，不能由“拆成子图”自动推导为多智能体协作。
</details>

<details>
<summary>State、Context、Checkpoint、Store 有什么区别？</summary>

State 承载节点交换数据；Context 提供本次运行参数；Checkpoint 保存 thread 的状态和执行位置；Store 保存跨 thread 的用户信息。长期记忆与恢复执行不应共用一个模糊的“上下文”概念。
</details>

<details>
<summary>同一用户新开对话，能接着之前中断的预约吗？</summary>

新 thread 可通过同 user_id 读取长期偏好，但不能自动恢复旧 thread 的待执行位置。要接着原预约，应使用原 thread，并确认它的 pending interrupt 状态。
</details>

<details>
<summary>为什么节点只返回一条消息，历史还在？</summary>

messages 的 add_messages reducer 按 ID 合并，新 ID 追加、同 ID 更新。节点返回的是局部更新，并不是完整新状态；普通 list 字段也不自动获得这种语义。
</details>

<details>
<summary>SQL 检查后为何修改 response.id？</summary>

用相同消息 ID 替换尚未执行的 AI 请求，避免旧工具调用悬空。ToolMessage 仍用实际调用 ID 配对，两种 ID 的角色不同。
</details>

<details>
<summary>为什么要有 check_query，能保证安全吗？</summary>

它提供一个固定复核位置，能减少部分语法或语义错误，但依然是模型判断。真正的执行权限、超时和语句限制必须由数据库及确定性机制约束。
</details>

<details>
<summary>interrupt 恢复是从暂停那一行接着运行吗？</summary>

节点会从头重放，框架在对应 interrupt 处提供恢复值。因此中断前代码可能重复执行，多次 interrupt 的顺序需要稳定，外部动作需要幂等。
</details>

<details>
<summary>预约成功是不是代表房子已经锁定？</summary>

当前生成的是模拟工单并保存摘要，没有真实库存锁、支付或合同。接入交易时，需要房源唯一标识、状态校验、业务事务和幂等键。
</details>

<details>
<summary>为什么有 Store 还不能保证用户数据隔离？</summary>

namespace 只负责分组。客户端任意指定 user_id 时仍可越权，必须由服务端认证并绑定身份，同时限制 thread 与 Store 的访问范围。
</details>

<details>
<summary>TypedDict 的私有状态能保护隐私吗？</summary>

不能。内部通道与输出 schema 属于数据契约，流式更新和追踪仍可能包含该数据；权限控制和敏感字段生命周期需要独立设计。
</details>

<details>
<summary>前端为什么不用每次 read 后直接 JSON.parse？</summary>

read 返回任意字节块，可能拆开 UTF-8 字符与 SSE 事件。先流式解码，再缓冲到完整帧，最后解析 JSON；测试要覆盖任意切分位置。
</details>

<details>
<summary>现有测试能证明什么？</summary>

能证明指定版本下的图组装、路由、中断控制和数据合并，以及解析器的分块行为。不能证明真实模型抽取准确率、MySQL 查询质量、Docker 部署或生产性能。
</details>

## 4. 如果继续投入两周，优先做什么

| 顺序 | 任务 | 理由 |
| --- | --- | --- |
| 1 | 完成真实模型/数据库集成用例，冻结运行版本 | 先明确可用基线 |
| 2 | 数据库最小权限、查询超时和结果上限 | 约束模型生成查询的影响 |
| 3 | 认证与用户授权 | 防止通过标识篡改读取其他用户数据 |
| 4 | 订单服务与幂等 | 将模拟工单推进为可靠业务动作 |
| 5 | 抽取和等待拆节点、Store 并发控制 | 降低重放与并发导致的不一致 |

## 5. 讲解前的自查

- 能在代码中指出每个核心能力的入口。
- 能描述一次成功路径，也能描述等待、失败和退出。
- 能解释至少一个替代方案与取舍，而不只是列技术名。
- 区分当前实现、测试结论与后续计划。
- 所有演示使用虚构个人资料。
