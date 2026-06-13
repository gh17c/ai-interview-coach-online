"""
面试官对话引擎
==============
管理全模拟面试的整个对话流程：
- 开场白生成
- 逐题抽取（随机不重复）
- 追问决策（AI判断回答质量后决定追问还是放行）
- 维度间转场
"""

import random
import json
from modules.api_client import chat
from modules.scenarios import get_scenario


def start_interview(scenario_key: str, profile: dict) -> str:
    """生成面试开场白。AI以面试官身份自我介绍 + 说明面试流程。"""
    scenario = get_scenario(scenario_key)
    system_prompt = (
        f"{scenario['interviewer_tone']}\n\n"
        "面试即将开始，请以面试官身份做开场发言。"
    )

    user_message = (
        f"你是{scenario['name']}的面试官。考生报考{profile.get('target_school', '该校')}"
        f"{profile.get('discipline', '')}专业。\n"
        f"面试环节依次为：{' → '.join(scenario['dimensions'])}。\n"
        "请做开场发言：自我介绍 + 说明面试流程 + 安抚考生 + 开始第一个环节。"
        "语气自然，不要像读稿子。控制在100字以内。"
    )

    result = chat(system_prompt=system_prompt, user_message=user_message, temperature=0.7)
    return result["content"]


def ask_next_question(
    question_pool: dict,
    dimension: str,
    used_question_ids: set,
) -> dict:
    """
    从指定维度的题库中随机抽取一道未用过的题。
    返回: {"question": str, "dimension": str, "question_id": str}
    """
    questions = question_pool.get(dimension, [])
    if not questions:
        return {
            "question": "请介绍一下你自己。",
            "dimension": dimension,
            "question_id": "fallback",
        }

    available = [q for q in questions if q["id"] not in used_question_ids]
    if not available:
        available = questions
        used_question_ids.clear()

    chosen = random.choice(available)
    used_question_ids.add(chosen["id"])

    return {
        "question": chosen["text"],
        "dimension": dimension,
        "question_id": chosen["id"],
    }


def decide_follow_up(
    user_answer: str,
    current_question: str,
    interview_history: list[dict],
    scenario_key: str,
    round_number: int,
) -> dict:
    """
    AI 分析用户回答质量，判断是否追问。
    返回: {"should_follow_up": bool, "follow_up_question": str, "transition_text": str}
    """
    scenario = get_scenario(scenario_key)
    max_depth = scenario.get("follow_up_max_depth", 2)

    if round_number >= max_depth:
        return {
            "should_follow_up": False,
            "follow_up_question": "",
            "transition_text": "好的，我们看下一道题。",
        }

    system_prompt = (
        f"{scenario['interviewer_tone']}\n\n"
        "你正在面试一位考生。现在你需要判断：\n"
        "1. 先分析考生刚才的回答质量（简评）\n"
        "2. 如果回答明显有漏洞、过于简短（<50字）、或暴露出值得深挖的点 → 追问\n"
        "3. 如果回答充分完整 → 放行\n\n"
        "重要：不要每道题都追问。只有回答确实存在问题或明显有追问价值时才追问。"
    )

    context = f"当前题目：{current_question}\n"
    context += f"考生回答：{user_answer}\n"
    context += f"当前追问轮次：{round_number + 1}/{max_depth}\n"

    user_message = (
        f"{context}\n\n"
        "请判断是否追问。返回 JSON：\n"
        '{"should_follow_up": true/false,'
        ' "follow_up_question": "追问内容（仅当should_follow_up为true时填写）",'
        ' "transition_text": "自然转场语（仅当should_follow_up为false时填写，要自然衔接）"}'
    )

    result = chat(
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=0.5,
        response_format={"type": "json_object"},
    )

    try:
        decision = json.loads(result["content"])
    except json.JSONDecodeError:
        decision = {"should_follow_up": False, "follow_up_question": "", "transition_text": "好的，下一题。"}

    return {
        "should_follow_up": decision.get("should_follow_up", False),
        "follow_up_question": decision.get("follow_up_question", ""),
        "transition_text": decision.get("transition_text", "好的，我们继续下一道题。"),
    }


def generate_transition(
    from_dimension: str,
    to_dimension: str,
    scenario_key: str,
) -> str:
    """生成维度间的自然转场语。"""
    scenario = get_scenario(scenario_key)

    system_prompt = (
        f"{scenario['interviewer_tone']}\n"
        "你正在面试一位考生，一个环节刚结束，需要过渡到下一个环节。"
    )

    user_message = (
        f"「{from_dimension}」环节已结束，接下来进入「{to_dimension}」环节。\n"
        f"请说一句自然的转场语。不要生硬，要有衔接感。控制在1-2句话。"
    )

    result = chat(system_prompt=system_prompt, user_message=user_message, temperature=0.7)
    return result["content"]
