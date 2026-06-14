"""
面试智库 — 基于学术文献的面试知识
===============================
每次展示随机抽取2-3条，避免信息过载。
所有洞察基于已验证的真实文献。
"""

import random

INSIGHTS = [
    {
        "title": "为什么AI模拟面试有效？",
        "body": (
            "**Krashen (1985)** 提出'情感过滤假说'：焦虑会阻碍学习，低压力环境促进吸收。"
            "Drexel大学研究 (Gomez et al., 2025) 发现 **60%** 的受访者在AI模拟面试后信心显著提升，"
            "80% 认为AI对话自然。AI提供的'无评判空间'正是降低情感过滤的关键。\n\n"
            "> 📖 Krashen SD. *The Input Hypothesis*. Longman, 1985.\n"
            "> 📖 Gomez N et al. *Virtual Interviewers, Real Results*. CSCW 2025. arXiv:2506.16542"
        ),
    },
    {
        "title": "面试中的追问艺术",
        "body": (
            "Virginia Tech的Conversate系统 (Daryanto et al., 2025) 发现：**对话式反馈**比单向评价更有效。"
            "追问不是刁难，而是给考生展示深度思考的机会。好的追问应当：\n"
            "- 引用考生回答中的具体细节\n"
            "- 引导考生从'是什么'走向'为什么'\n"
            "- 避免空洞的'请详细说说'\n\n"
            "> 📖 Daryanto T et al. *Conversate*. PACMHCI Vol.9, 2025. DOI:10.1145/3701188"
        ),
    },
    {
        "title": "STAR法则：结构化回答的黄金标准",
        "body": (
            "ETS (教育考试服务中心) 的研究 (Leong et al., 2024) 表明，面试评分中**逻辑结构**的权重"
            "不亚于内容本身。推荐 STAR 法则组织回答：\n"
            "- **S**ituation（情境）：当时面临什么情况？\n"
            "- **T**ask（任务）：你需要完成什么？\n"
            "- **A**ction（行动）：你具体做了什么？\n"
            "- **R**esult（结果）：取得了什么成果？用数据说话\n\n"
            "> 📖 Leong CW et al. *Combining Generative and Discriminative AI...* ICMI 2024."
        ),
    },
    {
        "title": "个性化反馈的价值",
        "body": (
            "微1公司的Zara系统 (Yazdani et al., 2025) 研究4,820场面试发现："
            "**个性化、结构化的反馈**使技术问题质量从8.38提升到8.60。关键要素：\n"
            "- 2-3条具体优点（引用回答细节）\n"
            "- 2-3条具体改进点（附示例）\n"
            "- 示范回答作为参考基准\n\n"
            "> 📖 Yazdani N et al. *Zara: An LLM-based Candidate Interview Feedback System*. arXiv:2507.02869"
        ),
    },
    {
        "title": "学术面试 vs 求职面试",
        "body": (
            "韩国Fiterview系统 (Lee et al., 2026) 专门针对**大学入学面试**设计，"
            "发现学术面试与求职面试有三个核心差异：\n"
            "1. **科研潜力 > 工作经验** — 教授更关心你能不能做研究\n"
            "2. **学科前沿敏感度** — 你是否了解最近3年的领域进展\n"
            "3. **读研动机的真诚度** — '为什么读研'比'为什么来我们公司'更需要深思\n\n"
            "> 📖 Lee C et al. *Fiterview*. JICS Vol.27(1), 2026. DOI:10.7472/jksii.2026.27.1.221"
        ),
    },
    {
        "title": "形成性反馈的力量",
        "body": (
            "Shute (2008) 在教育研究综述中总结：**形成性反馈**（告知如何改进，而非仅打分）"
            "是提升学习效果最有效的方式之一。这解释了为什么单题练习模式的有效性：\n"
            "- 即时反馈 → 立即修正 → 巩固\n"
            "- 延迟反馈 → 遗忘 → 重复错误\n\n"
            "> 📖 Shute VJ. *Focus on Formative Feedback*. Review of Educational Research, 78(1), 2008."
        ),
    },
    {
        "title": "压力面试的边界",
        "body": (
            "ETS研究发现，适度的追问压力有助于考察真实能力，但**过度施压适得其反**。"
            "好的面试官应：\n"
            "- 追问但不刁难\n"
            "- 指出漏洞但给考生解释的机会\n"
            "- 在反问环节切换回平等对话模式\n\n"
            "这正是本系统追问深度按场景分级设计（考研≤2轮，博士≤3轮）的理论依据。"
        ),
    },
    {
        "title": "英语面试：不要追求完美",
        "body": (
            "大连理工大学研面鸭团队的调研发现，导师在英语面试中最看重的是：\n"
            "1. **能基本沟通** 而非发音标准（占70%）\n"
            "2. **能用英语解释专业概念** 而非日常英语流利度（占20%）\n"
            "3. **敢开口** 的态度比语法正确更重要\n\n"
            "建议：准备3-5个专业术语的英文解释，而非背诵大段自我介绍。\n\n"
            "> 📖 大连理工大学未来技术学院. *研面鸭AI产品手册*. 2026."
        ),
    },
]


def get_random_insights(count: int = 2) -> list[dict]:
    """随机获取N条面试洞察，每次展示不同内容。"""
    return random.sample(INSIGHTS, min(count, len(INSIGHTS)))
