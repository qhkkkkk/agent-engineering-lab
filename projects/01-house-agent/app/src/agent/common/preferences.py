"""偏好数据合并与序列化；历史预算使用区间包络策略。"""
from copy import deepcopy
from typing import Mapping, Any

from agent.common.store import ReservedInfo


def preference_namespace(context: Mapping[str, Any] | None) -> tuple[str, str]:
    user_id = (context or {}).get("user_id")
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("context.user_id 必须是非空字符串")
    return (user_id.strip(), "preferences")


def merge_budget_envelope(existing: dict | None, minimum: float | None,
                          maximum: float | None) -> dict:
    """保存历史区间包络；当前搜索预算仍以本次 State 为准。"""
    prefs = deepcopy(existing or {})
    if minimum is not None and (prefs.get("budget_min") is None or minimum < prefs["budget_min"]):
        prefs["budget_min"] = minimum
    if maximum is not None and (prefs.get("budget_max") is None or maximum > prefs["budget_max"]):
        prefs["budget_max"] = maximum
    return prefs


def append_reservation(existing: dict | None, reservation: ReservedInfo) -> dict:
    """新建和更新分支都写入 JSON 值，兼容旧记录中的 reserved_info=null。"""
    prefs = deepcopy(existing or {})
    records = list(prefs.get("reserved_info") or [])
    records.append(reservation.model_dump(mode="json", exclude_none=True))
    prefs["reserved_info"] = records
    return prefs
