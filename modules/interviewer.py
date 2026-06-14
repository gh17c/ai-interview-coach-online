"""
面试官对话引擎
==============
管理全模拟面试的整个对话流程。核心设计：
- 预制题库仅作为"话题指南"，实际出题由AI根据对话上下文动态生成
- AI记住已讨论内容的摘要，避免重复/类似出题
- 追问前先分析考生回答的具体内容，确保追问针对回答中暴露的问题
- 维度间转场结合上一维度的表现自然过渡
- 面试结束前设置"反问环节"，模拟真实面试
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


def _build_conversation_context(messages: list[dict], last_n: int = 8) -> str:
    """从对话历史中提取最近N轮作为上下文，让AI知道之前聊了什么。"""
    recent = messages[-last_n:] if len(messages) > last_n else messages
    lines = []
    for m in recent:
        role = "面试官" if m["role"] == "interviewer" else "考生"
        content = m.get("content", "")[:300]
        dim = m.get("dimension", "")
        fu = "[追问]" if m.get("is_followup") else ""
        lines.append(f"【{role}{fu}｜{dim}】{content}")
    return "\n".join(lines)


def _get_last_question(messages: list[dict]) -> str:
    """获取对话历史中最后一个面试官提出的主问题（非追问）。"""
    for m in reversed(messages):
        if m["role"] == "interviewer" and not m.get("is_followup"):
            return m.get("content", "")[:100]
    return ""


def _extract_discussed_topics(messages: list[dict]) -> list[str]:
    """从对话历史中提取已被讨论过的主题，供AI参考以避免重复。"""
    topics = []
    for m in messages:
        if m["role"] == "interviewer" and not m.get("is_followup"):
            topic = m.get("content", "").strip()[:50]
            if topic:
                topics.append(topic)
    return topics[-12:]


def ask_next_question(
    question_pool: dict,
    dimension: str,
    used_question_ids: set,
    interview_history: list[dict],
    profile: dict,
    scenario_key: str,
) -> dict:
    """
    智能出题：结合题库话题 + 对话上下文动态生成。
    返回: {"question": str, "dimension": str, "question_id": str}
    """
    scenario = get_scenario(scenario_key)
    questions = question_pool.get(dimension, [])
    available = [q for q in questions if q["id"] not in used_question_ids]

    pool_hint = ""
    pool_id = None
    if available:
        chosen = random.choice(available)
        pool_hint = chosen["text"]
        pool_id = chosen["id"]
        used_question_ids.add(pool_id)
    elif questions:
        used_question_ids.clear()
        chosen = random.choice(questions)
        pool_hint = chosen["text"]
        pool_id = chosen["id"]
        used_question_ids.add(pool_id)

    discussed = _extract_discussed_topics(interview_history)
    discussed_text = "\n".join([f"  · {t}" for t in discussed]) if discussed else "（尚无）"
    context = _build_conversation_context(interview_history, last_n=6)
    last_question = _get_last_question(interview_history)

    system_prompt = (
        f"{scenario['interviewer_tone']}\n\n"
        "你正在面试一位考生。现在该问下一道题了。\n"
        f"当前环节：「{dimension}」\n\n"
        "⚠️ 核心规则（违反会扣分）：\n"
        "1. 新问题必须和上一道题有**明确的主题差异**，不能是同一话题的换说法\n"
        "   - 例：刚问了'团队合作中的角色'，下一道就不能再问'团队项目经历'\n"
        "   - 判断标准：新题的核心话题词不能和上一题重复\n"
        "2. 严禁重复已讨论话题列表中的任何内容\n"
        "3. 结合考生具体背景，确保每个问题考察不同维度\n"
        "4. 语言口语化，像真人面试官说话"
    )

    hint_line = (
        f"题库话题参考（仅作方向提示，用自己的话重述，不要照读）：{pool_hint}"
        if pool_hint
        else f"请根据「{dimension}」的要求，结合考生背景自行生成一道面试题。"
    )
    profile_info = (
        f"考生背景：报考{profile.get('discipline', '未知')}专业，"
        f"目标{profile.get('target_school_tier', '')}院校。\n"
        f"优势：{', '.join(profile.get('strong_points', [])) or '暂无'}\n"
        f"薄弱：{', '.join(profile.get('weak_points', [])) or '暂无'}"
    )

    user_message = (
        f"{profile_info}\n\n"
        f"=== ⚠️ 上一道题（新题必须和它有本质区别）===\n{last_question}\n\n"
        f"=== 已讨论话题（必须避开）===\n{discussed_text}\n\n"
        f"=== 最近对话 ===\n{context}\n\n"
        f"{hint_line}\n\n"
        "请生成一道面试题。先确认和上一题主题不同，再返回 JSON：\n"
        '{"question": "面试题内容（1-2句话，口语化）", "dimension": "' + dimension + '"}'
    )

    result = chat(
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=0.7,
        response_format={"type": "json_object"},
    )

    try:
        data = json.loads(result["content"])
        question_text = data.get("question", pool_hint or f"请谈谈你在{dimension}方面的理解。")
    except json.JSONDecodeError:
        question_text = pool_hint or f"请谈谈你在{dimension}方面的理解。"

    return {
        "question": question_text,
        "dimension": dimension,
        "question_id": pool_id or f"dynamic_{dimension}",
    }


def decide_follow_up(
    user_answer: str,
    current_question: str,
    interview_history: list[dict],
    scenario_key: str,
    round_number: int,
) -> dict:
    """
    AI 深度分析考生回答内容，判断是否追问。
    返回: {"should_follow_up": bool, "follow_up_question": str, "transition_text": str}
    """
    scenario = get_scenario(scenario_key)
    max_depth = scenario.get("follow_up_max_depth", 2)
    tone = scenario.get("interviewer_tone", "")

    if round_number >= max_depth:
        return {"should_follow_up": False, "follow_up_question": "", "transition_text": ""}

    context = _build_conversation_context(interview_history, last_n=6)

    system_prompt = (
        f"{tone}\n\n"
        "你正在面试一位考生。现在你需要判断是否追问。\n\n"
        "请严格按照以下步骤思考：\n"
        "1. 【理解回答】用1句话总结考生刚才回答的核心观点\n"
        "2. 【发现缺口】这个回答是否有：\n"
        "   - 逻辑漏洞/矛盾 → 追问\n"
        "   - 过于简短空洞（<50字）→ 追问\n"
        "   - 缺少具体例子或数据支撑 → 追问\n"
        "   - 值得深入的亮点但没说透 → 追问\n"
        "   - 回答充分、条理清晰 → 放行\n"
        "3. 【生成追问/放行】：\n"
        "   - 追问必须紧贴考生回答中的具体细节\n"
        "   - 正确：「你提到U-Net做图像分割，和FCN比有什么优势？」\n"
        "   - 错误：「请详细说说」（空洞无针对性）\n"
        "   - 不追问时生成自然过渡语\n\n"
        "重要：追问必须引用考生回答中的具体细节，让考生感到你认真听了。"
    )

    user_message = (
        f"当前题目：{current_question}\n"
        f"考生回答：{user_answer}\n"
        f"追问轮次：{round_number + 1}/{max_depth}\n\n"
        f"=== 面试对话上下文 ===\n{context}\n\n"
        "请判断是否追问。返回 JSON：\n"
        '{\n'
        '  "analysis": "你对考生回答的1句话总结",\n'
        '  "should_follow_up": true/false,\n'
        '  "follow_up_question": "针对考生回答中的具体细节追问（仅当should_follow_up为true）",\n'
        '  "transition_text": "自然的转场语（仅当should_follow_up为false）"\n'
        '}'
    )

    result = chat(
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=0.6,
        response_format={"type": "json_object"},
    )

    try:
        decision = json.loads(result["content"])
    except json.JSONDecodeError:
        decision = {"should_follow_up": False, "follow_up_question": "", "transition_text": ""}

    return {
        "should_follow_up": decision.get("should_follow_up", False),
        "follow_up_question": decision.get("follow_up_question", ""),
        "transition_text": decision.get("transition_text", ""),
    }


def generate_transition(
    from_dimension: str,
    to_dimension: str,
    scenario_key: str,
    interview_history: list[dict],
) -> str:
    """生成维度间的自然转场语，结合面试历史让过渡更自然。"""
    scenario = get_scenario(scenario_key)
    context = _build_conversation_context(interview_history, last_n=4)

    system_prompt = (
        f"{scenario['interviewer_tone']}\n"
        "你正在面试一位考生，一个环节刚结束，需要过渡到下一个环节。"
    )

    user_message = (
        f"「{from_dimension}」环节已结束，接下来进入「{to_dimension}」环节。\n\n"
        f"=== 刚才的对话 ===\n{context}\n\n"
        "请说一句自然的转场语。要求：\n"
        "1. 简要总结上一环节的感受（如'你的专业基础不错'）\n"
        "2. 自然引出下一环节\n"
        "3. 控制在1-2句话，不要生硬"
    )

    result = chat(system_prompt=system_prompt, user_message=user_message, temperature=0.7)
    return result["content"]


# ==================== 反问环节 ====================

def start_reverse_questioning(scenario_key: str, profile: dict) -> str:
    """
    面试主体环节结束后，面试官邀请考生反问。
    这是真实面试中常见的'对我们有什么想了解的？'环节。
    """
    scenario = get_scenario(scenario_key)
    system_prompt = (
        f"{scenario['interviewer_tone']}\n\n"
        "所有正式提问环节已结束。现在进入'反问环节'：面试官邀请考生对课题组、研究方向、"
        "学校等提出自己关心的问题。这既是尊重考生，也是考察考生是否做了功课。"
    )

    target_school = profile.get("target_school", "我们学校")
    discipline = profile.get("discipline", "该专业")

    user_message = (
        f"考生报考{target_school}{discipline}。"
        f"所有正式面试环节刚结束。请以面试官身份自然地说：\n"
        f"1. 告知面试主体环节已结束\n"
        f"2. 邀请考生提问（对我们课题组/学校/研究方向有什么想了解的？）\n"
        f"语气轻松自然，让考生感到放松。控制在1-2句话。"
    )

    result = chat(system_prompt=system_prompt, user_message=user_message, temperature=0.7)
    return result["content"]


def respond_to_candidate_question(
    candidate_question: str,
    scenario_key: str,
    profile: dict,
    interview_history: list[dict],
) -> str:
    """
    面试官回答考生的反问。模拟真实面试官的回答风格——真诚、不夸大，适当展示课题组优势。
    """
    scenario = get_scenario(scenario_key)
    target_school = profile.get("target_school", "我们学校")
    discipline = profile.get("discipline", "该专业")

    system_prompt = (
        f"{scenario['interviewer_tone']}\n\n"
        "考生正在向你提问（反问环节）。请以面试官身份回答。\n"
        "回答原则：\n"
        "1. 真诚——知道就说知道，不知道就说'这个具体细节我需要确认后回复你'\n"
        "2. 正面——适当展示课题组/学校的优势，但不夸大\n"
        "3. 简洁——控制在2-4句话，不要长篇大论\n"
        "4. 考察——在回答中也可以顺带了解考生的关注点"
    )

    user_message = (
        f"学校：{target_school}，专业：{discipline}\n"
        f"考生提问：{candidate_question}\n\n"
        f"请以面试官身份自然回答。回答后可以加一句'还有其他想了解的吗？'"
    )

    result = chat(system_prompt=system_prompt, user_message=user_message, temperature=0.7)
    return result["content"]


def close_interview(scenario_key: str) -> str:
    """面试全部结束（含反问环节后的收尾语）。"""
    scenario = get_scenario(scenario_key)
    system_prompt = (
        f"{scenario['interviewer_tone']}\n\n"
        "面试和反问环节都结束了。请以面试官身份做最终收尾：感谢参与、告知后续流程（如'结果会在一周内通知'）、"
        "祝福考生。语气温暖真诚，控制在2-3句话。"
    )
    user_message = f"这是{scenario['name']}的面试收尾。"
    result = chat(system_prompt=system_prompt, user_message=user_message, temperature=0.7)
    return result["content"]
