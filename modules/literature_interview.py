"""预推免英文文献翻译面试的材料、朗读评分与翻译评价。"""

import json
import hashlib
import os
import random
import re
import time
from difflib import SequenceMatcher
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from modules.api_client import chat


_MATERIAL_HISTORY_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "literature_material_history.jsonl"
)
_TRANSIENT_API_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504, 520, 521, 522, 524}


class MaterialGenerationError(RuntimeError):
    """AI 文献生成失败且没有安全的不重复本地材料可用。"""


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
    {
        "id": "electronic-thin-film",
        "title": "Defect engineering in oxide semiconductor thin films",
        "field": "电子材料",
        "text": (
            "Oxide semiconductor thin films are promising for transparent transistors because they combine optical transparency with relatively high carrier mobility. "
            "Their electrical behavior is strongly affected by oxygen vacancies and by the roughness of the dielectric interface. In this work, an indium-free zinc tin oxide film was deposited by solution processing and then annealed under different oxygen partial pressures. "
            "Annealing in a mildly oxidizing atmosphere reduced the concentration of deep defect states and lowered the off-state current. However, excessive oxidation also decreased the carrier concentration and slowed the switching response. "
            "The results show that defect control must be balanced with carrier transport rather than optimized by maximizing oxygen content alone. Interface passivation further improved bias stability during prolonged operation."
        ),
        "terms": ["oxide semiconductor", "thin film", "carrier mobility", "oxygen vacancies", "dielectric interface", "oxygen partial pressure", "defect states", "off-state current", "carrier concentration", "interface passivation"],
        "reference_translation": "氧化物半导体薄膜兼具光学透明性和较高的载流子迁移率，因此适用于透明晶体管。其电学行为会受到氧空位以及介电层界面粗糙度的显著影响。本研究采用溶液法沉积无铟锌锡氧化物薄膜，并在不同氧分压下进行退火。温和的氧化气氛能够降低深能级缺陷态的浓度和关态电流；但氧化过度也会降低载流子浓度，使开关响应变慢。结果表明，缺陷调控需要与载流子输运相平衡，而不能只追求更高的含氧量。界面钝化还提高了器件长时间工作时的偏压稳定性。",
    },
    {
        "id": "inorganic-glass",
        "title": "Strength and durability of alkali-activated inorganic binders",
        "field": "无机非金属材料",
        "text": (
            "Alkali-activated binders can use industrial by-products to produce cementless construction materials with lower process emissions. Their performance depends on the dissolution of the precursor, the chemistry of the activating solution and the development of a continuous gel network. "
            "A series of binders was prepared from granulated slag with different silicate-to-hydroxide ratios. Increasing the silicate fraction initially accelerated strength development because more polymeric species were available for gel formation. "
            "When the solution became too viscous, nevertheless, mixing defects and entrapped pores increased. Specimens exposed to wet-dry cycles retained most of their compressive strength, while specimens stored in a concentrated sulfate solution showed surface decalcification. "
            "These observations indicate that mixture design and curing humidity should be considered together when durability is evaluated."
        ),
        "terms": ["alkali-activated binder", "industrial by-products", "process emissions", "precursor", "activating solution", "gel network", "silicate-to-hydroxide ratio", "polymeric species", "compressive strength", "sulfate solution"],
        "reference_translation": "碱激发胶凝材料可以利用工业副产物制备低工艺排放的无水泥建筑材料。其性能取决于前驱体的溶解、激发溶液的化学组成以及连续凝胶网络的形成。研究人员以粒化炉渣为原料，制备了具有不同硅酸盐与氢氧化物比例的胶凝材料。提高硅酸盐比例起初会加快强度发展，因为体系中有更多聚合物种类参与凝胶形成；但当溶液黏度过高时，搅拌缺陷和残留孔隙会增加。经历干湿循环后，试样仍保留了大部分抗压强度，而在高浓度硫酸盐溶液中养护的试样出现了表面脱钙。这说明评价耐久性时，应同时考虑配比设计和养护湿度。",
    },
    {
        "id": "advanced-ceramic",
        "title": "Thermal shock resistance of porous silicon nitride ceramics",
        "field": "陶瓷材料",
        "text": (
            "Porous silicon nitride ceramics are attractive for thermal protection and filtration because they retain strength at high temperature while providing a low-density structure. The main challenge is to introduce connected pores without creating an easy path for catastrophic fracture. "
            "In this study, pore formers with two particle sizes were blended with silicon nitride powder and removed during firing. The bimodal pore structure increased permeability and reduced the mismatch between the ceramic skeleton and the surrounding gas. "
            "After repeated heating and cooling, samples with a narrow pore-size distribution developed long cracks, whereas the bimodal samples mainly showed stable microcrack growth. Mechanical strength still decreased as total porosity increased, but the loss was smaller when the pore walls were reinforced by elongated beta-silicon nitride grains. "
            "The results emphasize that pore connectivity, pore size distribution and grain morphology must be designed together."
        ),
        "terms": ["porous silicon nitride", "thermal protection", "low-density structure", "pore former", "bimodal pore structure", "permeability", "thermal shock", "pore-size distribution", "microcrack", "grain morphology"],
        "reference_translation": "多孔氮化硅陶瓷在高温下仍能保持强度，同时具有低密度结构，因此适用于热防护和过滤。其主要难点是在引入连通孔隙的同时，避免形成导致灾难性断裂的易裂通道。本研究将两种粒径的造孔剂与氮化硅粉末混合，并在烧结过程中将其去除。双峰孔结构提高了渗透率，降低了陶瓷骨架与周围气体之间的不匹配。反复加热和冷却后，孔径分布较窄的试样形成了长裂纹，而双峰结构试样主要表现为稳定的微裂纹扩展。总孔隙率增加仍会降低强度，但当孔壁由细长的β-氮化硅晶粒增强时，强度损失较小。结果强调，孔隙连通性、孔径分布和晶粒形貌需要协同设计。",
    },
    {
        "id": "lithium-battery-cathode",
        "title": "Surface stabilization of high-nickel lithium-ion cathodes",
        "field": "电池材料",
        "text": (
            "High-nickel layered oxide cathodes offer high specific capacity for lithium-ion batteries, but their surfaces can react with the electrolyte during charging to a high voltage. This reaction produces an unstable interphase, releases oxygen and accelerates transition-metal dissolution. "
            "A thin phosphate coating was applied to the cathode particles by a wet-chemical route. The coating was sufficiently continuous to suppress direct contact with the electrolyte, yet thin enough to preserve lithium-ion diffusion. "
            "Electrochemical tests showed a smaller impedance increase and better capacity retention after 200 cycles at elevated temperature. Post-mortem microscopy revealed fewer surface cracks and less rock-salt reconstruction. If the coating was made too thick, however, the initial rate capability decreased because lithium transport became sluggish. "
            "Therefore, surface modification should be optimized by considering both interfacial stability and ion-transport resistance."
        ),
        "terms": ["high-nickel layered oxide", "specific capacity", "electrolyte", "interphase", "oxygen release", "transition-metal dissolution", "phosphate coating", "lithium-ion diffusion", "capacity retention", "surface crack", "rock-salt reconstruction"],
        "reference_translation": "高镍层状氧化物正极为锂离子电池提供了较高的比容量，但在高电压充电时，其表面可能与电解液发生反应。这种反应会形成不稳定的界面膜，释放氧气，并加速过渡金属溶出。研究人员通过湿化学方法在正极颗粒表面制备了薄磷酸盐涂层。该涂层足够连续，可以抑制正极与电解液的直接接触，同时又足够薄，不会阻碍锂离子扩散。电化学测试表明，在高温下循环200次后，涂层样品的阻抗增长更小，容量保持率更高。循环后的显微观察还发现表面裂纹和岩盐相重构减少。然而，涂层过厚会使锂离子传输变慢，导致初始倍率性能下降。因此，表面改性必须同时考虑界面稳定性和离子传输阻力。",
    },
    {
        "id": "polymer-composite",
        "title": "Reversible crosslinking in recyclable polymer composites",
        "field": "高分子材料",
        "text": (
            "Thermoset polymers provide dimensional stability and chemical resistance, but their permanent crosslinked networks make mechanical recycling difficult. A recyclable epoxy was designed with exchangeable ester bonds that can rearrange when a catalyst is activated. "
            "Glass fibers were incorporated to improve stiffness, and the composite was cured at a temperature compatible with conventional processing. Tensile testing showed that the initial modulus was comparable to that of a commercial epoxy, while fracture toughness increased because the reversible bonds dissipated energy near a crack tip. "
            "When the composite was heated with a mild catalyst, the matrix softened without decomposing the fibers, allowing the reinforcement to be separated and reused. Recycled laminates retained most of their stiffness but showed a moderate reduction in interlaminar strength. "
            "The study demonstrates that molecular design can link durability during service with recoverability at the end of a product's life."
        ),
        "terms": ["thermoset polymer", "crosslinked network", "mechanical recycling", "exchangeable ester bond", "catalyst", "glass fiber", "fracture toughness", "crack tip", "interlaminar strength", "recoverability"],
        "reference_translation": "热固性聚合物具有尺寸稳定性和耐化学性，但其永久交联网络使机械回收变得困难。研究人员设计了一种含可交换酯键的可回收环氧树脂，在催化剂被激活时，这些酯键可以发生重排。为提高刚度，体系中加入了玻璃纤维，并在适合传统加工的温度下固化。拉伸测试表明，该复合材料的初始模量与商用环氧树脂相当；由于可逆键能够在裂纹尖端附近耗散能量，其断裂韧性有所提高。用温和催化剂加热时，基体软化但纤维不会分解，从而可以分离并重复使用增强体。回收后的层合板保留了大部分刚度，但层间强度有所下降。该研究说明，分子设计可以将服役期间的耐久性与产品寿命结束后的可回收性结合起来。",
    },
    {
        "id": "biomedical-implant",
        "title": "Surface modification of titanium for bone implants",
        "field": "生物医用材料",
        "text": (
            "Titanium alloys are widely used for bone implants because they combine high specific strength with good corrosion resistance. Nevertheless, a bare metallic surface does not always provide sufficient biological cues for rapid bone integration. In this study, a porous oxide layer was produced by electrochemical treatment and then functionalized with a calcium-phosphate coating. "
            "The porous layer increased the available surface area, while the ceramic coating improved wettability and promoted the attachment of osteoblast-like cells. Immersion tests in a simulated body fluid produced apatite deposits without a significant loss of coating adhesion. "
            "The treatment also reduced the release of metallic ions during a long-term corrosion test. Excessive porosity, however, weakened the surface and made it more vulnerable to fretting damage. "
            "The results suggest that implant design must balance biological activity, mechanical integrity and resistance to wear at the same interface."
        ),
        "terms": ["titanium alloy", "bone implant", "specific strength", "bone integration", "porous oxide layer", "electrochemical treatment", "calcium phosphate", "wettability", "osteoblast-like cell", "apatite", "fretting damage"],
        "reference_translation": "钛合金兼具较高的比强度和良好的耐腐蚀性，因此被广泛用于骨植入物。然而，裸露的金属表面并不总能为快速骨整合提供充分的生物学信号。本研究通过电化学处理制备多孔氧化层，然后在其表面构建磷酸钙涂层。多孔层增加了有效表面积，陶瓷涂层则改善了润湿性并促进成骨样细胞附着。在模拟体液中浸泡后，表面形成了磷灰石沉积，且涂层附着力没有明显降低。该处理还减少了长期腐蚀试验中的金属离子释放。但孔隙率过高会削弱表面，使其更容易发生微动磨损。结果表明，植入物设计需要在同一界面上平衡生物活性、机械完整性和耐磨性。",
    },
    {
        "id": "corrosion-coating",
        "title": "Self-healing coatings for corrosion protection",
        "field": "表面工程与腐蚀",
        "text": (
            "Organic coatings protect steel by separating the metal from water and aggressive ions, but scratches can create localized corrosion cells. A self-healing coating was prepared by embedding inhibitor-loaded microcapsules in an epoxy matrix. When a scratch ruptured the capsules, the inhibitor was released and reacted with the exposed steel surface. "
            "Electrochemical impedance measurements showed that the damaged coating recovered a substantial fraction of its barrier resistance after several hours in a saline environment. The healing response was faster at higher capsule concentrations, yet excessive capsules reduced adhesion and introduced weak interfaces. "
            "Microscopy confirmed that the released inhibitor formed a compact film near the defect rather than sealing the entire coating. Long-term immersion still revealed gradual loss of protection as the capsules were depleted. "
            "Therefore, practical self-healing systems require a compromise between local response, coating cohesion and the amount of stored inhibitor."
        ),
        "terms": ["organic coating", "localized corrosion", "self-healing coating", "microcapsule", "corrosion inhibitor", "epoxy matrix", "electrochemical impedance", "barrier resistance", "saline environment", "coating cohesion"],
        "reference_translation": "有机涂层通过隔绝水和侵蚀性离子来保护钢材，但划痕可能形成局部腐蚀电池。研究人员将装有缓蚀剂的微胶囊嵌入环氧树脂基体，制备了自修复涂层。当划痕使胶囊破裂时，缓蚀剂被释放并与裸露的钢表面反应。电化学阻抗测试显示，受损涂层在盐水环境中放置数小时后，屏蔽电阻恢复了相当一部分。提高胶囊浓度可以加快修复响应，但胶囊过多会降低附着力并引入弱界面。显微观察证实，释放出的缓蚀剂在缺陷附近形成致密膜，而不是封闭整个涂层。长期浸泡仍表明，随着胶囊逐渐耗尽，保护作用会慢慢减弱。因此，实用的自修复体系需要在局部响应、涂层内聚力和缓蚀剂储量之间取得平衡。",
    },
    {
        "id": "computational-materials",
        "title": "Combining simulation and experiments to design lightweight alloys",
        "field": "计算材料与模拟",
        "text": (
            "Computational materials design can narrow the search space before an alloy is produced, but predictions are useful only when they are connected to measurable microstructures. A combined workflow was used to screen aluminum-magnesium compositions with low density and improved yield strength. "
            "First-principles calculations estimated the stability of solute configurations, while a phase-field model predicted the size and spacing of precipitates during aging. Several compositions were then cast and characterized by electron microscopy and tensile testing. "
            "The experiments confirmed the predicted trend in precipitation density, although the absolute strength was lower than the calculation suggested because casting defects were not included in the model. Adding a defect-sensitive correction improved the agreement for later batches. "
            "This example shows that simulation should guide experiments iteratively, with uncertainty and processing history treated as part of the material design problem."
        ),
        "terms": ["computational materials design", "microstructure", "aluminum-magnesium alloy", "first-principles calculation", "solute configuration", "phase-field model", "precipitate", "electron microscopy", "casting defect", "uncertainty quantification"],
        "reference_translation": "计算材料设计可以在制备合金之前缩小搜索范围，但只有与可测量的微观结构联系起来，预测结果才具有实际价值。研究人员采用联合流程筛选铝镁合金成分，以获得低密度和较高屈服强度。首先利用第一性原理计算估算溶质构型的稳定性，再用相场模型预测时效过程中析出相的尺寸和间距。随后铸造并表征了多种成分，开展电子显微观察和拉伸测试。实验验证了析出密度的预测趋势，但实测强度低于计算结果，因为模型没有考虑铸造缺陷。加入对缺陷敏感的修正后，后续批次的预测与实验更加吻合。这个例子表明，模拟应当以迭代方式指导实验，同时要把不确定性和加工历史视为材料设计问题的一部分。",
    },
)


