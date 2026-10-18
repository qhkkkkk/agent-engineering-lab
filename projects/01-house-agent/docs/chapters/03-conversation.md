# 03 · 问答子图：用最小流程看清消息与链式构建

上一章：[预约子图](02-reservation.md) · [总目录](../../README.md) · 下一章：[主图](04-main-graph.md)

这个子图只有一个模型节点，但保留它有两个价值：承接非找房/预约问题，并作为理解完整图结构的最小对照。

## 1. 为什么 State 只用 MessagesState

普通问答只需要对话历史。没有必要为了与推荐图“看起来统一”而加入城市、预算和预约字段。状态设计应由跨步骤需要的数据决定。

问答分支目前没有文档检索或向量库；它是简单聊天，不应称为 RAG。

## 2. 先看节点

[查看实际代码：src/agent/node/extend.py](../../app/src/agent/node/extend.py#L7)

```python
def extend_node(state: MessagesState):
    return {
        "messages": [model.invoke(
        [SystemMessage(content="你是一个乐于助人的助手，可以根据历史对话进行问题的回复")]
        + state["messages"]
    )]
    }
```

`SystemMessage` 定义当前回答角色，`state['messages']` 提供历史。两者通过列表拼接形成模型输入；`.invoke()` 返回 AIMessage，节点只返回 messages 的局部更新。

为什么把系统提示放在函数里组装，而不是持续写入历史？它是本次调用的行为约束，不必每次追加一条相同系统消息到 State，使历史重复增长。

如果 node 直接返回 response 而不是 `{'messages':[response]}`，它就没有按 StateGraph 的字典更新契约说明要更新哪个 channel。

## 3. 再看链式建图

[查看实际代码：src/agent/extend.py](../../app/src/agent/extend.py#L1)

```python
from langgraph.constants import START
from langgraph.graph import StateGraph, MessagesState

from agent.node.extend import extend_node

extend_graph = (
    StateGraph(MessagesState)
    .add_node(extend_node)
    .add_edge(START, "extend_node")
    .compile()
)
```

这段链式调用与下面的展开形式意义相同：

```python
builder = StateGraph(MessagesState)
builder.add_node(extend_node)
builder.add_edge(START, "extend_node")
extend_graph = builder.compile()
```

链式写法之所以能继续 `.add_edge()`，是因为这些构建方法返回 builder 本身；最外层圆括号允许跨行续写。它不是把多个函数同时并行执行。

没有出边的末端节点执行完后，这个子图自然完成。主图将它作为一个节点使用后，还会接到主图的 END。`compile()` 生成可执行图对象，本身不会自动调用模型。

## 4. 子图完成与主图完成有何区别

```text
问答子图：START → extend_node → 子图完成
主图路径：意图识别 → extend_graph → 主图 END
```

同理，推荐子图完成后，主图可以继续进入 need_reserve。子图局部终点与完整业务终点不必相同。

## 5. 扩展时应该加在哪里

如果以后要回答租房政策，可以在这个分支增加“检索 → 相关性判断 → 回答”，但要同时加入检索数据与失败出口；不能只换一段系统提示，就宣布已拥有可靠知识库。

当前一个共享模型能服务不同节点，但不同节点的系统提示、结构化输出和绑定工具不同，任务角色因此不同；这也不意味着部署了多个独立模型实例。

<details><summary>为什么不能把所有字段都放进一个统一 State？</summary>

不相关字段让依赖关系变模糊，也增加错误读取与输出混杂。子图用最小必要状态，主图通过共享字段连接它们。
</details>
