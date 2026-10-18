import os
import uuid
from typing import Optional

from dotenv import load_dotenv
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.tools import QuerySQLDatabaseTool
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import filter_messages, HumanMessage, SystemMessage, AIMessage
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime
from langgraph.store.base import BaseStore
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from agent.common.context import ContextSchema
from agent.common.llm import model
from agent.common.preferences import merge_budget_envelope, preference_namespace
from sqlalchemy import URL
from agent.state.recommend import RecommendState, get_recommend_info


class UserInfo(BaseModel):
    """用户的租房需求信息"""

    city: Optional[str] = Field(
        default=None,
        description="用户所在或想要租房的城市，例如：西安、北京、上海"
    )
    district: Optional[str] = Field(
        default=None,
        description="用户想要租房的具体区域或行政区，例如：雁塔区、碑林区、海淀区"
    )
    budget_min: Optional[float] = Field(
        default=None,
        description="用户的最低预算，单位为元/月。如果是xx元以内，要设置最小值为0"
    )
    budget_max: Optional[float] = Field(
        default=None,
        description="用户的最高预算，单位为元/月。如果是xx元以上，最大值设置为10000"
    )
    room_type: Optional[str] = Field(
        default=None,
        description="房屋类型，例如：整租、合租、公寓、一室一厅、两室一厅"
    )
    orientation: Optional[str] = Field(
        default=None,
        description="房屋朝向，例如：朝南、朝北、东南、南北通透"
    )
    room_count: Optional[int] = Field(
        default=None,
        description="需要推荐的房屋数量"
    )
    others: Optional[str] = Field(
        default=None,
        description="特殊要求，例如：带阳台、独立卫生间、近地铁、可养宠物、有电梯等"
    )


