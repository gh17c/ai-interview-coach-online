"""
DeepSeek API 统一调用层
======================
所有 LLM 调用走此模块，统一管理 API Key、Token计数、费用统计。
DeepSeek 兼容 OpenAI SDK。
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

_client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY", ""),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
)

DEFAULT_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# DeepSeek 价格 (RMB/1M tokens)，截至2026年6月
PRICE_INPUT = 1.0 / 1_000_000    # 1元/百万token
PRICE_OUTPUT = 2.0 / 1_000_000   # 2元/百万token

_total_cost = 0.0
_total_tokens = {"prompt": 0, "completion": 0}


def _calculate_cost(usage: dict) -> float:
    """根据DeepSeek价格计算费用（元）"""
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    return prompt_tokens * PRICE_INPUT + completion_tokens * PRICE_OUTPUT


def chat(
    system_prompt: str,
    user_message: str,
    temperature: float = 0.7,
    model: str = None,
    response_format: dict | None = None,
) -> dict:
    """
    单轮对话 — 发送 system + user，返回 AI 回复。

    参数:
        system_prompt: 系统提示词
        user_message: 用户消息
        temperature: 0.0-1.0，创造力
        model: 模型名，默认 deepseek-chat
        response_format: 需要JSON输出时传入 {"type": "json_object"}

    返回:
        {"content": str, "usage": dict, "cost": float}
    """
    global _total_cost, _total_tokens
    if model is None:
        model = DEFAULT_MODEL

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    kwargs = {"model": model, "messages": messages, "temperature": temperature}
    if response_format:
        kwargs["response_format"] = response_format

    response = _client.chat.completions.create(**kwargs)
    usage = response.usage
    cost = _calculate_cost({
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
    })

    _total_tokens["prompt"] += usage.prompt_tokens
    _total_tokens["completion"] += usage.completion_tokens
    _total_cost += cost

    return {
        "content": response.choices[0].message.content,
        "usage": {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        },
        "cost": cost,
    }


def multi_turn_chat(
    messages: list[dict],
    temperature: float = 0.7,
    model: str = None,
) -> dict:
    """
    多轮对话 — 传入完整消息列表。

    参数:
        messages: [{"role": "system"|"user"|"assistant", "content": "..."}, ...]
        temperature: 0.0-1.0
        model: 模型名

    返回:
        {"content": str, "usage": dict, "cost": float}
    """
    global _total_cost, _total_tokens
    if model is None:
        model = DEFAULT_MODEL

    response = _client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    usage = response.usage
    cost = _calculate_cost({
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
    })

    _total_tokens["prompt"] += usage.prompt_tokens
    _total_tokens["completion"] += usage.completion_tokens
    _total_cost += cost

    return {
        "content": response.choices[0].message.content,
        "usage": {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        },
        "cost": cost,
    }


def get_total_cost() -> float:
    """获取累计费用（元）"""
    return _total_cost


def get_total_tokens() -> dict:
    """获取累计Token数"""
    return dict(_total_tokens)


def reset_cost() -> None:
    """重置费用和Token计数器"""
    global _total_cost, _total_tokens
    _total_cost = 0.0
    _total_tokens = {"prompt": 0, "completion": 0}
