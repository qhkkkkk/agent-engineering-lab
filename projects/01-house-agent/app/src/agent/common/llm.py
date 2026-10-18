"""共享模型入口：OpenRouter 模型及本地配置。"""
import os

from dotenv import load_dotenv
from langchain_openrouter import ChatOpenRouter

# 环境变量优先，个人配置其次，公开配置仅提供非敏感默认值。
load_dotenv(".env.local")
load_dotenv(".env")
model = ChatOpenRouter(
    model=os.getenv("LLM_MODEL", "openai/gpt-4o-mini"),
    api_key=os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
    temperature=0,
)
