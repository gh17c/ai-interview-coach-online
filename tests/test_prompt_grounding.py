import json
import unittest
from unittest.mock import patch


class PromptGroundingTests(unittest.TestCase):
    def test_question_generation_prompt_contains_resume_evidence_and_variety_rules(self):
        from modules.profiler import generate_question_pool

        captured = []

        def fake_chat(**kwargs):
            captured.append(kwargs)
            return {
                "content": json.dumps({"questions": [{"id": "q1", "text": "请说明你在项目中的具体贡献。", "difficulty": "中"}]}),
                "usage": {},
                "cost": 0,
            }

        profile = {
            "discipline": "材料科学与工程",
            "target_school_tier": "985",
            "research_exp": "负责Fe3O4@EGaIn磁流体制备与SEM/TEM表征",
            "high_score_courses": "材料科学基础（95）；材料物理性能（92）",
            "competitions": "全国大学生混凝土材料设计大赛一等奖",
            "strong_points": ["实验操作"],
            "weak_points": [],
            "interview_focus": [],
        }
        with patch("modules.profiler.chat", side_effect=fake_chat):
            generate_question_pool(profile, "pre_recommendation", [1, 1, 1, 1, 1])

        prompts = "\n".join(call["user_message"] + call["system_prompt"] for call in captured)
        self.assertIn("Fe3O4@EGaIn", prompts)
        self.assertIn("材料科学基础", prompts)
        self.assertIn("不得假设", prompts)
        self.assertIn("刁难", prompts)


if __name__ == "__main__":
    unittest.main()