def collect_user_info(state: RecommendState, runtime: Runtime[ContextSchema], *, store: BaseStore):
    """收集用户希望的推荐信息"""

    # 1. 获取需要被解析的数据：最新的用户消息 + 用户的偏好数据
    # 场景1：
    # 最新的用户消息： 西安 3套
    # 用户的偏好数据： 预算 1000-2000元
    user_messages = filter_messages(state["messages"], include_types="human")
    pref = state.get("user_preferences")
    if pref and (pref.get("budget_min") is not None or pref.get("budget_max") is not None):
        # 偏好中包含最低和最高预算
        extract_messages = [
            HumanMessage(content="用户的历史偏好信息如下："
                         f"1. 最低预算：{pref.get('budget_min')}"
                         f"2. 最高预算：{pref.get('budget_max')}"),
            user_messages[-1]
        ]
    else:
        # 无偏好数据
        extract_messages = [user_messages[-1]]

    # 2. 提取信息(LLM结构化返回)
    # 拓展：将信息与数据库表中的字段进行映射
    def extract_info(messages) -> UserInfo:
        system_message = SystemMessage(
            content="""
你是一个租房需求信息提取专家。请从用户的描述与历史信息中提取租房相关信息。
如果用户历史偏好信息与最新用户消息冲突，以最新的用户消息为主。
只提取用户明确提到的信息，不要猜测或推断。
如果某个信息用户没有提到，就返回null。
注意预算的单位可能是元/月、元/天等，请统一转换为元/月。
如果用户提到价格范围，请分别提取最低和最高预算。
如果用户提到推荐几套房，提取room_count字段。"""
        )
        return model.with_structured_output(schema=UserInfo).invoke([system_message] + messages)

    # 更新状态函数
    def update_state(current_state: dict, info: UserInfo) -> dict:
        if not info:
            return current_state

        user_info_dict = info.model_dump(exclude_none=True)
        current_state.update(user_info_dict)
        return current_state


    # 根据历史偏好和用户消息提取消息
    updated_state = {}
    extracted_info = extract_info(extract_messages)
    updated_state = update_state(updated_state, extracted_info)

    # 3. 中断咨询推荐的必须参数
    # 场景2：
    # 最新的用户消息：给我推荐房子（并未表明推荐城市，模糊推荐）
    # 询问用户意向城市

    # 检查是否缺失关键信息: 城市、预算范围
    missing_info = []
    if not updated_state.get("city"):
        missing_info.append("**城市**")
    if updated_state.get("budget_min") is None or updated_state.get("budget_max") is None:
        missing_info.append("**预算范围**")

    while missing_info:
        prompt = f"为了给您推荐合适的房源，请提供以下信息:{'，'.join(missing_info)}和其它信息。\n"
        prompt += "如果您不想提供，请输入'**不提供**',我会根据已有信息为您推荐房源。"
        # 根据缺失的信息进行中断
        answer = interrupt(prompt)
        if str(answer).strip() == "不提供":
            # 已经缺失关键信息，而且用户还不提供。需要给关键信息设置默认值
            if not updated_state.get("city"):
                updated_state["city"] = "随机城市"
            if updated_state.get("budget_min") is None:
                updated_state["budget_min"] = 500.0
            if updated_state.get("budget_max") is None:
                updated_state["budget_max"] = 5000.0
            if not updated_state.get("room_count"):
                updated_state["room_count"] = 5
        else:
            # 缺失关键信息，但用户已经补充
            # 将answer构建为HumanMessage
            user_response_msg = HumanMessage(content=str(answer))
            extracted_info = extract_info([user_response_msg])
            # updated_state就是包含了中断的结果
            updated_state = update_state(updated_state, extracted_info)
        # Resume 后仍缺条件则再次询问；同一节点的 interrupt 调用顺序须保持稳定。
        missing_info = []
        if not updated_state.get("city"):
            missing_info.append("**城市**")
        if updated_state.get("budget_min") is None or updated_state.get("budget_max") is None:
            missing_info.append("**预算范围**")

    # 4. 持久化处理：更新预算
    # 场景3：
    # 最新的用户消息：西安 3套  预算0-5000元
    # 用户的偏好数据：预算 1000-2000元
    if any(updated_state.get(key) is not None for key in ("budget_min", "budget_max")):
        namespace = preference_namespace(runtime.context)
        prefs_result = store.search(namespace)
        existing = prefs_result[0] if prefs_result else None
        prefs = merge_budget_envelope(
            existing.value if existing else {},
            updated_state.get("budget_min"), updated_state.get("budget_max"),
        )
        store.put(namespace, existing.key if existing else str(uuid.uuid4()), prefs)
        updated_state["user_preferences"] = prefs

    # 5. 准备最终的消息，并更新
    updated_state["messages"] = [HumanMessage(content=get_recommend_info(updated_state))]

    print(f"已收集用户信息：\n城市：{updated_state.get('city')}"
          f"区域：{updated_state.get('district')}"
          f"预算：{updated_state.get('budget_min')}-{updated_state.get('budget_max')}元/月"
          f"房间数：{updated_state.get('room_count')}")

    # 返回局部更新；messages 由 MessagesState 的 add_messages 合并，不清空历史。
    return updated_state


# .env 在 common.llm 中先于模型初始化加载；DB_PASSWORD 保持原始密码。
load_dotenv()
required = ("DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME")
missing = [key for key in required if not os.getenv(key)]
if missing:
    raise ValueError("缺少数据库配置：" + ", ".join(missing))
db_url = URL.create(
    "mysql+pymysql", username=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"], host=os.environ["DB_HOST"],
    port=int(os.environ["DB_PORT"]), database=os.environ["DB_NAME"],
)
# 此模块在导入时建立数据库连接，启动前需完成配置。
db = SQLDatabase.from_uri(db_url)

# 获取数据库工具
toolkit = SQLDatabaseToolkit(db=db, llm=model)
tools = toolkit.get_tools()
# 节点：获取表信息
get_schema_tool =  next(tool for tool in tools if tool.name == "sql_db_schema")
get_schema_node = ToolNode([get_schema_tool], name="get_schema")  # 工具执行节点（返回ToolMessage）
# 节点：执行sql查询
run_query_tool =  next(tool for tool in tools if tool.name == "sql_db_query")
run_query_node = ToolNode([run_query_tool], name="run_query")     # 工具执行节点（返回ToolMessage）

