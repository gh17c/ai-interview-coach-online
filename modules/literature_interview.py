"""预推免英文文献翻译面试的材料、朗读评分与翻译评价。"""

import json
import random
import re
from difflib import SequenceMatcher
from typing import Optional

from modules.api_client import chat


MATERIALS = (
    {
        "id": "grain-boundary",
        "title": "Grain-boundary engineering in stainless steel",
        "field": "金属材料与热处理",
        "text": (
            "Grain boundaries strongly influence the mechanical and corrosion behavior of "
            "polycrystalline metals. In this study, austenitic stainless steel was subjected "
            "to a moderate cold-rolling process followed by solution treatment. The treatment "
            "increased the fraction of low-energy grain boundaries and reduced the number of "
            "sites where corrosion pits could initiate. Tensile tests showed that the yield "
            "strength decreased slightly after annealing, whereas elongation improved markedly. "
            "These results indicate that grain-boundary engineering can provide a useful balance "
            "between corrosion resistance and ductility for structural applications. The benefit "
            "was most obvious when the material was tested in a chloride solution, suggesting "
            "that boundary connectivity matters in addition to the average grain size."
        ),
        "terms": ["grain boundary", "austenitic stainless steel", "cold rolling", "solution treatment", "corrosion pits", "yield strength", "elongation", "ductility"],
        "reference_translation": "晶界会显著影响多晶金属的力学性能和耐腐蚀行为。本研究对奥氏体不锈钢进行了适度冷轧，随后进行固溶处理。该处理提高了低能晶界的比例，并减少了腐蚀点蚀可能萌生的位置。拉伸试验表明，退火后屈服强度略有降低，而延伸率明显提高。这些结果说明，晶界工程能够在结构材料应用中实现耐腐蚀性与延性的有益平衡。",
    },
    {
        "id": "additive-manufacturing",
        "title": "Porosity control in laser powder bed fusion",
        "field": "增材制造",
        "text": (
            "Laser powder bed fusion is widely used to manufacture metal components with complex "
            "geometries. However, pores formed during processing may reduce fatigue life. Here, "
            "the laser power and scanning speed were varied to study their effect on an aluminum "
            "alloy. A low energy density produced lack-of-fusion defects because adjacent tracks "
            "did not overlap sufficiently. Excessive energy density, in contrast, caused keyhole "
            "pores and evaporation of alloying elements. The best samples were obtained within an "
            "intermediate processing window, where the melt pool was stable and relative density "
            "exceeded 99.5 percent. Microscopy further showed that the remaining defects were "
            "small and isolated rather than connected into long cracks. This processing window "
            "therefore provides a practical starting point for improving fatigue performance."
        ),
        "terms": ["laser powder bed fusion", "fatigue life", "scanning speed", "energy density", "lack-of-fusion defects", "keyhole pores", "alloying elements", "melt pool", "relative density"],
        "reference_translation": "激光粉末床熔融被广泛用于制造几何形状复杂的金属构件。然而，加工过程中形成的孔隙可能降低疲劳寿命。本文改变激光功率和扫描速度，研究其对一种铝合金的影响。较低的能量密度会因相邻熔道重叠不足而产生未熔合缺陷；相反，过高的能量密度会导致匙孔孔隙及合金元素挥发。最佳样品位于中等工艺窗口内，此时熔池稳定、相对致密度超过99.5%。",
    },
    {
        "id": "ceramic-composite",
        "title": "Interface design in ceramic-matrix composites",
        "field": "复合材料",
        "text": (
            "Ceramic-matrix composites are attractive for high-temperature applications because "
            "they retain stiffness at temperatures beyond the capability of many metal alloys. "
            "Their fracture behavior is controlled by the interface between the fiber and the "
            "matrix. A weak interface can deflect cracks and allow fibers to pull out, which "
            "improves damage tolerance. If the interface is too weak, however, load transfer to "
            "the fibers becomes inefficient. In the present work, a thin boron nitride coating "
            "was deposited on silicon carbide fibers. The coating improved interfacial control "
            "and increased the work of fracture without a large loss of tensile strength. The "
            "result also demonstrates why interface chemistry and coating thickness must be "
            "optimized together instead of treating the interface as simply strong or weak."
        ),
        "terms": ["ceramic-matrix composites", "high-temperature applications", "fiber", "matrix", "interface", "crack deflection", "fiber pull-out", "damage tolerance", "load transfer", "work of fracture"],
        "reference_translation": "陶瓷基复合材料适用于高温环境，因为在超过许多金属合金承受能力的温度下仍能保持刚度。其断裂行为受纤维与基体之间界面的控制。较弱的界面能够使裂纹偏转并允许纤维拔出，从而提高损伤容限；但界面过弱又会使载荷难以有效传递给纤维。本研究在碳化硅纤维上沉积了薄层氮化硼涂层。该涂层改善了界面调控，在拉伸强度没有显著损失的条件下提高了断裂功。",
    },
    {
        "id": "phase-transformation",
        "title": "Precipitation strengthening of an aluminum alloy",
        "field": "相变与强化",
        "text": (
            "Precipitation strengthening is an effective method for improving the strength of "
            "heat-treatable aluminum alloys. After solution treatment and quenching, the alloy "
            "was aged at 180 degrees Celsius for different times. Fine precipitates formed during "
            "the early stage of aging and hindered dislocation motion. As a result, hardness and "
            "ultimate tensile strength increased. Prolonged aging led to coarsening of the "
            "precipitates, which reduced their ability to block dislocations. This overaged state "
            "showed lower strength but better electrical conductivity. Therefore, the aging time "
            "should be selected according to the intended balance of properties. In practice, "
            "the optimum condition is often chosen after comparing hardness, conductivity and "
            "long-term dimensional stability rather than maximizing strength alone."
        ),
        "terms": ["precipitation strengthening", "solution treatment", "quenching", "aging", "precipitates", "dislocation motion", "ultimate tensile strength", "overaged state", "electrical conductivity"],
        "reference_translation": "析出强化是提高可热处理铝合金强度的有效方法。固溶处理和淬火后，研究人员将合金在180摄氏度下进行不同时长的时效。时效早期形成的细小析出相会阻碍位错运动，因此硬度和抗拉强度提高。时效时间过长会使析出相粗化，削弱其阻碍位错的能力。过时效状态强度较低，但导电性更好。因此，应根据所需的性能平衡选择时效时间。",
    },
)