def list_material_fields() -> list[str]:
    """返回材料库中的方向，保持材料库定义顺序且去重。"""
    return list(dict.fromkeys(item["field"] for item in MATERIALS))


def _normalise_for_comparison(value: object) -> str:
    """Normalize article text/title for exact and near-duplicate detection."""
    text = re.sub(r"\s+", " ", str(value or "").strip().lower())
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", text)


def material_fingerprint(material_or_text: object) -> str:
    """Return a stable fingerprint without exposing article content."""
    if isinstance(material_or_text, dict):
        value = material_or_text.get("text", "")
    else:
        value = material_or_text
    normalized = _normalise_for_comparison(value)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _read_material_history(path: Optional[Path] = None, limit: int = 120) -> list[dict]:
    """Read prior generated materials, tolerating a missing/corrupt log."""
    history_path = Path(path or _MATERIAL_HISTORY_PATH)
    try:
        lines = history_path.read_text(encoding="utf-8").splitlines()
    except (FileNotFoundError, OSError, UnicodeError):
        return []
    records: list[dict] = []
    for line in lines[-max(1, int(limit)) :]:
        try:
            record = json.loads(line)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(record, dict) and (record.get("text") or record.get("fingerprint")):
            records.append(record)
    return records


def _record_material(material: dict, path: Optional[Path] = None) -> None:
    """Persist a generated article so a later app session can avoid it."""
    history_path = Path(path or _MATERIAL_HISTORY_PATH)
    try:
        history_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": material.get("source", "ai"),
            "id": material.get("id", ""),
            "title": material.get("title", ""),
            "field": material.get("field", ""),
            "text": material.get("text", ""),
            "fingerprint": material_fingerprint(material),
        }
        with history_path.open("a", encoding="utf-8") as history_file:
            history_file.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        # Persistence is best-effort; the in-memory session check still
        # protects the current run when the data folder is read-only.
        return


