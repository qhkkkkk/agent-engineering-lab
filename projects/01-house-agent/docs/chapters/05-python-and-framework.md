# 05 · 语法与框架写法索引：看懂代码中的“压缩表达”

[主图](04-main-graph.md) · [总目录](../../README.md) · 下一章：[前端与接口](06-frontend-api.md)

这章把容易卡住的表达式拆成普通 Python 操作。每一种写法先区分“Python 语法”与“框架赋予的行为”，不要把注解、调用、容器和依赖注入混为一谈。

## 1. 四种看起来都带括号的写法

| 代码 | 属于什么 | 在本项目的含义 |
| --- | --- | --- |
| `Runtime[ContextSchema]` | 泛型类型注解 | 运行上下文符合该 schema 的静态描述 |
| `Annotated[Any, InjectedStore()]` | 类型注解 + 元数据对象 | 框架识别需要注入 Store |
| `state['messages']` | 字典键访问 | 从当前 State 取消息列表 |
| `state['messages'][-1]` | 列表索引 | 再取列表最后一项 |
| `model.invoke([...])` | 方法调用 | 真正请求模型 |
| `ToolNode([tool])` | 构造对象 | 用工具列表创建执行节点 |

先看括号左边是谁：类型、字典、列表、函数还是对象方法。仅凭方括号不能判断行为。

## 2. TypedDict、BaseModel、MessagesState 分工

| 写法 | 适用位置 | 不要误解为 |
| --- | --- | --- |
| `class ContextSchema(TypedDict)` | 描述上下文键与类型 | 自动登录或运行时强校验 |
| `class UserInfo(BaseModel)` | 模型输出的解析/验证/序列化 | 所有业务语义都已正确 |
| `class RecommendState(MessagesState)` | 继承消息 channel 再增加字段 | Python 自动为每个键生成值 |
| `class NeedReserveOutput(TypedDict)` | 为节点间额外输出提供 schema | 私有权限控制或加密 |

TypedDict 在运行时依然是普通字典语义；Pydantic 有模型实例与验证行为；MessagesState 还携带 LangGraph 消息 reducer 的约定。它们不能只因为都“定义字段”就互换。

## 3. Optional 不等于“可以不传且自动为 None”

```python
budget_min: Optional[float] = Field(default=None, description="最低预算")
```

`Optional[float]` 等价于 `float | None`，描述可接受值；`default=None` 才提供缺省值。没有默认值时，一个接受 None 的 Pydantic 字段仍可能要求调用者显式提供。

`None` 表示未知；0 表示已知数字零。比较大小前先判断 None，否则会出现不能比较 None 与数字的错误。

## 4. 字典访问、默认值与真假判断

```python
prefs['budget_min']             # 缺键会 KeyError
prefs.get('budget_min')         # 缺键返回 None
prefs.get('reserved_info', [])  # 缺键返回 []，但已有 None 仍返回 None
prefs.get('reserved_info') or []# 缺键或假值时得到 []
```

最后一种适用于希望把空预约列表统一处理的场景，但不能照搬到预算：`budget_min or 500` 会把合法 0 改成 500。

| 表达式 | 值为 0 时 | 值为 None 时 |
| --- | --- | --- |
| `not value` | True | True |
| `value is None` | False | True |
| `value is not None` | True | False |

## 5. and 的短路为什么能防止下标越界

```python
if prefs_result and prefs_result[0]:
    ...
```

Python 先计算左边。空列表为 False，右边不会执行，所以不会访问空列表的第 0 项。这里第二个判断检查的是第一项的真假，不是再次取列表长度。

当前写法更直接：

```python
existing = prefs_result[0] if prefs_result else None
```

条件表达式先判断中间条件，再选择左值或右值。不是先执行 `[0]` 才看列表是否为空。

## 6. 生成器表达式、列表推导式、any、next

```python
next(tool for tool in tools if tool.name == 'sql_db_schema')
```

可展开理解为：

```python
for tool in tools:
    if tool.name == 'sql_db_schema':
        selected = tool
        break
```

但 next 在没有匹配项时会抛 StopIteration；可写 `next(generator, default)` 提供默认值，再显式验证依赖。

```python
any(updated_state.get(key) is not None
    for key in ('budget_min', 'budget_max'))
```

逐项产生 bool，只要有一个 True 就停止。它判断“至少一个预算键有值”，不是“值本身为真”，因此保留 0。

与 `[expr for item in items]` 的列表推导式相比，生成器按需产生值，不立即创建完整列表。两者都不保证业务执行并行。

## 7. 嵌套函数为什么能访问 model、updated_state 等外部名字

