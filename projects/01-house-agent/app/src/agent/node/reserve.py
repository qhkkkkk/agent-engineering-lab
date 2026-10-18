import uuid
from typing import Annotated, Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode, ToolRuntime, InjectedStore
from langgraph.types import interrupt

from agent.common.llm import model
from agent.common.store import ReservedInfo
from agent.common.preferences import append_reservation, preference_namespace
from agent.state.reserve import ReserveState

# 节点：获取预定房源名称
def get_title(state: ReserveState):
    prompt = "请输入要预定的房源名称"

    while True:
        title = interrupt(prompt)
        if title:  # 验证操作
            return {"title": title}

        # 验证失败：再次输入
        prompt = f"‘{title}’ 不是一个有效的房源名称，请更正"


# 节点：获取预定电话
def get_phone(state: ReserveState):
    prompt = "请输入要预定的手机号"

    while True:
        phone_number = interrupt(prompt)
        if phone_number:  # 验证操作
            return {"phone_number": phone_number}

        # 验证失败：再次输入
        prompt = f"‘{phone_number}’ 不是一个有效的电话号码，请更正"


# 节点：获取预定人员身份证
def get_id(state: ReserveState):
    prompt = "请输入要预定的身份证号码"

    while True:
        id_card = interrupt(prompt)
        if id_card:  # 验证操作
            return {"id_card": id_card}

        # 验证失败：再次输入
        prompt = f"‘{id_card}’ 不是一个有效的身份证号码，请更正"

# 节点：更新HumanMessage
def add_reserve_message(state: ReserveState):
    reserve_prompt = """
根据提供的信息，帮我预定房源。
- 预定的房源标题：{title}
- 用户预定号码：{phone_number}
- 用户身份证号码：{id_card}
    """

    return {"messages": [HumanMessage(content=reserve_prompt.format(
        title=state["title"],
        phone_number=state["phone_number"],
        id_card=state["id_card"]
    ))]}


# 1. 生成工单
# 2. 持久化存储预定信息
#    运行时数据：ToolRuntime
#    store: Annotated[Any, InjectedStore()]  在工具中注入store
@tool
def generate_orders(phone_number: str, id_card: str, house_title: str,
                    runtime: ToolRuntime, store: Annotated[Any, InjectedStore()]) -> str:
    """
根据用户电话、身份证、预定的房源，生成工单号。

Args:
    phone_number: 用户电话
    id_card：身份证
    house_title：用户要预定的房源标题
    runtime：工具的运行时信息
    store：注入工具的持久存储
    """

    # 1. 模拟生成工单号(扩展：持久化订单表)
    order_id = str(uuid.uuid4())

    # 2. 构建预定信息
    reserved_info = ReservedInfo(
        order_id=order_id,
        title=house_title,
        phone_number=phone_number
    )

    # 3. 持久化存储用户偏好（预定信息）
    namespace = preference_namespace(runtime.context)
    # 查询
    prefs_result = store.search(namespace)
    existing = prefs_result[0] if prefs_result else None
    prefs = append_reservation(existing.value if existing else {}, reserved_info)
    store.put(namespace, existing.key if existing else str(uuid.uuid4()), prefs)

    return f"已成功预定房源：{house_title}, 预定工单号为：{order_id}"

# 将来就可以将这个工具，使用ToolNode进行定义
tool_node = ToolNode([generate_orders])

# 节点：执行模型：1. 决定进行工具（预定房源）调用  2. 返回最终结果
def call_orders(state: ReserveState):
    return {"messages": [model.bind_tools([generate_orders]).invoke(
        [SystemMessage(content="你是一个工单生成的助手，支持调用工具进行房源预定工单生成。支持查看结果并返回最终答案")]
        + state["messages"]
    )]}









