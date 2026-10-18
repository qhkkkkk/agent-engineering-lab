# 项目与文档约定

## 新增项目

在 `projects/` 下创建独立目录，例如 `02-customer-support-agent/`，复制 [项目模板](templates/project-readme.md)作为起点，并在根 README 增加索引。

```text
02-customer-support-agent/
├── README.md
├── docs/
│   ├── architecture.md
│   ├── implementation.md
│   ├── engineering-notes.md
│   ├── quickstart.md
│   ├── interview.md
│   └── testing.md
├── app/
├── examples/
├── assets/
└── data/
```

## 文档必须说明什么

1. 用户想完成的事情和实际能力范围。
2. 一条完整请求的成功路径、等待点和失败出口。
3. 为什么这样划分模块、状态、模型节点和工具。
4. 实际代码入口、关键输入输出和数据契约。
5. 开发问题的原因、处理机制及验证方法。
6. 可以复制的运行步骤，以及已经执行的测试。

## 提交前检查

- 相对链接有效，流程图与代码一致。
- 不包含真实密钥、私人配置、运行缓存和个人资料。
- 不以离线测试代替集成或性能结论。
- 区分已实现能力与后续计划。
- 保留代码及依赖要求的许可证声明。

不同项目分别维护依赖、端口和配置，不依靠上一个项目的残留环境运行。
