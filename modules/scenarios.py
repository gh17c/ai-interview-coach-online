"""面试场景配置 — 定义考研/保研/博士三种场景的参数"""

SCENARIOS = {
    "postgraduate": {
        "key": "postgraduate",
        "name": "考研复试",
        "dimensions": ["专业知识", "科研深挖", "综合素养", "英语考察"],
        "default_question_counts": [6, 4, 4, 2],
        "interviewer_tone": (
            "你是一位严谨但不压迫的研究生导师，担任考研复试面试官。"
            "你侧重考察考生的专业基础扎实度、科研潜力和读研动机。"
        ),
        "follow_up_max_depth": 2,
    },
    "summer_camp": {
        "key": "summer_camp",
        "name": "保研夏令营",
        "dimensions": ["自我介绍", "科研深挖", "综合素养", "英语考察"],
        "default_question_counts": [1, 5, 3, 3],
        "interviewer_tone": (
            "你是一位友善、开放的教授，担任保研夏令营面试官。"
            "你侧重考察学生的学术潜力、思维活跃度和沟通表达能力。"
            "面试氛围轻松对话式，不要施加过大压力。"
        ),
        "follow_up_max_depth": 2,
    },
    "phd": {
        "key": "phd",
        "name": "博士申请面试",
        "dimensions": ["研究计划", "专业知识", "综合素养", "英语考察"],
        "default_question_counts": [3, 5, 3, 3],
        "interviewer_tone": (
            "你是一位学术严谨、追问深入的博士生导师，担任博士申请面试官。"
            "你侧重考察申请者的独立研究能力、学术创新性和学术规划。"
            "对于研究计划中的漏洞会深入追问，追问可达3轮。"
        ),
        "follow_up_max_depth": 3,
    },
}


def get_scenario(key: str) -> dict:
    """获取指定场景配置，不存在则返回考研复试默认"""
    return SCENARIOS.get(key, SCENARIOS["postgraduate"])


def list_scenarios() -> list[dict]:
    """列出所有场景摘要"""
    return [
        {"key": k, "name": v["name"], "dimensions": v["dimensions"]}
        for k, v in SCENARIOS.items()
    ]
