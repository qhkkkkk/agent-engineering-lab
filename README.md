# Agent Engineering Lab

**从一行代码读到一套业务流程：Agent 项目、架构取舍与开发复盘。**

这里按项目组织 Agent 工程实践。每个项目保留完整源码，并从子图开始逐层拆解状态、节点、工具、人工输入和主图编排；既能快速了解项目，也能沿代码反复复习。

**[在线复习台](https://qhkkkkk.github.io/agent-engineering-lab/) · [项目目录](projects/README.md) · [新增项目模板](templates/project-readme.md)**

## 项目目录

| 项目 | 业务链路 | 核心技术 | 入口 |
| --- | --- | --- | --- |
| **01 · 智能租房助手** | 找房 → 补充需求 → SQL 查询 → 预约 → 跨会话偏好 | LangGraph、Text-to-SQL、interrupt/resume、Store、SSE、Docker | [5 分钟总览](projects/01-house-agent/README.md) · [从推荐子图开始读代码](projects/01-house-agent/docs/chapters/01-recommendation.md) |

## 两条阅读路线

| 阅读目的 | 路线 |
| --- | --- |
| 快速了解项目 | [业务与能力](projects/01-house-agent/README.md) → [系统设计](projects/01-house-agent/docs/architecture.md) → [技术追问](projects/01-house-agent/docs/interview.md) |
| 深入源码与复习 | [推荐子图](projects/01-house-agent/docs/chapters/01-recommendation.md) → [预约子图](projects/01-house-agent/docs/chapters/02-reservation.md) → [问答子图](projects/01-house-agent/docs/chapters/03-conversation.md) → [主图](projects/01-house-agent/docs/chapters/04-main-graph.md) → [语法索引](projects/01-house-agent/docs/chapters/05-python-and-framework.md) |

教程对每个关键节点回答五个问题：**读取什么、返回什么、为何这样写、复杂语法如何展开、失败或重放会怎样。** 章节包含真实源码链接、状态变化表和折叠自测题。

## 可以从中看到什么

- 以业务约束决定图结构，把确定性步骤与模型决策分开。
- 区分 State、Context、Checkpoint、Store 的生命周期。
- 维护 AI 工具请求与 ToolMessage 的消息协议。
- 为缺失需求和分步预约提供可恢复的人机交互。
- 从数据序列化、SSE 分块到容器网络逐层定位问题。

## 仓库布局

```text
agent-engineering-lab/
├── README.md
├── docs/index.html                    # 可交互的复习导航，无模型依赖
├── CONTRIBUTING.md
├── templates/project-readme.md
└── projects/
    ├── README.md                     # 后续实战的统一目录
    └── 01-house-agent/
        ├── README.md                 # 项目展示与阅读入口
        ├── docs/chapters/            # 推荐 → 预约 → 问答 → 主图
        ├── docs/                     # 运行、测试、问题复盘
        ├── app/                      # 应用代码与脱敏 .env
        ├── examples/                 # API 请求体
        ├── assets/                   # 架构图与复习台预览
        └── data/                     # 数据补充
```

新增实战使用 `projects/02-.../`，各自维护依赖与配置。项目当前以单用户演示和离线回归为基础，真实交易、认证、模型/数据库完整联调的范围写在各项目文档中。
