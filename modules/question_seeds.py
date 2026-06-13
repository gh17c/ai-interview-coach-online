"""
真实面经种子题库
================
从知乎、新东方、考研论坛等公开渠道收集的真实面试题，
按场景和维度分类，作为 AI 出题的 few-shot 风格引导。
每个维度取5条代表性题目注入 Prompt。
"""

SEEDS = {
    "postgraduate": {
        "专业知识": [
            "请解释[核心概念]的基本原理，并说明它在你报考专业中有哪些具体应用。",
            "对比[A]和[B]两种方法（或模型/协议/算法），分别说明适用场景和优缺点。",
            "本科所学的核心专业课中，你掌握最好的是哪一门？为什么？请举一个该课程中的重要知识点说明。",
            "请用简单的语言向非专业人士解释[专业概念]，你会怎么讲？",
            "你报考的专业领域最近有哪些技术热点或新进展？请选一个谈谈你的理解。",
            "在[专业方向]中，理论与工程实践之间的差距在哪里？你如何看待？",
            "本科期间做过的课程设计中，哪一个让你最有收获？请介绍设计思路和遇到的问题。",
            "如果你要给本科生讲一节关于[核心知识点]的课，你的讲课思路是什么？",
        ],
        "科研深挖": [
            "你的毕业论文（或毕业设计）研究的是什么问题？用了什么方法？得出什么结论？",
            "为什么选这个题目？有什么创新点？还有哪些不足之处？",
            "研究过程中遇到的最大困难是什么？你是怎么解决的？",
            "你的项目中用到了[技术A]，为什么选择它而不是[技术B]？做过对比实验吗？",
            "如果现在重新做这个项目，你会改进哪些地方？为什么？",
            "你的科研经历中，你觉得最有价值的一段是什么？你在其中扮演了什么角色？",
            "在你的大创/竞赛项目中，数据是怎么获取的？数据质量如何？样本量够不够？",
        ],
        "综合素养": [
            "为什么选择报考我们学校而不是其他学校？",
            "研究生期间你有什么具体的学习和科研计划？",
            "如果导师给你一个你不感兴趣的研究方向，你会怎么处理？",
            "你怎么看待研究生期间发表论文的压力？",
            "如果这次复试没有通过，你打算怎么办？",
            "你本科期间哪门课程成绩不理想？原因是什么？",
            "你觉得自己最大的优点和缺点分别是什么？",
            "你是否有读博的打算？为什么？",
            "如果和课题组的同学发生分歧，你会怎么处理？",
            "你对研究生生活有什么期待？又有哪些担心？",
        ],
        "英语考察": [
            "Please introduce yourself in about 2 minutes.",
            "Please describe your undergraduate research experience in English.",
            "Why do you choose our university and this major?",
            "What are your career plans after graduation?",
            "Please explain a key concept from your major in English.",
        ],
    },
    "summer_camp": {
        "自我介绍": [
            "请用2-3分钟做一个自我介绍，重点介绍你的学术背景和科研经历。",
            "请用英文做一个简短的自我介绍（1-2分钟）。",
        ],
        "科研深挖": [
            "请简要介绍你本科期间最有代表性的一段科研经历。",
            "在[项目名]中，你具体负责什么？做出了哪些贡献？",
            "你的论文/项目的创新点是什么？和已有研究相比有什么不同？",
            "研究过程中你遇到过什么挫折？你是如何调整和解决的？",
            "如果你有机会继续推进这个课题，你下一步会做什么？",
            "你对哪个研究方向最感兴趣？为什么？",
            "你有没有关注过我们学院哪位老师的研究？对他的哪个方向感兴趣？",
        ],
        "综合素养": [
            "你还参加了哪些学校的夏令营？如果都拿到offer你会怎么选？",
            "你今天面试的表现自己觉得怎么样？",
            "你觉得和其他优秀的营员相比，你的核心竞争力是什么？",
            "研究生阶段你有什么规划？是否考虑直博？",
            "你最大的优点和缺点是什么？请用具体的例子说明。",
            "你某门课程的成绩为什么偏低？",
            "你怎么看待科研中的失败？",
            "如果让你给本科低年级同学一条建议，你会说什么？",
        ],
        "英语考察": [
            "Please introduce yourself in 1-2 minutes.",
            "Please describe your research interests and why they matter.",
            "What's the most challenging course you've taken? Why?",
            "Please read and translate this abstract from English to Chinese.",
            "If you could work on any research topic, what would it be and why?",
        ],
    },
    "phd": {
        "研究计划": [
            "请简要介绍你的博士研究计划，包括研究问题、方法和预期贡献。",
            "你的研究计划创新点在哪里？和现有研究相比有什么不同？",
            "如果研究过程中关键假设不成立或者数据拿不到，你有什么备选方案？",
            "你的研究方向和你目标导师的现有课题如何衔接？有哪些结合点？",
            "你计划用什么研究方法？为什么选择这个方法而不是其他？",
            "你对博士期间的科研产出有什么预期？",
        ],
        "专业知识": [
            "介绍你所研究领域中一个经典的理论或模型，并评述其局限性。",
            "你硕士期间做的研究方向，目前国际上的前沿进展是什么？",
            "请解释[核心方法]的数学原理和适用条件。",
            "你在研究中用到的[技术X]，其底层原理是什么？",
            "如何看待你所在领域目前存在的主要争议或未解决的问题？",
            "你对AI在你研究领域中的应用有什么看法？",
        ],
        "综合素养": [
            "你为什么选择读博而不是直接工作？",
            "博士毕业后的职业规划是什么？",
            "你怎么看待博士生期间的心理压力？",
            "如果和导师在学术观点上有分歧，你会怎么处理？",
            "你觉得成为一位优秀的研究者需要哪些品质？你自己具备哪些？",
            "你是否有独立撰写基金申请或项目申请的经验？",
            "你的研究可能有什么社会影响或伦理问题？",
        ],
        "英语考察": [
            "Please present your research proposal in 3 minutes in English.",
            "Please describe your master's thesis and its main contributions.",
            "How do you see your research fitting into the international landscape?",
            "Please explain a key methodology from your field in English.",
            "What English academic journals do you regularly read?",
        ],
    },
}


def get_seeds(scenario_key: str, dimension: str, limit: int = 5) -> list[str]:
    """
    获取指定场景和维度的种子题目，用于few-shot注入。
    """
    scenario_seeds = SEEDS.get(scenario_key, {})
    seeds = scenario_seeds.get(dimension, [])
    return seeds[:limit]