def _as_material_records(materials: Optional[Iterable[object]]) -> list[dict]:
    records: list[dict] = []
    for item in materials or []:
        if isinstance(item, dict):
            records.append(item)
        elif item:
            records.append({"text": str(item)})
    return records


def _is_duplicate_material(candidate: dict, previous_materials: Optional[Iterable[object]] = None) -> bool:
    """Detect exact, title, or very-near text duplicates."""
    candidate_fp = material_fingerprint(candidate)
    candidate_title = _normalise_for_comparison(candidate.get("title", ""))
    candidate_text = _normalise_for_comparison(candidate.get("text", ""))
    for previous in _as_material_records(previous_materials):
        if candidate_fp and candidate_fp == str(previous.get("fingerprint", "")):
            return True
        if candidate.get("id") and candidate.get("id") == previous.get("id"):
            return True
        previous_title = _normalise_for_comparison(previous.get("title", ""))
        if candidate_title and previous_title and candidate_title == previous_title:
            return True
        previous_text = _normalise_for_comparison(previous.get("text", ""))
        if candidate_text and previous_text and SequenceMatcher(None, candidate_text, previous_text).ratio() >= 0.94:
            return True
    return False


def _history_prompt_summary(history: Iterable[dict], limit: int = 24) -> str:
    summaries: list[str] = []
    for item in list(history)[-limit:]:
        title = str(item.get("title") or "").strip()
        text = re.sub(r"\s+", " ", str(item.get("text") or "").strip())
        if title or text:
            summaries.append(f"- {title}: {text[:110]}")
    return "\n".join(summaries) or "（暂无历史材料）"


