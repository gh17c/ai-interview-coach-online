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
    "pre_recommendation": {
        "key": "pre_recommendation",
        "name": "预推免综合面试",
        "dimensions": [
            "自我介绍与报考动机",
            "科研/项目深挖",
            "专业基础与学术思维",
            "综合素质与压力面",
            "英语交流与反问",
        ],
        "default_question_counts": [1, 4, 4, 3, 3],
        "interviewer_tone": (
            "你是一位参加预推免综合面试的教授组成员，代表目标院系进行正式考核。"
            "面试流程要接近真实预推免：开场自我介绍，核验科研与项目经历，考察专业基础和学术思维，"
            "追问报考动机、院校匹配度、抗压与沟通，再进行英文交流和考生反问。"
            "语气专业、克制、有追问压力但保持公平；每次只问一个问题，先听清回答再针对细节追问。"
            "重点核验考生本人真正做了什么，识别模板化表达、夸大贡献和对目标院系缺乏了解的情况。"
        ),
        "evaluation_focus": (
            "预推免综合面试特别关注：自我介绍是否聚焦学术潜力；科研贡献是否真实具体；"
            "专业基础能否迁移到新问题；回答是否有证据、结构和个人判断；对目标院系和研究方向是否匹配；"
            "在压力追问下是否诚实、稳定、可沟通；英文表达是否能完成基本学术交流。"
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

# 文献翻译模式使用独立的流程，不参与画像页的普通题库生成；保留场景
# 配置是为了历史记录和顶部信息栏可以正确显示名称。
LITERATURE_TRANSLATION_SCENARIO = {
    "key": "literature_translation",
    "name": "预推免英文文献翻译面试",
    "dimensions": ["英文朗读", "中文口译"],
    "default_question_counts": [1, 1],
    "interviewer_tone": "正式、简洁，关注材料科学术语和科学逻辑。",
    "follow_up_max_depth": 0,
}


def get_scenario(key: str) -> dict:
    """获取指定场景配置，不存在则返回考研复试默认"""
    if key == "literature_translation":
        return LITERATURE_TRANSLATION_SCENARIO
    return SCENARIOS.get(key, SCENARIOS["postgraduate"])


def list_scenarios() -> list[dict]:
    """列出所有场景摘要"""
    return [
        {
            "key": k,
            "name": v["name"],
            "dimensions": v["dimensions"],
            "description": v.get("evaluation_focus", ""),
        }
        for k, v in SCENARIOS.items()
    ]