# 节点：获取全量表
def list_tables(state: RecommendState):
    # 1. 获取AIMessage(tool_calls)
    tool_call = {
        "name": "sql_db_list_tables",
        "args": {},
        "id": str(uuid.uuid4()),
        "type": "tool_call",
    }
    # 模拟必定调用工具
    tool_call_message = AIMessage(content="", tool_calls=[tool_call])

    # 2. 手动调用工具：sql_db_list_tables
    list_tables_tool = next(tool for tool in tools if tool.name == "sql_db_list_tables")
    tool_message = list_tables_tool.invoke(tool_call)

    # 3. 整合结果
    response = AIMessage(content=f"可用的表：{tool_message.content}")
    return {
        "messages": [tool_call_message, tool_message, response]
    }

# 节点：绑定工具（获取表信息），让LLM将来必定执行工具节点
def call_get_schema(state: RecommendState):
    llm_with_tools =  model.bind_tools([get_schema_tool], tool_choice="any")
    # llm 根据历史消息筛选表，并获取需要的表信息
    response =  llm_with_tools.invoke(state["messages"])  # AIMessage(tool_calls)
    # 下一步一定是会调用get_schema_tool工具的！
    return {
        "messages": [response]
    }


# 构造SQL: select * from house where city=西安 and 条件2=？

# 节点：生成SQL + 整合结果
def generate_query(state: RecommendState):
    generate_query_system_prompt = """
您是一个设计用于与SQL数据库交互的代理。
给定一个输入问题，创建一个语法正确的{dialect}查询来运行，然后查看查询的结果并返回答案。
需要根据rows from table的示例设置真实查询的值。
除非用户指定了他们希望获得的特定数量的示例，否则始终将查询限制为最多{top_k}个结果。
您可以按相关列对结果排序，以返回最感兴趣的结果。不要查询特定表中的所有列，只查询给定问题的相关列。
不要对数据库做任何DML语句（INSERT， UPDATE， DELETE， DROP等)。
        """
    system_prompt = generate_query_system_prompt.format(
        dialect=db.dialect,
        top_k=state.get("room_count", 5)
    )

    system_message = SystemMessage(content=system_prompt)
    llm_with_tools = model.bind_tools([run_query_tool])
    return {
        "messages": [llm_with_tools.invoke([system_message] + state["messages"])]  # AIMessage(tool_call?)
    }

    # QuerySQLDatabaseTool
    # tool_call: {
    #     "name": sql_db_query  # 运行sql
    #     "args": {"query": "select ....."}              # sql
    #     "id":
    # }

def check_query(state: RecommendState):
    # 走到这个节点，上一个节点必然是generate_query，并且最新的消息必然是AIMessage(tool_call)
    check_query_system_prompt = """
你是一个非常注重细节的SQL专家。仔细检查{dialect}查询中的常见错误，包括：
-使用NULL值的NOT IN
-在应该使用UNION ALL时使用UNION
-使用BETWEEN表示独占范围
-谓词中的数据类型不匹配
-正确引用标识符
-使用正确数量的函数参数
-转换为正确的数据类型
-使用合适的列进行连接
如果存在上述任何错误，请重写查询。如果没有错误，只需复制原始查询即可。
在运行此检查之后，您将调用适当的工具来执行查询。
        """.format(dialect=db.dialect)
    system_message = SystemMessage(content=check_query_system_prompt)
    # 将SQL当作用户消息传入进行检查
    tool_call = state["messages"][-1].tool_calls[0]
    # tool_call["args"]["query"] 就能拿到SQL
    # tool_call: {
    #     "name": sql_db_query  # 运行sql
    #     "args": {"query": "select ....."}              # sql
    #     "id":
    # }
    user_message = HumanMessage(content=tool_call["args"]["query"])
    llm_with_tools = model.bind_tools([run_query_tool], tool_choice="any")  # 必须让AIMessage带上tool_calls
    response = llm_with_tools.invoke([system_message, user_message])  # 带tool_calls的AIMessage
    # 目前最新的一个消息是AI(t)，现在又生成了一个AI(t)，则可以将两个合成一个
    response.id = state["messages"][-1].id
    return {"messages": [response]}
