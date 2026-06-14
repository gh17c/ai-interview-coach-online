"""
评估引擎
========
evaluate_answer: 单题即时评估（单题练习模式）
generate_full_report: 全场综合报告（全模拟模式）

评分哲学：严厉但公正。不使用模糊的"不错/还可以"，而用具体证据说话。
AI 必须使用全量程（1-10），不能集中在 7-8 分的安全区。
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
    word_count = len(user_answer.replace("\n", "").replace(" ", ""))
    answer_len_hint = ""
    if word_count < 30:
        answer_len_hint = "⚠️ 考生回答极短（<30字），按评分标准应严格扣分，不能给超过4分。"
    elif word_count < 80:
        answer_len_hint = "⚠️ 考生回答偏短（<80字），通常缺乏展开，分数不应超过6分。"
    elif word_count < 150:
        answer_len_hint = "ℹ️ 考生回答中等长度（80-150字），如果内容充实可给到7-8分。"
    else:
        answer_len_hint = "ℹ️ 考生回答充分（>150字），有空间展示深度和结构。"

    system_prompt = (
        "你是一位严厉而公正的学术面试评估专家。你的评分必须能够**区分不同质量的回答**。\n\n"
        "## 评分量程（必须使用全量程，禁止集中在6-8分区间！）\n\n"
        "| 分数 | 标准 | 典型特征 |\n"
        "|------|------|----------|\n"
        "| 9-10 | 卓越 | 回答全面、逻辑严密、有独到见解或深度思考、举例精准、可立即录取 |\n"
        "| 7-8  | 优秀 | 回答正确且较深入，逻辑清晰，有个别亮点，但缺少深度或个人见解 |\n"
        "| 5-6  | 及格 | 基本方向对，但内容单薄、缺少具体例子、逻辑不够严密 |\n"
        "| 3-4  | 较差 | 回答简短空洞、有逻辑漏洞、或答非所问 |\n"
        "| 1-2  | 极差 | 完全答错、自相矛盾、或只有一两句话 |\n\n"
        "## 评分四要素（各占25%）\n"
        "1. **内容准确性**：回答是否正确、没有事实错误\n"
        "2. **深度与细节**：是否展开论述、有无具体例子/数据支撑\n"
        "3. **逻辑结构**：回答是否有条理（如STAR法则）\n"
        "4. **个人见解**：是否有自己的思考，而非背诵模板\n\n"
        "## 重要原则\n"
        "- **必须使用全量程**：如果所有考生都拿7-8分，评分系统就是废的\n"
        "- **简短回答必须低分**：这是面试，不是问答机器人，一两句话拿不到高分\n"
        "- **有具体例子才给高分**：空谈理论的回答最多6分\n"
        "- **优点和缺点各至少2条**：每条必须引用回答中的具体内容\n"
        "- **示范回答要展示差距**：让考生看到9-10分的回答长什么样"
    )

    user_message = (
        f"考生报考：{profile.get('discipline', '未知')}专业\n"
        f"题目维度：{dimension}\n"
        f"面试题目：{question}\n"
        f"考生回答（{word_count}字）：{user_answer}\n\n"
        f"{answer_len_hint}\n\n"
        "请按四要素逐项评估，然后给出总分。返回 JSON：\n"
        '{\n'
        '  "score": 整数1-10（⚠️ 必须使用全量程！参考字数提示决定分数上限）, \n'
        '  "accuracy_score": 1-10（内容准确性）, \n'
        '  "depth_score": 1-10（深度与细节）, \n'
        '  "structure_score": 1-10（逻辑结构）, \n'
        '  "insight_score": 1-10（个人见解）, \n'
        '  "strengths": ["具体优点1（引用回答原句）", "具体优点2"], \n'
        '  "weaknesses": ["具体待改进1（指出缺失了什么）", "具体待改进2"], \n'
        '  "model_answer": "示范回答（200-300字，展示9-10分水平应有的结构和深度）", \n'
        '  "follow_up_suggestions": ["追问方向1", "追问方向2"]\n'
        '}'
    )

    result = chat(
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=0.4,
        response_format={"type": "json_object"},
    )

    try:
        evaluation = json.loads(result["content"])
    except json.JSONDecodeError:
        evaluation = {
            "score": max(1, min(4, word_count // 20)),
            "strengths": ["回答已提交"],
            "weaknesses": ["评估解析异常，请重试"],
            "model_answer": "",
            "follow_up_suggestions": [],
        }

    # 硬上限：极短回答不能超过4分（防止AI给同情分）
    if word_count < 30 and evaluation.get("score", 5) > 4:
        evaluation["score"] = max(1, evaluation["score"] - 4)

    evaluation.setdefault("score", 5)
    evaluation.setdefault("strengths", [])
    evaluation.setdefault("weaknesses", [])
    evaluation.setdefault("model_answer", "")
    evaluation.setdefault("follow_up_suggestions", [])
    evaluation.setdefault("accuracy_score", 0)
    evaluation.setdefault("depth_score", 0)
    evaluation.setdefault("structure_score", 0)
    evaluation.setdefault("insight_score", 0)

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

    # 统计基础数据
    total_questions = 0
    dim_question_counts = {d: 0 for d in dimensions}
    for msg in interview_log:
        if msg["role"] == "interviewer" and not msg.get("is_followup") and msg.get("dimension"):
            dim_question_counts[msg.get("dimension", "")] = dim_question_counts.get(msg.get("dimension", ""), 0) + 1
            total_questions += 1

    # 估算回答字数分布
    answer_lens = []
    for msg in interview_log:
        if msg["role"] == "user":
            ans = msg.get("content", "")
            answer_lens.append(len(ans.replace("\n", "").replace(" ", "")))

    avg_len = sum(answer_lens) / max(len(answer_lens), 1)
    short_count = sum(1 for l in answer_lens if l < 50)
    adequate_count = sum(1 for l in answer_lens if l >= 100)

    summary_lines = []
    for msg in interview_log:
        role = "面试官" if msg.get("role") == "interviewer" else "考生"
        content = msg.get("content", "")[:200]
        dim = msg.get("dimension", "")
        is_fu = "追问" if msg.get("is_followup") else "主问"
        summary_lines.append(f"[{role} | {dim} | {is_fu}] {content}")

    conversation_summary = "\n\n".join(summary_lines[-60:])  # 取最近60条

    system_prompt = (
        "你是一位资深学术面试评估专家。请根据面试对话记录生成诊断报告。\n\n"
        "## 评分原则\n"
        "- 使用全量程（0-100），平均分应在60-70分左右\n"
        "- 90+：卓越，几乎无失误\n"
        "- 75-89：优秀，偶有不足\n"
        "- 60-74：良好，有明显可改进处\n"
        "- 40-59：一般，多个维度需要提升\n"
        "- 40以下：较差，基础不牢固\n\n"
        "- 反馈要具体（引用对话细节）、建设性（告诉怎么改）、不讨好\n"
        "- 回答过短（<50字）必须体现在扣分和反馈中\n"
        "- 每个维度分数必须能拉开差距，不要全都70-80"
    )

    dim_list = "、".join(dimensions)

    stats_info = (
        f"共回答了{len(answer_lens)}次（含追问），"
        f"平均每条约{int(avg_len)}字。"
        f"过短回答（<50字）：{short_count}次，"
        f"充分回答（≥100字）：{adequate_count}次。"
    )

    user_message = (
        f"面试类型：{scenario['name']}\n"
        f"考生报考{profile.get('discipline', '')}专业，目标{profile.get('target_school_tier', '')}院校。\n"
        f"面试维度：{dim_list}\n"
        f"统计：{stats_info}\n\n"
        f"=== 面试对话 ===\n{conversation_summary}\n=== 对话结束 ===\n\n"
        "请返回 JSON：\n"
        '{\n'
        f'  "overall_score": 整数0-100（⚠️ 使用全量程，不能都集中在70-80）, \n'
        f'  "dimension_scores": {{"{dimensions[0]}": 0-100, ...}}, \n'
        '  "highlights": ["亮点（引用对话细节）", ...最多5条], \n'
        '  "improvements": ["待改进（指出具体问题）", ...最多5条], \n'
        '  "per_question_feedback": [\n'
        '    {{"question": "题目摘要", "dimension": "维度", "comment": "简短评价", "score": 0-100}},\n'
        '    ...\n'
        '  ],\n'
        '  "improvement_plan": ["具体可执行的改进建议", ...最多5条]\n'
        '}'
    )

    result = chat(
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=0.4,
        response_format={"type": "json_object"},
    )

    try:
        report = json.loads(result["content"])
    except json.JSONDecodeError:
        report = {
            "overall_score": 60,
            "dimension_scores": {},
            "highlights": ["你完成了本次模拟面试"],
            "improvements": ["报告生成遇到技术问题"],
            "per_question_feedback": [],
            "improvement_plan": ["建议重新进行一次面试"],
        }

    report.setdefault("overall_score", 60)
    report.setdefault("dimension_scores", {})
    report.setdefault("highlights", [])
    report.setdefault("improvements", [])
    report.setdefault("per_question_feedback", [])
    report.setdefault("improvement_plan", [])

    return report
