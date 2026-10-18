"""用假模型和临时数据库验证图结构及状态流转。"""
import importlib
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import HumanMessage
from langchain_community.utilities import SQLDatabase
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command
from sqlalchemy import create_engine


class GraphOfflineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:")
        database = SQLDatabase(cls.engine)
        settings = {"DB_HOST": "unused", "DB_PORT": "3306", "DB_USER": "unused",
                    "DB_PASSWORD": "unused", "DB_NAME": "unused"}
        with patch.dict(os.environ, settings), \
             patch("langchain_openrouter.ChatOpenRouter", return_value=FakeListChatModel(responses=["演示"])), \
             patch.object(SQLDatabase, "from_uri", return_value=database):
            cls.main_module = importlib.import_module("agent.graph")
            cls.reserve_nodes = importlib.import_module("agent.node.reserve")
            cls.reserve_state = importlib.import_module("agent.state.reserve").ReserveState
            cls.recommend_nodes = importlib.import_module("agent.node.recommend")

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def test_all_four_graphs_compile(self):
        for module_name, export in (("agent.graph", "graph"), ("agent.recommend", "recommended_graph"),
                                    ("agent.reserve", "reserve_graph"), ("agent.extend", "extend_graph")):
            graph = getattr(importlib.import_module(module_name), export)
            self.assertIn("__start__", graph.get_graph().nodes)
            self.assertIn("__end__", graph.get_graph().nodes)

    def test_private_channel_is_internal_not_top_level_output(self):
        graph = self.main_module.graph
        self.assertIn("reserve", graph.channels)
        self.assertNotIn("reserve", graph.output_channels)

    def test_intent_router(self):
        for intent, target in (("recommend_house", "recommended_graph"), ("reserve_house", "reserve_graph"),
                               ("get_info", "get_user_preferences"), ("others", "extend_graph")):
            self.assertEqual(self.main_module.router_message({"user_intent": intent}), target)

    def test_three_real_capture_nodes_resume_in_order(self):
        nodes = self.reserve_nodes
        builder = StateGraph(self.reserve_state)
        builder.add_sequence([nodes.get_title, nodes.get_phone, nodes.get_id])
        builder.add_edge(START, "get_title")
        builder.add_edge("get_id", END)
        graph = builder.compile(checkpointer=InMemorySaver())
        config = {"configurable": {"thread_id": "offline-demo"}}
        result = graph.invoke({"messages": []}, config)
        self.assertIn("房源", result["__interrupt__"][0].value)
        result = graph.invoke(Command(resume="虚构房源"), config)
        self.assertIn("手机号", result["__interrupt__"][0].value)
        result = graph.invoke(Command(resume="demo-phone"), config)
        self.assertIn("身份证", result["__interrupt__"][0].value)
        result = graph.invoke(Command(resume="demo-id"), config)
        self.assertEqual((result["title"], result["phone_number"], result["id_card"]),
                         ("虚构房源", "demo-phone", "demo-id"))
        self.assertFalse(graph.get_state(config).next)

    def test_actual_booking_tool_create_then_update(self):
        store = InMemoryStore()
        runtime = SimpleNamespace(context={"user_id": "offline-user"})
        for title in ("虚构房源甲", "虚构房源乙"):
            self.reserve_nodes.generate_orders.func(
                phone_number="demo-phone", id_card="demo-id", house_title=title,
                runtime=runtime, store=store,
            )
        records = store.search(("offline-user", "preferences"))
        self.assertEqual(len(records), 1)
        self.assertEqual([x["title"] for x in records[0].value["reserved_info"]],
                         ["虚构房源甲", "虚构房源乙"])

    def test_partial_requirement_resumes_again_and_keeps_zero(self):
        module = self.recommend_nodes

        class Extractor:
            def with_structured_output(self, schema):
                return self

            def invoke(self, messages):
                text = messages[-1].content
                if text == "太原":
                    return module.UserInfo(city="太原")
                if text == "0-1500":
                    return module.UserInfo(budget_min=0, budget_max=1500)
                return module.UserInfo()

        context_schema = importlib.import_module("agent.common.context").ContextSchema
        builder = StateGraph(module.RecommendState, context_schema=context_schema)
        builder.add_node("collect_user_info", module.collect_user_info)
        builder.add_edge(START, "collect_user_info")
        builder.add_edge("collect_user_info", END)
        store = InMemoryStore()
        graph = builder.compile(checkpointer=InMemorySaver(), store=store)
        config = {"configurable": {"thread_id": "partial-requirements"}}
        context = {"user_id": "requirements-user"}
        with patch.object(module, "model", Extractor()):
            result = graph.invoke({"messages": [HumanMessage(content="找房")], "user_preferences": {}},
                                  config, context=context)
            self.assertIn("城市", result["__interrupt__"][0].value)
            result = graph.invoke(Command(resume="太原"), config, context=context)
            self.assertIn("预算", result["__interrupt__"][0].value)
            result = graph.invoke(Command(resume="0-1500"), config, context=context)
        self.assertEqual(result["city"], "太原")
        self.assertEqual(result["budget_min"], 0)
        self.assertEqual(store.search(("requirements-user", "preferences"))[0].value["budget_min"], 0)
        self.assertFalse(graph.get_state(config).next)


if __name__ == "__main__":
    unittest.main()
