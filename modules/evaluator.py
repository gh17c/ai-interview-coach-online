"""
评估引擎
========
evaluate_answer: 单题即时评估（单题练习模式）
generate_full_report: 全场综合报告（全模拟模式）
"""

import json
from modules.api_client import chat
from modules.scenarios import get_scenario


def evaluate_answer(
    question: str,
    user_answer: str,
    dimension: str,
    profile: dict,
) -> dict:
    """
    对单道题的回答进行评估。
    返回: {score, strengths, weaknesses, model_answer, follow_up_suggestions}
    """
    system_prompt = (
        "你是一位专业的学术面试评估专家。请对考生的回答进行评估。\n"
        "评分标准（1-10分）：\n"
        "- 8-10分：回答全面、有深度、逻辑清晰、有个人见解\n"
        "- 5-7分：基本正确但不够深入，或缺少具体例子\n"
        "- 1-4分：回答有明显错误或过于简短\n\n"
        "请给出具体、有建设性的反馈。批评要温和但直接。"
    )

    user_message = (
        f"考生报考专业：{profile.get('discipline', '未知')}\n"
        f"题目所属维度：{dimension}\n"
        f"面试题目：{question}\n"
        f"考生回答：{user_answer}\n\n"
        "请评估并返回 JSON：\n"
        '{"score": 整数1-10,'
        ' "strengths": ["优点1", "优点2"],'
        ' "weaknesses": ["待改进1", "待改进2"],'
        ' "model_answer": "一段完整的示范回答（200字左右，展示高分回答应该有的结构和深度）",'
        ' "follow_up_suggestions": ["如果这是真实面试，可能追问的方向1", "方向2"]}'
    )

    result = chat(
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=0.5,
        response_format={"type": "json_object"},
    )

    try:
        evaluation = json.loads(result["content"])
    except json.JSONDecodeError:
        evaluation = {
            "score": 5,
            "strengths": ["回答已提交"],
            "weaknesses": ["评估解析异常，请重试"],
            "model_answer": "（评估生成失败，请重新提交回答）",
            "follow_up_suggestions": [],
        }

    evaluation.setdefault("score", 5)
    evaluation.setdefault("strengths", [])
    evaluation.setdefault("weaknesses", [])
    evaluation.setdefault("model_answer", "")
    evaluation.setdefault("follow_up_suggestions", [])

    return evaluation


def generate_full_report(
    interview_log: list[dict],
    profile: dict,
    scenario_key: str,
) -> dict:
    """
    全模拟面试结束后，生成完整的诊断报告。
    """
    scenario = get_scenario(scenario_key)
    dimensions = scenario["dimensions"]

    summary_lines = []
    for msg in interview_log:
        role = "面试官" if msg.get("role") == "interviewer" else "考生"
        content = msg.get("content", "")[:200]
        dim = msg.get("dimension", "")
        is_fu = "追问" if msg.get("is_followup") else "主问"
        summary_lines.append(f"[{role} | {dim} | {is_fu}] {content}")

    conversation_summary = "\n\n".join(summary_lines)

    system_prompt = (
        "你是一位资深学术面试评估专家。请根据完整的面试对话记录，"
        "生成一份全面、公正的诊断报告。\n"
        "你的反馈应该是：具体的（引用对话中的例子）、建设性的（告诉考生怎么改进）、"
        "温暖的（肯定努力的同时指出不足）。"
    )

    dim_list = "、".join(dimensions)
    user_message = (
        f"面试类型：{scenario['name']}\n"
        f"考生报考{profile.get('discipline', '')}专业，目标{profile.get('target_school_tier', '')}院校。\n"
        f"面试涵盖维度：{dim_list}\n\n"
        f"=== 完整面试对话 ===\n{conversation_summary}\n=== 对话结束 ===\n\n"
        "请返回 JSON：\n"
        '{\n'
        f'  "overall_score": 整数0-100,\n'
        f'  "dimension_scores": {{"{dimensions[0]}": 分数, ...}},\n'
        '  "highlights": ["整体亮点1（引用对话细节）", ...最多5条],\n'
        '  "improvements": ["整体待改进1（引用对话细节）", ...最多5条],\n'
        '  "per_question_feedback": [\n'
        '    {{"question": "题目摘要", "dimension": "维度", "comment": "简短评价", "score": 分数}},\n'
        '    ...\n'
        '  ],\n'
        '  "improvement_plan": ["具体可执行的改进建议1", ...最多5条]\n'
        '}'
    )

    result = chat(
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=0.5,
        response_format={"type": "json_object"},
    )

    try:
        report = json.loads(result["content"])
    except json.JSONDecodeError:
        report = {
            "overall_score": 60,
            "dimension_scores": {},
            "highlights": ["你完成了本次模拟面试"],
            "improvements": ["报告生成遇到技术问题，请查看逐题对话"],
            "per_question_feedback": [],
            "improvement_plan": ["建议重新进行一次面试以获取完整报告"],
        }

    report.setdefault("overall_score", 60)
    report.setdefault("dimension_scores", {})
    report.setdefault("highlights", [])
    report.setdefault("improvements", [])
    report.setdefault("per_question_feedback", [])
    report.setdefault("improvement_plan", [])

    return report
