import unittest
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


class LiteratureInterviewTests(unittest.TestCase):
    def _generated_payload(self, title="AI-generated cathode interface"):
        return {
            "title": title,
            "field": "电池材料",
            "text": (
                "High-voltage lithium-ion cathodes often suffer from interfacial reactions that "
                "increase impedance during cycling. In this study, a compositionally graded "
                "surface layer was formed on a nickel-rich layered oxide by a controlled annealing "
                "step. The gradient reduced the abrupt mismatch in lattice parameters between the "
                "bulk and the electrolyte-facing surface, while a small amount of dopant stabilized "
                "the oxygen sublattice. Operando diffraction indicated that the treated particles "
                "underwent a smaller anisotropic contraction during delithiation. Electrochemical "
                "tests showed improved capacity retention at elevated temperature, although the "
                "benefit diminished when the layer became too thick. The result suggests that "
                "surface composition, defect concentration and ionic transport should be optimized "
                "together rather than evaluated independently."
            ),
            "terms": [
                "high-voltage cathode", "interfacial reaction", "compositionally graded layer",
                "nickel-rich layered oxide", "lattice parameter", "oxygen sublattice",
                "anisotropic contraction", "delithiation", "capacity retention",
            ],
            "reference_translation": (
                "高电压锂离子电池正极在循环过程中容易发生界面反应并导致阻抗升高。"
                "本研究通过受控退火在富镍层状氧化物表面形成成分梯度层，缓解了体相与电解液接触表面之间的晶格参数突变，"
                "并通过少量掺杂稳定氧亚晶格。结果表明，表面成分、缺陷浓度和离子传输需要协同优化。"
            ),
        }

    def test_random_material_has_intermediate_length_and_material_terms(self):
        from modules.literature_interview import MATERIALS, get_random_material

        material = get_random_material()
        self.assertIn(material["id"], {item["id"] for item in MATERIALS})
        self.assertGreater(len(material["text"].split()), 100)
        self.assertGreaterEqual(len(material["terms"]), 6)
        self.assertTrue(material["reference_translation"])

    def test_random_material_can_exclude_previous_material(self):
        from modules.literature_interview import MATERIALS, get_random_material

        material = get_random_material(MATERIALS[0]["id"])
        self.assertNotEqual(material["id"], MATERIALS[0]["id"])

    def test_material_fields_are_unique_and_preserve_order(self):
        from modules.literature_interview import MATERIALS, list_material_fields

        fields = list_material_fields()
        self.assertEqual(fields, list(dict.fromkeys(item["field"] for item in MATERIALS)))

    def test_random_material_can_filter_by_field(self):
        from modules.literature_interview import get_random_material

        material = get_random_material(field="增材制造")
        self.assertEqual(material["field"], "增材制造")

    def test_unknown_field_falls_back_to_material_library(self):
        from modules.literature_interview import MATERIALS, get_random_material

        material = get_random_material(field="不存在的方向")
        self.assertIn(material["id"], {item["id"] for item in MATERIALS})

    def test_material_library_covers_core_materials_directions(self):
        from modules.literature_interview import list_material_fields

        fields = set(list_material_fields())
        self.assertTrue({"电子材料", "无机非金属材料", "陶瓷材料", "电池材料"}.issubset(fields))
        self.assertTrue({"高分子材料", "生物医用材料", "表面工程与腐蚀", "计算材料与模拟"}.issubset(fields))

    def test_generate_material_uses_ai_and_keeps_selected_field(self):
        from modules.literature_interview import generate_material

        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = Path(temp_dir) / "materials.jsonl"
            payload = self._generated_payload()
            with patch("modules.literature_interview.chat", return_value={"content": json.dumps(payload)}), patch(
                "modules.literature_interview._MATERIAL_HISTORY_PATH", history_path
            ):
                material = generate_material(field="电池材料")
            history = history_path.read_text(encoding="utf-8")

        self.assertEqual(material["field"], "电池材料")
        self.assertEqual(material["source"], "ai")
        self.assertTrue(material["id"].startswith("ai-"))
        self.assertGreater(len(material["text"].split()), 100)
        self.assertIn(material["title"], history)

    def test_generate_material_rejects_duplicate_and_requests_a_new_article(self):
        from modules.literature_interview import generate_material

        first = self._generated_payload("重复的电池界面研究")
        second = self._generated_payload("全新的电池热稳定性研究")
        second["text"] = second["text"].replace(
            "compositionally graded surface layer", "porous gradient coating"
        ).replace(
            "nickel-rich layered oxide", "lithium iron phosphate composite"
        ).replace(
            "oxygen sublattice", "electrochemical reaction network"
        ).replace(
            "elevated temperature", "fast charging conditions"
        )
        responses = [{"content": json.dumps(first)}, {"content": json.dumps(second)}]

        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = Path(temp_dir) / "materials.jsonl"

            def fake_chat(*args, **kwargs):
                return responses.pop(0)

            with patch("modules.literature_interview.chat", side_effect=fake_chat), patch(
                "modules.literature_interview._MATERIAL_HISTORY_PATH", history_path
            ):
                generated = generate_material(field="电池材料")
                generated_again = generate_material(field="电池材料", exclude_materials=[generated])

        self.assertNotEqual(generated["title"], generated_again["title"])
        self.assertEqual(generated_again["source"], "ai")

    def test_local_fallback_is_unseen_and_does_not_silently_repeat(self):
        from modules.literature_interview import MaterialGenerationError, create_material

        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "modules.literature_interview._MATERIAL_HISTORY_PATH",
            Path(temp_dir) / "materials.jsonl",
        ), patch.dict(
            os.environ,
            {"LITERATURE_GENERATION_ATTEMPTS": "1"},
        ), patch("modules.literature_interview.chat", side_effect=RuntimeError("offline")):
            first = create_material(field="电池材料")
            self.assertEqual(first["source"], "local-fallback")
            with self.assertRaises(MaterialGenerationError):
                create_material(field="电池材料", exclude_materials=[first])

    def test_each_material_has_sufficient_translation_content(self):
        from modules.literature_interview import MATERIALS

        for material in MATERIALS:
            self.assertGreater(len(material["text"].split()), 100, material["id"])
            self.assertGreaterEqual(len(material["terms"]), 8, material["id"])
            self.assertTrue(material["reference_translation"], material["id"])

    def test_reading_score_rewards_matching_text_and_reports_terms(self):
        from modules.literature_interview import MATERIALS, score_reading

        material = MATERIALS[0]
        result = score_reading(material["text"], material["text"], 60, material["terms"])
        self.assertGreaterEqual(result["score"], 90)
        self.assertEqual(result["coverage_score"], 100)
        self.assertEqual(result["term_score"], 100)
        self.assertGreater(result["words_per_minute"], 100)

    def test_reading_score_penalizes_empty_transcript(self):
        from modules.literature_interview import MATERIALS, score_reading

        result = score_reading(MATERIALS[0]["text"], "", 0, MATERIALS[0]["terms"])
        self.assertLess(result["score"], 40)
        self.assertTrue(result["missing_words"])

    def test_translation_evaluation_parses_json_and_clamps_scores(self):
        from modules.literature_interview import MATERIALS, evaluate_translation

        payload = '{"score": 108, "accuracy_score": 85, "terminology_score": 80, "completeness_score": 75, "expression_score": 70, "strengths": ["术语准确"]}'
        fake_client_result = {"content": payload}
        with patch("modules.literature_interview.chat", return_value=fake_client_result):
            result = evaluate_translation(MATERIALS[0], "晶界会影响金属性能。")
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["accuracy_score"], 85)
        self.assertEqual(result["reference_translation"], MATERIALS[0]["reference_translation"])
        self.assertTrue(result["strengths"])

    def test_translation_evaluation_has_fallback_when_api_fails(self):
        from modules.literature_interview import MATERIALS, evaluate_translation

        with patch("modules.literature_interview.chat", side_effect=RuntimeError("offline")):
            result = evaluate_translation(MATERIALS[0], "测试译文")
        self.assertEqual(result["score"], 0)
        self.assertTrue(result["reference_translation"])
        self.assertTrue(result["suggestions"])

    def test_countdown_component_emits_completion_event(self):
        source = (Path(__file__).resolve().parents[1] / "components" / "countdown" / "index.html").read_text(encoding="utf-8")
        self.assertIn("streamlit:componentReady", source)
        self.assertIn("streamlit:setComponentValue", source)
        self.assertIn('status:"complete"', source)
        self.assertIn("setInterval(draw", source)


if __name__ == "__main__":
    unittest.main()