def _error_status_code(error: Exception) -> Optional[int]:
    for candidate in (
        getattr(error, "status_code", None),
        getattr(getattr(error, "response", None), "status_code", None),
    ):
        try:
            if candidate is not None:
                return int(candidate)
        except (TypeError, ValueError):
            continue
    match = re.search(r"\b(4\d\d|5\d\d)\b", str(error or ""))
    return int(match.group(1)) if match else None


def _generation_retry_limit() -> int:
    try:
        return max(0, min(4, int(os.getenv("LITERATURE_GENERATION_RETRIES", "2"))))
    except (TypeError, ValueError):
        return 2


def _generation_attempt_limit() -> int:
    try:
        return max(1, min(5, int(os.getenv("LITERATURE_GENERATION_ATTEMPTS", "3"))))
    except (TypeError, ValueError):
        return 3


def _is_transient_generation_error(error: Exception) -> bool:
    return _error_status_code(error) in _TRANSIENT_API_STATUS_CODES or type(error).__name__ in {
        "APITimeoutError",
        "APIConnectionError",
    }


def _response_format_unsupported(error: Exception) -> bool:
    message = str(error or "").lower()
    return "response_format" in message and any(
        marker in message
        for marker in ("unknown", "unsupported", "unexpected", "invalid", "extra", "not allowed")
    )


