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
    "pre_recommendation": {
        "自我介绍与报考动机": [
            "请用2分钟做自我介绍，重点说明与你申请方向最相关的经历。",
            "为什么选择我们学校、这个专业和这个研究方向？请说出具体了解。",
            "如果只能保留一项经历放在面试开场，你会选哪一项？为什么？",
            "你认为自己相比其他申请者最有竞争力的地方是什么？请用事实证明。",
            "你对未来研究生阶段最想解决的一个学术问题是什么？",
        ],
        "科研/项目深挖": [
            "请介绍一项你亲自参与的科研或项目经历，并明确说明你本人负责了什么。",
            "你在项目中做出的关键决策是什么？如果不这样做，结果会怎样？",
            "你的实验或结论有哪些证据支持？数据、基线和评价指标是否充分？",
            "项目中最困难的一步是什么？你如何定位问题并验证解决方案？",
            "如果继续做这个课题，你会优先改进哪一处？为什么？",
            "请区分项目中你独立完成、与他人合作以及仅了解的部分。",
        ],
        "专业基础与学术思维": [
            "请解释一个本专业核心概念，并说明它在实际研究中的适用边界。",
            "比较两种常见方法的假设、优点和局限；如果条件改变，你会如何选择？",
            "遇到一个你没有见过的新问题时，你会如何拆解、查资料并验证判断？",
            "请谈谈你最近关注的本专业前沿问题，以及你认为仍未解决的地方。",
            "如果实验结果与预期相反，你会先检查哪些环节？",
            "请把一个专业问题讲给非本专业的面试老师听，要求准确且易懂。",
        ],
        "综合素质与压力面": [
            "如果导师安排的研究方向与你的兴趣不一致，你会如何沟通和行动？",
            "你的成绩单中哪门课表现不理想？原因是什么，之后如何补救？",
            "如果我们质疑你在项目中的贡献被夸大了，你会如何回应？",
            "同时拿到多个学校的预推免机会时，你会用哪些标准做选择？",
            "请说一个你被批评或失败的经历，以及它如何改变了你的做法。",
            "当你无法按期完成科研任务时，你会如何向导师汇报？",
        ],
        "英语交流与反问": [
            "Please introduce yourself and your research interests in about two minutes.",
            "Please describe your most important research or project experience in English.",
            "What is the most challenging problem you have solved, and what did you learn?",
            "Please explain a core concept from your major to a non-specialist professor.",
            "What would you like to ask our lab or department before making your decision?",
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