def get_random_material(exclude_id: str = "") -> dict:
    """返回一段原创、适合中等难度预推免翻译环节的材料。"""
    candidates = [item for item in MATERIALS if item["id"] != exclude_id] or list(MATERIALS)
    return dict(random.choice(candidates))


def _words(text: str) -> list[str]:
    # Treat hyphenated compounds such as ``cold-rolling`` as the same two
    # words that a speech recognizer commonly returns.
    return re.findall(r"[a-z]+|\d+(?:\.\d+)?", (text or "").lower())


def score_reading(source_text: str, transcript: str, duration_seconds: float = 0.0, terms: Optional[list[str]] = None) -> dict:
    """基于语音转写计算朗读完整度与流畅度，不做音素级发音判断。"""
    expected = _words(source_text)
    actual = _words(transcript)
    expected_set = set(expected)
    actual_set = set(actual)
    overlap = len(expected_set & actual_set) / max(len(expected_set), 1)
    sequence = SequenceMatcher(None, expected, actual).ratio()
    matched_terms = [term for term in (terms or []) if all(word in actual_set for word in _words(term))]
    term_coverage = len(matched_terms) / max(len(terms or []), 1)
    words_per_minute = len(actual) * 60 / duration_seconds if duration_seconds > 0 else 0.0
    speed_score = 1.0 if 75 <= words_per_minute <= 185 else max(0.35, 1 - abs(words_per_minute - 130) / 160) if words_per_minute else 0.45
    score = round(min(100, max(0, 55 * overlap + 20 * sequence + 15 * term_coverage + 10 * speed_score)))
    missing = [word for word in expected if word not in actual_set]
    return {
        "score": score,
        "coverage_score": round(overlap * 100),
        "sequence_score": round(sequence * 100),
        "term_score": round(term_coverage * 100),
        "speed_score": round(speed_score * 100),
        "words_per_minute": round(words_per_minute),
        "recognized_words": len(actual),
        "expected_words": len(expected),
        "matched_terms": matched_terms,
        "missing_words": list(dict.fromkeys(missing))[:12],
    }


def evaluate_translation(material: dict, translation: str) -> dict:
    """通过模型评价中文口译结果，并在模型异常时提供可用的回退报告。"""
    system_prompt = (
        "你是材料科学与工程专业的预推免面试官，正在评估英文文献口译。"
        "评分严格、可解释，但不要求逐字直译。重点考察科学含义、逻辑关系、材料术语和信息完整性。"
        "不要因语音转写的少量标点问题过度扣分，也不要虚构原文没有的信息。"
    )
    user_message = (
        f"材料方向：{material['field']}\n英文原文：\n{material['text']}\n\n"
        f"关键术语：{', '.join(material['terms'])}\n\n考生口译转写：\n{translation}\n\n"
        "返回 JSON：{\n"
        '"score":0-100整数,"accuracy_score":0-100,"terminology_score":0-100,"completeness_score":0-100,"expression_score":0-100,'
        '"strengths":["具体优点"],"omissions":["漏译或误译；没有则说明无重大遗漏"],'
        '"terminology_feedback":["术语建议"],"suggestions":["可执行改进建议"],"reference_translation":"参考译文"\n}'
    )
    fallback = {
        "score": 0,
        "accuracy_score": 0,
        "terminology_score": 0,
        "completeness_score": 0,
        "expression_score": 0,
        "strengths": ["已完成口译提交。"],
        "omissions": ["模型评价暂时不可用，请稍后重试。"],
        "terminology_feedback": [],
        "suggestions": ["对照参考译文复盘术语和逻辑关系。"],
        "reference_translation": material["reference_translation"],
    }
    try:
        result = chat(system_prompt, user_message, temperature=0.2, response_format={"type": "json_object"}, max_tokens=1200)
        evaluation = json.loads(result["content"])
        if not isinstance(evaluation, dict):
            raise ValueError("模型返回的评价不是 JSON 对象")
    except (ValueError, RuntimeError, json.JSONDecodeError, TypeError, KeyError):
        return fallback
    for key, value in fallback.items():
        evaluation.setdefault(key, value)
    for key in ("score", "accuracy_score", "terminology_score", "completeness_score", "expression_score"):
        try:
            evaluation[key] = max(0, min(100, int(evaluation[key])))
        except (TypeError, ValueError):
            evaluation[key] = 0
    return evaluation
