# 函数与状态索引

[项目目录](../README.md)

源码阅读主线为：[推荐](chapters/01-recommendation.md) → [预约](chapters/02-reservation.md) → [问答](chapters/03-conversation.md) → [主图](chapters/04-main-graph.md)。

## 按代码定位

| 文件/对象 | 用途 | 逐段说明 |
| --- | --- | --- |
| state/recommend.py：RecommendState | 本次查询状态、共享消息与偏好 | [01 §2–3](chapters/01-recommendation.md) |
| node/recommend.py：UserInfo / collect_user_info | 结构化抽取、补问和保存 | [01 §4–5](chapters/01-recommendation.md) |
| list_tables / call_get_schema | 列表与结构调用 | [01 §6–8](chapters/01-recommendation.md) |
| generate_query / check_query | 提案、检查与消息替换 | [01 §9–10](chapters/01-recommendation.md) |
| recommend.py：should_continue | 查询循环与终止 | [01 §11](chapters/01-recommendation.md) |
| state/reserve.py / get_title / get_phone / get_id | 顺序采集与检查点 | [02 §2–4](chapters/02-reservation.md) |
| add_reserve_message / call_orders | 字段到模型输入、工具循环 | [02 §5、9–10](chapters/02-reservation.md) |
| common/store.py / generate_orders | 预约模型、依赖注入、工单保存 | [02 §6–8](chapters/02-reservation.md) |
| extend.py / extend_node | 最小问答与链式建图 | [03](chapters/03-conversation.md) |
| state/main.py / ContextSchema | 主图共享状态与内部通道 | [04 §1–2](chapters/04-main-graph.md) |
| get_store_info / identify_question / router_message | 读取、分类与分支 | [04 §3–4](chapters/04-main-graph.md) |
| get_user_preferences / need_reserve | 记录回答与人工分流 | [04 §5–6](chapters/04-main-graph.md) |
| graph.py | 嵌入子图、主图入口与出口 | [04 §7–10](chapters/04-main-graph.md) |
| static/chat.js / sse.js | API、等待状态与流式解析 | [06](chapters/06-frontend-api.md) |
| pyproject / langgraph.json / Dockerfile / Compose | 安装、注册与部署 | [07](chapters/07-deployment.md) |

## 按语法定位

[语法索引](chapters/05-python-and-framework.md)包括：类型与注入、Optional/None/0、字典默认值、and 短路、条件表达式、生成器、next/any、仅关键字参数、列表拼接、Pydantic 序列化、字符串模板、Literal、链式调用与标识作用域。

复习每个函数时依次问：读取什么、返回什么、是否有副作用、恢复是否会重跑、失败由哪一层处理。
