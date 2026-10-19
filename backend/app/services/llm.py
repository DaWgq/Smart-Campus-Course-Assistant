"""DeepSeek 大模型封装（通过 langchain-openai 兼容 OpenAI 协议）。"""
from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings

_llm: ChatOpenAI | None = None


def get_llm(temperature: float = 0.3) -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            model=settings.DEEPSEEK_MODEL,
            temperature=temperature,
            timeout=60,
            max_retries=2,
        )
    return _llm


def build_messages(system: str, history: list[dict], user_input: str) -> list:
    msgs: list = [SystemMessage(content=system)]
    for m in history[-8:]:
        if m.get("role") == "user":
            msgs.append(HumanMessage(content=str(m.get("content", ""))))
        elif m.get("role") == "assistant":
            msgs.append(AIMessage(content=str(m.get("content", ""))))
    msgs.append(HumanMessage(content=user_input))
    return msgs


def chat(system: str, history: list[dict], user_input: str) -> str:
    llm = get_llm()
    resp = llm.invoke(build_messages(system, history, user_input))
    return (resp.content or "").strip()


def chat_json(system: str, user_input: str, fallback: dict | None = None) -> dict:
    """要求模型返回 JSON，失败时回退到本地解析。"""
    import json
    import re

    try:
        raw = chat(system + "\n\n只输出合法 JSON，不要任何额外说明文字或代码块标记。", [], user_input)
        text = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
    except Exception:
        pass
    return fallback or {}
