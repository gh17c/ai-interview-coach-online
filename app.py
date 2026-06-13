"""
CLI 测试入口
============
用于快速测试各模块是否正常工作，无需启动 Streamlit。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.api_client import chat, reset_cost, get_total_cost, get_total_tokens
from modules.scenarios import get_scenario, list_scenarios
from modules.question_seeds import get_seeds, SEEDS

print("=" * 60)
print("🧪 AI 学术面试教练 — 模块连通性测试")
print("=" * 60)

# 1. 场景配置
print("\n📋 [1/5] 场景配置测试")
for s in list_scenarios():
    scenario = get_scenario(s["key"])
    print(f"   ✅ {scenario['name']}: {len(scenario['dimensions'])} 个维度 → {' → '.join(scenario['dimensions'])}")

# 2. 种子题库
print("\n📚 [2/5] 种子题库测试")
for key in SEEDS:
    for dim in SEEDS[key]:
        seeds = get_seeds(key, dim, limit=3)
        print(f"   ✅ {key}/{dim}: {len(seeds)} 条种子 → '{seeds[0][:40]}...'")

# 3. API连通性（需要配置.env中的API Key）
print("\n🤖 [3/5] DeepSeek API 连通性测试")
try:
    result = chat(
        system_prompt="你是一个有帮助的助手。用一句话回复。",
        user_message="你好，请确认连接正常。",
        temperature=0.1,
    )
    content = result["content"][:60]
    tokens = result["usage"]["total_tokens"]
    cost = result["cost"]
    print(f"   ✅ API 连通正常！回复: '{content}' | Tokens: {tokens} | 费用: ¥{cost:.6f}")
except Exception as e:
    print(f"   ❌ API 连接失败: {e}")
    print("   请检查 .env 文件中的 DEEPSEEK_API_KEY 是否正确配置。")

# 4. 画像分析测试
print("\n🔍 [4/5] 画像分析测试")
from modules.profiler import analyze_profile

test_form = {
    "target_major": "信息与通信工程",
    "undergrad_major": "电子信息工程",
    "scenario": "postgraduate",
    "target_school": "华中科技大学",
    "research_exp": "参与国家级大创，方向是图像分割，使用U-Net模型",
    "competitions": "数学建模省二等奖",
    "english_level": "CET-6 520",
}
try:
    profile = analyze_profile(test_form)
    print(f"   ✅ 学科: {profile.get('discipline')}")
    print(f"   ✅ 跨专业: {profile.get('cross_discipline')}")
    print(f"   ✅ 子方向: {profile.get('subfields')}")
    print(f"   ✅ 优势: {profile.get('strong_points')}")
    print(f"   ✅ 薄弱: {profile.get('weak_points')}")
except Exception as e:
    print(f"   ❌ 画像分析失败: {e}")

# 5. 费用统计
print("\n💰 [5/5] 费用统计")
cost = get_total_cost()
tokens = get_total_tokens()
print(f"   累计费用: ¥{cost:.6f}")
print(f"   累计Token: 输入={tokens['prompt']}, 输出={tokens['completion']}, 合计={tokens['prompt']+tokens['completion']}")

print("\n" + "=" * 60)
print("✅ 全部测试完成！")
print("=" * 60)
print("\n💡 启动网页界面: streamlit run app_ui.py")