局部函数 `extract_info` 在节点内部定义，方便把只服务于该节点的步骤放在一起。它通过正常的 Python 名字解析访问模型等外部对象，不是创建独立 Agent 或线程。

参数名与调用时传值仍要对应：`extract_info([HumanMessage(...)])` 应使用传入 messages。忽略传参而一直读旧变量，会导致恢复后抽取的仍是旧问题。

## 8. `*`、`**`、`[]` 在函数边界的不同含义

```python
def node(state, runtime, *, store): ...
node(state, runtime, store=my_store)
```

单独的 `*` 使后面的参数必须按关键字传入。`**kwargs` 则收集额外关键字参数，`fn(**dict_value)` 是展开字典传参；不是同一个操作。

`[SystemMessage(...)] + messages` 是列表拼接；`return {'messages':[response]}` 是字典内放列表。这里没有 `**`，不能理解成自动合并整个 State。

## 9. `@tool` 和 Annotated 分别发生在哪一层

`@tool` 在函数定义时包装工具对象，读取名字、docstring 和参数；框架执行时按调用 args 加上注入依赖运行工具。

`Annotated[Any, InjectedStore()]` 的结构是“主要类型 + 附加元数据”。模型接收的工具 schema 不应要求填写 Store；执行层解析标记并注入真实对象。

普通调用工具底层函数不会自动获得框架所有依赖，所以离线测试需要显式提供测试 runtime 和 Store。

## 10. model_dump、dict.update、deepcopy、list 的差异

| 调用 | 输出/副作用 |
| --- | --- |
| `model_dump()` | Pydantic 模型转普通数据 |
| `model_dump(exclude_none=True)` | 去掉 None 字段，保留 0 |
| `model_dump(mode='json')` | 转成适合 JSON 的值表示 |
| `dict.update(other)` | 原地合并字典，返回 None |
| `deepcopy(value)` | 隔离嵌套对象引用 |
| `list(existing_list)` | 创建新列表，但元素仍可能共享引用 |

这些解决数据表示与内存引用，不提供数据库原子事务、锁或幂等。

## 11. 相邻字符串、f-string、format

```python
content = ("用户的历史偏好如下："
           f"最低预算：{prefs.get('budget_min')}"
           f"最高预算：{prefs.get('budget_max')}")
```

相邻字符串在此处拼接，f-string 先计算花括号表达式。没有显式 `\n` 就没有换行；缩进只影响源码排版，不会自动变成消息格式。

`.format(city=...)` 则由模板占位符匹配关键字，缺参数可能 KeyError。它与 SQL 参数化不是同一个东西，不能把普通字符串格式化称为防注入查询。

## 12. Literal 是允许值描述，路由仍需要真实代码

```python
def router(...) -> Literal['reserve_graph', '__end__']:
    ...
```

注解帮助描述可能返回值，但普通 Python 不会因此自动拒绝其他字符串。Pydantic 结构化模型使用 Literal 时才有对应字段验证。图的路径映射还需与实际返回值匹配。

## 13. 三种“名字”与三种 ID

| 层次 | 例子 |
| --- | --- |
| 服务入口 ID | `reserve_agent`，定义在 langgraph.json |
| Python 图变量 | `reserve_graph = builder.compile()` |
| 父图内节点名 | `add_node('reserve_graph', reserve_graph)` |
| 函数/子图内节点名 | `get_phone` |

| 标识 | 用途 |
| --- | --- |
| AIMessage.id | 消息合并与替换 |
| tool_call.id | 工具请求与 ToolMessage 配对 |
| Store key / order_id | 偏好记录标识 / 单次预约标识，彼此也不同 |

再加上 API 的 assistant_id、thread_id、context.user_id，每个标识都在自己的作用域内。先确认作用域，才能正确定位“到底该复用哪个 ID”。

## 14. 链式建图与普通展开

`StateGraph(...).add_node(...).add_edge(...).compile()` 是方法依次返回 builder 后继续调用。它是构建阶段，不会按这行源码立即顺序调用各节点。

节点真正的执行顺序由边、条件和运行输入决定。函数在文件里的定义先后，通常也不等于图的业务执行顺序。

## 15. 练习：先翻译成普通话，再读源码

- `next(t for t in tools if t.name == name)`：找到名字匹配的第一个工具。
- `x = result[0] if result else None`：列表非空才取首项。
- `value is not None`：允许合法 0，拒绝缺失。
- `Annotated[Any, InjectedStore()]`：这是由框架注入的依赖。
- `response.id = old.id`：更新同一条历史消息，而不是追加悬空请求。
- `store.put(namespace, old.key, value)`：覆盖同一个分组下同一条记录。

能用普通话说明“输入是什么、输出是什么、谁执行”，再回到具体语法，复习效率会更高。