def _call_generation_model(system_prompt: str, user_message: str, model: Optional[str] = None) -> dict:
    """Call the configured chat model with short retries for provider outages."""
    selected_model = model or os.getenv("LITERATURE_MODEL") or os.getenv("DEEPSEEK_MODEL") or "deepseek-chat"
    retry_limit = _generation_retry_limit()
    last_error: Optional[Exception] = None
    for attempt in range(retry_limit + 1):
        try:
            try:
                return chat(
                    system_prompt,
                    user_message,
                    temperature=0.85,
                    model=selected_model,
                    response_format={"type": "json_object"},
                    max_tokens=1100,
                )
            except Exception as exc:
                # Older OpenAI-compatible gateways may reject JSON mode while
                # still returning ordinary text. Retry once without that
                # optional parameter before treating the model as unavailable.
                if _response_format_unsupported(exc):
                    return chat(
                        system_prompt,
                        user_message,
                        temperature=0.85,
                        model=selected_model,
                        max_tokens=1100,
                    )
                raise
        except Exception as exc:
            last_error = exc
            if not _is_transient_generation_error(exc) or attempt >= retry_limit:
                raise
            time.sleep(min(3.0, 0.5 * (2**attempt)))
    raise last_error or RuntimeError("文献生成没有返回响应")


