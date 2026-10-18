from typing_extensions import TypedDict

from langgraph.graph import MessagesState

# 主图状态
class State(MessagesState):
    user_preferences: dict   # 用户偏好数据
    user_intent: str         # 用戶意图

# 供节点和条件边使用的内部通道；不是隐私或访问权限控制。
class NeedReserveOutput(TypedDict):
    reserve: str  # 需要、不需要
    # 未列入主 State 的顶层输出 schema，更新事件/追踪仍可能包含它。
