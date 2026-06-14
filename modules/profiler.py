"""
用户画像分析 + 个性化题库生成
=============================
analyze_profile: 解析用户表单 → 结构化画像 JSON
generate_question_pool: 根据画像 + 场景 + 种子生成全部面试题
replace_question: 用户换一题时重新生成单道题
"""

import json
from modules.api_client import chat
from modules.scenarios import get_scenario
from modules.question_seeds import get_seeds


def analyze_profile(form_data: dict) -> dict:
    """
    输入: 用户表单原始数据
    输出: 结构化画像
    """
    system_prompt = (
        "你是一位资深的学术面试评估专家。"
        "请根据用户提供的信息，分析其学术背景和面试画像。"
        "只返回 JSON，不要有任何其他文字。"
    )

    user_fields = f"""
报考专业：{form_data.get('target_major', '未提供')}
本科专业：{form_data.get('undergrad_major', '未提供')}
面试类型：{form_data.get('scenario', '未提供')}
目标院校：{form_data.get('target_school', '未提供')}
目标导师：{form_data.get('target_advisor', '未提供')}
科研经历：{form_data.get('research_exp', '未提供')}
竞赛/论文：{form_data.get('competitions', '未提供')}
英语水平：{form_data.get('english_level', '未提供')}
自我介绍草稿：{form_data.get('self_intro_draft', '未提供')}
"""

    user_message = f"""
请分析以下考生信息，返回如下 JSON 结构：
{{
    "discipline": "学科归类（如 计算机科学与技术、信息与通信工程）",
    "subfields": ["子方向1", "子方向2", ...],
    "cross_discipline": true/false,
    "weak_points": ["薄弱点1", "薄弱点2", ...],
    "strong_points": ["优势1", "优势2", ...],
    "target_school_tier": "985/211/双非/未知",
    "interview_focus": ["面试应重点考察的方向1", "方向2", ...]
}}

考生信息：
{user_fields}
"""

    result = chat(
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    try:
        profile = json.loads(result["content"])
    except json.JSONDecodeError:
        profile = {
            "discipline": form_data.get("target_major", "未知"),
            "subfields": [],
            "cross_discipline": form_data.get("target_major") != form_data.get("undergrad_major"),
            "weak_points": [],
            "strong_points": [],
            "target_school_tier": "未知",
            "interview_focus": ["专业基础", "科研潜力"],
        }

    profile.setdefault("discipline", form_data.get("target_major", "未知"))
    profile.setdefault("subfields", [])
    profile.setdefault("cross_discipline", False)
    profile.setdefault("weak_points", [])
    profile.setdefault("strong_points", [])
    profile.setdefault("target_school_tier", "未知")
    profile.setdefault("interview_focus", [])

    return profile


def generate_question_pool(
    profile: dict,
    scenario_key: str,
    question_counts: list[int],
) -> dict:
    """
    根据画像 + 场景 + few-shot种子生成全部题库。
    返回: {"专业知识": [{"id": "q_001", "text": "...", "difficulty": "中"}, ...], ...}
    """
    scenario = get_scenario(scenario_key)
    dimensions = scenario["dimensions"]
    tone = scenario.get("interviewer_tone", "")

    question_pool = {}
    question_counter = [0]

    for i, dim in enumerate(dimensions):
        count = question_counts[i] if i < len(question_counts) else 3
        if count <= 0:
            question_pool[dim] = []
            continue

        seeds = get_seeds(scenario_key, dim, limit=5)
        seed_text = "\n".join([f"{j+1}. {s}" for j, s in enumerate(seeds)])

        system_prompt = (
            f"你是一位{tone}\n"
            f"现在你需要为考生准备「{dim}」环节的面试题。\n"
            f"考生画像：报考{profile.get('discipline', '未知')}专业，"
            f"目标{profile.get('target_school_tier', '')}院校。\n"
            f"优势：{', '.join(profile.get('strong_points', [])) or '暂无'}\n"
            f"薄弱：{', '.join(profile.get('weak_points', [])) or '暂无'}\n"
            f"面试重点：{', '.join(profile.get('interview_focus', [])) or '通用'}"
        )

        user_message = f"""
请为「{dim}」环节生成 {count} 道面试题。

以下是一些真实面试题供你参考风格和深度（不要照抄，要结合考生画像个性化）：

{seed_text}

返回 JSON 格式：
{{"questions": [{{"id": "q_xxx_001", "text": "题目内容", "difficulty": "易/中/难"}}, ...]}}

要求：
- 题目要结合考生具体专业方向（{profile.get('discipline', '')}）
- 如果考生填了科研经历，要为ta的科研经历设计针对性追问点
- 难度分布要合理：约20%简单、60%中等、20%偏难
"""

        result = chat(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.7,
            response_format={"type": "json_object"},
        )

        try:
            data = json.loads(result["content"])
            questions = data.get("questions", [])
        except json.JSONDecodeError:
            questions = []

        if len(questions) < count:
            for seed in seeds[len(questions):count]:
                questions.append({
                    "id": f"q_{dim}_{question_counter[0]:03d}",
                    "text": seed,
                    "difficulty": "中",
                })
                question_counter[0] += 1

        for idx, q in enumerate(questions):
            if "id" not in q or not q["id"]:
                q["id"] = f"q_{dim}_{question_counter[0]:03d}"
                question_counter[0] += 1

        question_pool[dim] = questions

    return question_pool


def replace_question(
    question_pool: dict,
    dimension: str,
    old_question_id: str,
    profile: dict,
    scenario_key: str,
) -> dict:
    """
    用户点击"换一题"时：删除旧题，AI生成新题，补入题库。
    返回: {"id": str, "text": str, "difficulty": str}
    """
    seeds = get_seeds(scenario_key, dimension, limit=3)
    seed_text = "\n".join([f"- {s}" for s in seeds])

    system_prompt = (
        "你是一位学术面试出题专家。请生成一道新的面试题。\n"
        f"考生报考{profile.get('discipline', '未知')}专业。"
    )

    user_message = f"""
请为「{dimension}」环节生成 1 道新的面试题。

参考风格（不要照抄）：
{seed_text}

返回 JSON：
{{"id": "q_new_001", "text": "题目内容", "difficulty": "中"}}

要求：不要和之前的题目重复，要换个角度或换个子方向来问。
"""

    result = chat(
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=0.8,
        response_format={"type": "json_object"},
    )

    try:
        data = json.loads(result["content"])
        new_question = {
            "id": data.get("id", f"q_new_{dimension}"),
            "text": data.get("text", seeds[0] if seeds else "请介绍一下你的专业背景。"),
            "difficulty": data.get("difficulty", "中"),
        }
    except json.JSONDecodeError:
        new_question = {
            "id": f"q_new_{dimension}",
            "text": seeds[0] if seeds else "请介绍一下你的研究兴趣。",
            "difficulty": "中",
        }

    if dimension in question_pool:
        question_pool[dimension] = [
            q for q in question_pool[dimension] if q["id"] != old_question_id
        ]
        question_pool[dimension].append(new_question)

    return new_question


def parse_resume(raw_text: str) -> dict:
    """
    AI 解析简历/自述文本，提取结构化表单字段。
    用于"智能导入"功能：用户上传简历或粘贴内容 → AI自动填充表单。

    返回: {
        "target_major": str,
        "undergrad_major": str,
        "research_exp": str,
        "competitions": str,
        "english_level": str,
        "self_intro_draft": str,
        "target_school": str,
        "target_advisor": str,
    }
    """
    system_prompt = (
        "你是一位专业的简历解析专家。请从以下文本中提取关键信息。"
        "如果某项信息在文本中没有提及，字段值留空字符串。"
        "只返回 JSON，不要有任何其他文字。"
    )

    user_message = f"""
请从以下简历/自述文本中提取信息，返回 JSON：

{{
    "target_major": "报考/申请的专业（如'信息与通信工程'）",
    "undergrad_major": "本科专业（如图'电子信息工程'）",
    "research_exp": "科研经历摘要（如'国家级大创，方向是图像分割，使用U-Net模型'。提取1-3段最相关的科研/项目经历）",
    "competitions": "竞赛/论文/获奖（如'数学建模省二等奖，IEEE论文1篇'）",
    "english_level": "英语水平（如'CET-6 520'或'雅思7.0'）",
    "self_intro_draft": "自我介绍的简要草稿（根据简历内容生成一段100字左右的自我介绍）",
    "target_school": "目标院校（如果文本中提到）",
    "target_advisor": "目标导师（如果文本中提到）"
}}

文本内容：
{raw_text[:3000]}
"""

    result = chat(
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    try:
        data = json.loads(result["content"])
    except json.JSONDecodeError:
        data = {}

    return {
        "target_major": data.get("target_major", ""),
        "undergrad_major": data.get("undergrad_major", ""),
        "research_exp": data.get("research_exp", ""),
        "competitions": data.get("competitions", ""),
        "english_level": data.get("english_level", ""),
        "self_intro_draft": data.get("self_intro_draft", ""),
        "target_school": data.get("target_school", ""),
        "target_advisor": data.get("target_advisor", ""),
    }