def _parse_generation_json(content: object) -> dict:
    text = str(content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError, json.JSONDecodeError):
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("模型未返回 JSON 文献对象")
        try:
            parsed = json.loads(text[start : end + 1])
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("模型返回的文献 JSON 无法解析") from exc
    if isinstance(parsed, dict) and isinstance(parsed.get("material"), dict):
        parsed = parsed["material"]
    if not isinstance(parsed, dict):
        raise ValueError("模型返回的文献不是 JSON 对象")
    return parsed


def _normalise_generated_material(raw: dict, requested_field: str = "") -> dict:
    title = re.sub(r"\s+", " ", str(raw.get("title") or "").strip()).strip("\"'")
    text = re.sub(r"\s+", " ", str(raw.get("text") or "").strip())
    reference = re.sub(r"\s+", " ", str(raw.get("reference_translation") or "").strip())
    field = str(requested_field or raw.get("field") or "材料科学与工程").strip()
    terms_value = raw.get("terms") or []
    if isinstance(terms_value, str):
        terms_value = re.split(r"[,，;；、]\s*", terms_value)
    terms: list[str] = []
    for term in terms_value if isinstance(terms_value, (list, tuple)) else []:
        normalized = re.sub(r"\s+", " ", str(term or "").strip())
        if normalized and normalized not in terms:
            terms.append(normalized)
    english_word_count = len(re.findall(r"[A-Za-z]+", text))
    if len(title) < 8:
        raise ValueError("文献标题过短")
    if english_word_count < 100:
        raise ValueError("文献正文过短，至少需要约 100 个英文单词")
    if len(terms) < 6:
        raise ValueError("材料专业术语不足")
    if len(reference) < 40:
        raise ValueError("参考译文过短")
    fingerprint = material_fingerprint(text)
    return {
        "id": f"ai-{fingerprint[:16]}",
        "title": title,
        "field": field,
        "text": text,
        "terms": terms[:20],
        "reference_translation": reference,
        "difficulty": "中等",
        "source": "ai",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def generate_material(
    field: str = "",
    exclude_materials: Optional[Iterable[object]] = None,
    model: Optional[str] = None,
) -> dict:
    """Ask the model for a fresh article in ``field`` and persist its fingerprint.

    The function never silently returns a duplicate: invalid, repeated or
    unavailable responses are retried with a changed angle, then surfaced as
    ``MaterialGenerationError`` for the UI to handle.
    """
    requested_field = str(field or "").strip()
    previous = _read_material_history()
    previous.extend(_as_material_records(exclude_materials))
    system_prompt = (
        "你是材料科学与工程专业的预推免英文文献面试材料命题人。"
        "只生成适合一分钟准备、中文口译的原创英文科研短文，不要引用或改写已有论文原文。"
        "文章需要有研究背景、材料/方法、关键结果和局限或工程启示，语言难度中等，"
        "使用准确的材料学术语和清晰的因果/转折关系。必须严格输出 JSON，不要 Markdown。"
    )
    last_error: Optional[Exception] = None
    for attempt in range(_generation_attempt_limit()):
        nonce = f"{random.randrange(10**9):09d}"
        recent_summary = _history_prompt_summary(previous)
        user_message = (
            f"请生成一段全新的材料学英文文献，目标方向：{requested_field or '材料科学与工程（从常见方向中随机选择）'}。\n"
            "正文约 130–180 个英文单词，标题简洁。返回字段：title、field、text、terms（至少8个英文术语）、"
            "reference_translation（中文参考译文）。不要生成与以下历史材料相同或高度相似的标题、主题、句式或数据：\n"
            f"{recent_summary}\n本次生成随机标识：{nonce}。"
        )
        candidate: Optional[dict] = None
        try:
            response = _call_generation_model(system_prompt, user_message, model=model)
            candidate = _normalise_generated_material(
                _parse_generation_json(response.get("content") if isinstance(response, dict) else response),
                requested_field=requested_field,
            )
            if _is_duplicate_material(candidate, previous):
                raise ValueError("模型生成了重复或高度相似的文献")
            _record_material(candidate)
            return candidate
        except Exception as exc:
            last_error = exc
            # Keep the rejected candidate/history in the next prompt and ask
            # for a genuinely different angle on the next attempt.
            if candidate:
                previous.append(candidate)
            continue
    detail = str(last_error or "未知错误").strip()
    raise MaterialGenerationError(
        "AI 文献生成暂时失败，未返回可用且不重复的材料。"
        "请稍后重试；若持续出现，请检查硅基流动模型状态和额度。"
        f"（{detail[:160]}）"
    ) from last_error


def get_unseen_fallback_material(
    field: str = "", exclude_materials: Optional[Iterable[object]] = None
) -> dict:
    """Return an unused bundled article for an API-outage fallback.

    The selected direction is kept strict.  If every bundled article in that
    direction has already been used, raise instead of silently repeating one.
    """
    previous = _read_material_history()
    previous.extend(_as_material_records(exclude_materials))
    candidates = [
        item
        for item in MATERIALS
        if (not field or item["field"] == field) and not _is_duplicate_material(item, previous)
    ]
    if not candidates:
        raise MaterialGenerationError(
            f"“{field or '材料科学与工程'}”方向的备用材料已经用完，且 AI 暂时不可用；请稍后重试。"
        )
    return dict(random.choice(candidates))


def create_material(
    field: str = "",
    exclude_materials: Optional[Iterable[object]] = None,
    model: Optional[str] = None,
) -> dict:
    """Generate a fresh AI article, with a strict no-repeat local fallback."""
    try:
        return generate_material(field=field, exclude_materials=exclude_materials, model=model)
    except MaterialGenerationError as generation_error:
        fallback = get_unseen_fallback_material(field=field, exclude_materials=exclude_materials)
        fallback["source"] = "local-fallback"
        fallback["generation_error"] = str(generation_error)
        return fallback


def get_random_material(
    exclude_id: str = "",
    field: str = "",
    exclude_ids: Optional[Iterable[str]] = None,
    exclude_fingerprints: Optional[Iterable[str]] = None,
) -> dict:
    """按方向随机返回本地材料，可排除当前会话已使用的材料。"""
    blocked_ids = {str(item) for item in (exclude_ids or []) if item}
    if exclude_id:
        blocked_ids.add(str(exclude_id))
    blocked_fingerprints = {str(item) for item in (exclude_fingerprints or []) if item}
    candidates = [
        item for item in MATERIALS
        if (not field or item["field"] == field)
        and item["id"] not in blocked_ids
        and material_fingerprint(item) not in blocked_fingerprints
    ]
    if not candidates:
        candidates = [
            item for item in MATERIALS
            if (not field or item["field"] == field)
            and (not blocked_ids or item["id"] not in blocked_ids)
        ]
    if not candidates:
        # If a single direction has been exhausted, prefer an unseen article
        # from another direction rather than returning the same article again.
        candidates = [
            item
            for item in MATERIALS
            if item["id"] not in blocked_ids
            and material_fingerprint(item) not in blocked_fingerprints
        ]
    if not candidates:
        candidates = list(MATERIALS)
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
