"""
AI 学术面试教练 — Streamlit 前端
================================
页面状态机：profile → mode_select → interview → report
"""

import sys
import os
import time
import random
import hashlib
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import streamlit.components.v1 as components

from modules.scenarios import get_scenario, list_scenarios
from modules.profiler import analyze_profile, generate_question_pool, replace_question, parse_resume
from modules.document_parser import DocumentParseError, extract_document_text
from modules.interviewer import (
    start_interview, ask_next_question, decide_follow_up, generate_transition,
    start_reverse_questioning, respond_to_candidate_question, close_interview,
)
from modules.evaluator import evaluate_answer, generate_full_report
from modules.history import save_session, list_sessions, load_session, delete_session, log_pool_generation
from modules.knowledge_base import get_random_insights
from modules.voice import transcribe_audio


st.set_page_config(page_title="AI 学术面试教练", page_icon="🎓", layout="wide")

DEFAULTS = {
    "page": "profile", "mode": None, "scenario_key": "pre_recommendation",
    "profile": None, "question_pool": None, "question_counts": [6, 4, 4, 2],
    "messages": [], "interview_state": None, "used_question_ids": set(),
    "report": None, "single_practice_dim": None, "single_practice_count": 0,
    "profile_step": "fill",
    "voice_audio_hash": "",
    "voice_transcript": "",
    "voice_last_spoken_id": "",
    "smart_import_processed_id": "",
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

if isinstance(st.session_state.used_question_ids, list):
    st.session_state.used_question_ids = set(st.session_state.used_question_ids)


with st.sidebar:
    st.title("🎓 AI 学术面试教练")
    st.divider()

    # 使用按钮代替 radio——按钮是主动点击才触发，不会在每次rerun时自动复位
    if st.button("📋 新建面试", use_container_width=True, key="nav_new"):
        for key in DEFAULTS:
            if key != "page":
                st.session_state[key] = DEFAULTS[key]
        st.session_state.page = "profile"
        st.rerun()

    in_flow_pages = {"mode_select", "interview", "report"}
    if st.session_state.page not in in_flow_pages:
        if st.button("📚 历史记录", use_container_width=True, key="nav_history"):
            st.session_state.page = "history_list"
            st.rerun()

    # ===== 面试中途：Prompt透传面板 =====
    if st.session_state.page == "interview" and st.session_state.mode == "full_simulation":
        st.divider()
        with st.expander("🔬 AI 思考面板", expanded=False):
            is_followup = st.session_state.interview_state.get("follow_up_round", 0) > 0
            phase = st.session_state.interview_state.get("phase", "")
            if phase == "opening":
                st.markdown("**当前 Prompt：开场白生成**\n\nAI 被设定为场景面试官角色，生成自然的开场介绍。")
                st.caption("温度：0.7 | 策略：角色扮演")
            elif is_followup:
                st.markdown("**当前 Prompt：追问决策**\n\nAI 先总结你对上一问的回答，判断是否有逻辑漏洞/缺少例子/值得深入，再决定追问或放行。")
                st.caption("温度：0.6 | 策略：Chain-of-Thought + 结构化JSON输出")
            elif phase in ("reverse_questioning", "reverse_answering"):
                st.markdown("**当前 Prompt：反问环节**\n\nAI 以面试官身份真诚回答考生提问，适当展示课题组优势但不夸大。")
                st.caption("温度：0.7 | 策略：角色扮演")
            else:
                st.markdown("**当前 Prompt：智能出题**\n\nAI 结合题库话题提示 + 对话上下文 + 已讨论话题黑名单，动态生成不重复的面试题。")
                st.caption("温度：0.7 | 策略：Few-shot引导 + 防重复约束")

    # 面试中途退出按钮
    if st.session_state.page == "interview":
        st.divider()
        if st.button("🚪 退出面试", use_container_width=True, key="nav_exit", type="secondary"):
            # 保存当前进度
            profile = st.session_state.profile or {}
            msgs = st.session_state.messages or []
            mode = st.session_state.mode or "full_simulation"
            scenario = st.session_state.scenario_key
            # 生成简化报告
            from modules.evaluator import generate_full_report
            try:
                report = generate_full_report(msgs, profile, scenario)
            except Exception:
                report = {"overall_score": 0, "dimension_scores": {},
                          "highlights": ["面试中途退出"], "improvements": [],
                          "per_question_feedback": [], "improvement_plan": []}
            save_session({"scenario": scenario, "mode": mode, "profile": profile,
                          "messages": msgs, "report": report})
            st.session_state.report = report
            st.session_state.page = "report"
            st.rerun()

    st.divider()
    st.caption(f"📍 当前：{st.session_state.page}")

    # ===== A: 面试智库 =====
    if st.session_state.page in ("profile", "mode_select"):
        st.divider()
        st.subheader("📚 面试智库")
        # 每次rerun随机展示2条不重复洞察
        if "kb_insights" not in st.session_state:
            st.session_state.kb_insights = get_random_insights(2)
        if st.button("🔄 换一批", key="kb_refresh"):
            st.session_state.kb_insights = get_random_insights(2)
        for ins in st.session_state.kb_insights:
            with st.expander(f"💡 {ins['title']}", expanded=False):
                st.markdown(ins["body"])


def _clear_voice_state():
    """清理上一道题的语音录音与识别结果。"""
    st.session_state.voice_audio_hash = ""
    st.session_state.voice_transcript = ""
    # 不在本次运行中修改已渲染的 text_area widget 状态；下一次录音时会覆盖它。


def _capture_voice_transcript(widget_key: str) -> tuple[str, bool]:
    """显示录音控件并返回识别文本，以及本次是否刚完成新的识别。"""
    audio = st.audio_input("🎙️ 录音回答（可选）", key=widget_key)
    newly_transcribed = False

    if audio is not None:
        audio_bytes = audio.getvalue()
        audio_hash = hashlib.sha256(audio_bytes).hexdigest()
        if audio_hash != st.session_state.get("voice_audio_hash", ""):
            try:
                with st.spinner("🎧 正在识别语音..."):
                    transcript = transcribe_audio(audio_bytes, getattr(audio, "name", "answer.wav"))
                st.session_state.voice_audio_hash = audio_hash
                st.session_state.voice_transcript = transcript
                st.session_state.voice_transcript_edit = transcript
                newly_transcribed = True
                if transcript:
                    st.success("✅ 语音识别完成，可以修改后提交。")
                else:
                    st.warning(
                        "录音已上传，但语音识别返回空结果。请确认录音条有波形、"
                        "使用 Chrome/Edge，并用普通话靠近麦克风再录 5-15 秒。"
                    )
            except Exception as exc:
                st.session_state.voice_audio_hash = audio_hash
                st.session_state.voice_transcript = ""
                st.error(f"语音识别失败：{exc}")

    transcript = st.session_state.get("voice_transcript", "")
    if transcript:
        transcript = st.text_area(
            "语音识别结果（可修改）",
            key="voice_transcript_edit",
            height=110,
        )
    return transcript.strip(), newly_transcribed


def _speak_text(text: str):
    """调用浏览器内置语音合成朗读面试官文本。"""
    if not text:
        return
    safe_text = json.dumps(text, ensure_ascii=False).replace("</", "<\\/")
    components.html(
        f"""
        <script>
        const text = {safe_text};
        if ('speechSynthesis' in window) {{
          window.speechSynthesis.cancel();
          const utterance = new SpeechSynthesisUtterance(text);
          utterance.lang = 'zh-CN';
          utterance.rate = 0.95;
          utterance.pitch = 1.0;
          window.speechSynthesis.speak(utterance);
        }}
        </script>
        """,
        height=1,
    )


def _render_latest_speech(text_override: str = ""):
    """自动朗读最新面试官消息，并提供手动重播按钮。"""
    if text_override:
        content = text_override
    else:
        latest = next(
            (m for m in reversed(st.session_state.messages) if m.get("role") == "interviewer"),
            None,
        )
        if not latest:
            return
        content = latest.get("content", "")
    message_id = f"{len(st.session_state.messages)}:{content[:80]}"
    button_id = hashlib.sha1(message_id.encode("utf-8")).hexdigest()[:12]
    col1, col2 = st.columns([1, 5])
    with col1:
        replay = st.button("🔊 重播", key=f"speech_replay_{button_id}")
    with col2:
        st.caption("面试官语音播报已启用；也可以继续使用文字回答。")

    if replay or st.session_state.get("voice_last_spoken_id") != message_id:
        _speak_text(content)
        st.session_state.voice_last_spoken_id = message_id


def render_profile_page():
    st.title("📋 构建你的面试画像")

    # 初始化 step 状态
    if "profile_step" not in st.session_state:
        st.session_state.profile_step = "fill"

    # ===== 智能导入（选填）=====
    with st.expander("📎 智能导入（选填 — 上传简历或粘贴内容，AI 自动填充）", expanded=False):
        tab1, tab2 = st.tabs(["📄 粘贴文本", "📁 上传文件"])
        raw_text = None
        parse_requested = False

        with tab1:
            pasted = st.text_area(
                "粘贴简历或个人陈述内容",
                height=150,
                placeholder="粘贴你的简历文本、个人陈述、自我介绍等...\nAI 将自动提取专业、科研经历、竞赛、英语水平等信息并填入对应分区。",
                key="smart_paste",
            )
            if st.button("🤖 智能解析文本", key="btn_parse_paste", use_container_width=True):
                if pasted.strip():
                    raw_text = pasted
                    parse_requested = True

        with tab2:
            uploaded = st.file_uploader("上传简历文件", type=["pdf", "docx", "txt"], key="smart_file")
            if uploaded is not None:
                # 读取文件内容
                try:
                    file_bytes = uploaded.getvalue()
                    file_id = hashlib.sha256(file_bytes).hexdigest()
                    file_id = f"{uploaded.name.lower()}:{file_id}"
                    # Streamlit 会因任何输入框变化重新运行脚本；同一文件只触发一次 AI 解析。
                    if file_id != st.session_state.get("smart_import_processed_id", ""):
                        raw_text = extract_document_text(uploaded.name, file_bytes)
                        parse_requested = True
                        # 先登记本次尝试，网络/API 异常时也不会在用户编辑表单时重试。
                        # 用户移除后重新上传即可再次触发。
                        st.session_state.smart_import_processed_id = file_id
                except DocumentParseError as e:
                    st.warning(str(e))
                except Exception as e:
                    st.error(f"文件读取失败：{e}")
            else:
                st.session_state.smart_import_processed_id = ""

        if parse_requested and raw_text and raw_text.strip():
            with st.spinner("🤖 AI 正在解析你的信息..."):
                try:
                    parsed = parse_resume(raw_text)
                    # 直接注入 Streamlit 控件值（不能用 value= 参数，因为只在首次渲染生效）
                    st.session_state.f_target_major = parsed.get("target_major", "")
                    st.session_state.f_undergrad_major = parsed.get("undergrad_major", "")
                    st.session_state.f_target_school = parsed.get("target_school", "")
                    st.session_state.f_advisor = parsed.get("target_advisor", "")
                    st.session_state.f_research = parsed.get("research_exp", "")
                    st.session_state.f_competitions = parsed.get("competitions", "")
                    st.session_state.f_high_score_courses = parsed.get("high_score_courses", "")
                    st.session_state.f_english = parsed.get("english_level", "")
                    st.session_state.f_self_intro = parsed.get("self_intro_draft", "")
                    st.success("✅ 解析完成！已自动填充到下方表单，请检查并补充。")
                except Exception as e:
                    st.error(f"❌ 解析失败：{e}")

    st.divider()
    st.markdown("填写以下信息，AI 将为你生成**个性化面试题库**。越详细，题目越有针对性。")

    col1, col2 = st.columns(2)
    with col1:
        target_major = st.text_input("🎯 报考/申请专业 *", placeholder="如：信息与通信工程", key="f_target_major")
        undergrad_major = st.text_input("📖 本科专业 *", placeholder="如：电子信息工程", key="f_undergrad_major")
        scenario_list = list_scenarios()
        scenario_names = [s["name"] for s in scenario_list]
        current_scenario_key = st.session_state.get("scenario_key", "postgraduate")
        default_scenario_index = next(
            (i for i, item in enumerate(scenario_list) if item["key"] == current_scenario_key),
            0,
        )
        scenario_display = st.selectbox(
            "📝 面试类型 *",
            options=scenario_names,
            index=default_scenario_index,
            key="f_scenario_display",
        )
        scenario_map = {s["name"]: s["key"] for s in scenario_list}
        scenario_key = scenario_map.get(scenario_display, "postgraduate")
        selected_description = next(
            (s.get("description", "") for s in scenario_list if s["key"] == scenario_key),
            "",
        )
        if selected_description:
            st.caption(f"🎯 本场重点：{selected_description}")
        target_school = st.text_input("🏫 目标院校 *", placeholder="如：华中科技大学", key="f_target_school")

    with col2:
        target_advisor = st.text_input("👨‍🏫 目标导师（选填）", placeholder="导师姓名或研究方向", key="f_advisor")
        research_exp = st.text_area("🔬 科研经历（推荐填写）", placeholder="如：参与国家级大创，方向是图像分割，使用U-Net模型...", height=120, key="f_research")
        competitions = st.text_input("🏆 竞赛/论文（选填）", placeholder="如：数学建模省二等奖", key="f_competitions")
        high_score_courses = st.text_input(
            "📚 高分专业课（推荐填写）",
            placeholder="如：材料科学基础95，材料物理性能92",
            key="f_high_score_courses",
        )
        english_level = st.text_input("🇬🇧 英语水平（选填）", placeholder="如：CET-6 520", key="f_english")

    self_intro = st.text_area("✍️ 自我介绍草稿（选填，AI会据此出题）", placeholder="如果你已经有了自我介绍草稿，贴在这里...", height=100, key="f_self_intro")

    # ===== Step 1: 分析画像按钮 =====
    if st.session_state.profile_step == "fill":
        if st.button("🔍 分析我的面试画像", type="primary", use_container_width=True):
            if not target_major or not undergrad_major or not target_school:
                st.error("请填写必填项（标注 * 的字段）")
            else:
                try:
                    with st.spinner("🤖 AI 正在分析你的画像..."):
                        form_data = {
                            "target_major": target_major, "undergrad_major": undergrad_major,
                            "scenario": scenario_key, "target_school": target_school,
                            "target_advisor": target_advisor, "research_exp": research_exp,
                            "competitions": competitions, "english_level": english_level,
                            "high_score_courses": high_score_courses,
                            "self_intro_draft": self_intro,
                        }
                        profile = analyze_profile(form_data)
                        st.session_state.profile = profile
                        st.session_state.profile.update({
                            "target_major": target_major, "undergrad_major": undergrad_major,
                            "target_school": target_school, "target_advisor": target_advisor,
                        })
                    st.session_state.profile_step = "show_assessment"
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 分析失败：{e}")

    # ===== Step 2: 展示能力评估 + 题量设置 =====
    elif st.session_state.profile_step == "show_assessment":
        profile = st.session_state.profile or {}

        st.divider()
        st.subheader("🔬 AI 能力维度评估")

        # 用卡片展示各维度
        strong = profile.get("strong_points", [])
        weak = profile.get("weak_points", [])
        focus = profile.get("interview_focus", [])
        subfields = profile.get("subfields", [])

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("📚 学科方向", profile.get("discipline", "未知"))
        with c2:
            st.metric("🔄 跨专业", "是" if profile.get("cross_discipline") else "否")
        with c3:
            st.metric("🏫 院校层次", profile.get("target_school_tier", "未知"))
        with c4:
            st.metric("📌 关注维度", str(len(focus)))

        st.markdown("---")

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("### ✅ 优势")
            if strong:
                for s in strong:
                    st.markdown(f"- 🟢 {s}")
            else:
                st.caption("（信息不足，建议补充科研/竞赛经历）")

            if subfields:
                st.markdown("### 🧭 子方向")
                for sf in subfields:
                    st.markdown(f"- 📍 {sf}")

        with col_b:
            st.markdown("### ⚠️ 薄弱点")
            if weak:
                for w in weak:
                    st.markdown(f"- 🔴 {w}")
            else:
                st.caption("（信息不足）")

            if focus:
                st.markdown("### 🎯 建议面试侧重")
                for f in focus:
                    st.markdown(f"- 💡 {f}")

        st.divider()

        # 题量设置
        st.subheader("⚙️ 面试题量设置")
        scenario = get_scenario(scenario_key)
        dims = scenario["dimensions"]
        defaults = scenario["default_question_counts"]
        counts = []
        cols = st.columns(len(dims))
        for i, (dim, default) in enumerate(zip(dims, defaults)):
            with cols[i]:
                counts.append(cols[i].number_input(f"{dim}", min_value=0, max_value=15, value=default, step=1, key=f"count_{i}"))

        total_questions = sum(counts)
        est_time = total_questions * 3
        st.caption(f"📊 共计 **{total_questions}** 道题 · 预计面试时长 **{est_time}** 分钟")

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🔄 重新分析画像", use_container_width=True):
                st.session_state.profile_step = "fill"
                st.rerun()
        with col_btn2:
            if st.button("🚀 生成我的个性化题库", type="primary", use_container_width=True):
                try:
                    with st.spinner("📝 AI 正在生成个性化题目..."):
                        question_pool = generate_question_pool(profile, scenario_key, counts)
                        st.session_state.question_pool = question_pool
                        st.session_state.question_counts = counts
                        st.session_state.scenario_key = scenario_key
                    total = sum(len(v) for v in question_pool.values())
                    pool_summary = {dim: len(qs) for dim, qs in question_pool.items()}
                    log_pool_generation(profile, scenario_key, pool_summary)
                    st.success(f"✅ 题库生成完毕！共 **{total}** 道个性化题目，覆盖 {len(dims)} 个维度。")
                    st.session_state.profile_step = "fill"  # 重置步骤
                    st.session_state.page = "mode_select"
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 生成失败：{e}")
                    st.info("请检查网络连接，或尝试重新点击按钮。")


def render_mode_select_page():
    st.title("🎯 选择面试模式")
    if st.button("← 返回修改画像"):
        st.session_state.page = "profile"
        st.rerun()
    scenario = get_scenario(st.session_state.scenario_key)
    profile = st.session_state.profile or {}
    st.info(
        f"🎓 **{scenario['name']}** · {profile.get('target_school', '')} · "
        f"{profile.get('discipline', profile.get('target_major', ''))}  |  "
        f"题库已备好：共 **{sum(len(v) for v in st.session_state.question_pool.values())}** 题"
    )
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        ### 🎬 全模拟面试
        真实面试流程，AI 逐题提问并根据你的回答**动态追问**。
        - 🔄 逐维度推进
        - 🎯 AI 根据回答质量智能追问（1-2轮）
        - 📊 终场生成**完整诊断报告**
        - ⏱ 约 25-30 分钟
        """)
        if st.button("🎬 开始全模拟面试", type="primary", use_container_width=True):
            st.session_state.mode = "full_simulation"
            st.session_state.messages = []
            st.session_state.used_question_ids = set()
            st.session_state.interview_state = {
                "current_dim_idx": 0, "current_q_idx": 0,
                "follow_up_round": 0, "phase": "opening",
            }
            st.session_state.report = None
            st.session_state.page = "interview"
            with st.spinner("🤖 面试官准备中..."):
                opening = start_interview(st.session_state.scenario_key, profile)
                st.session_state.messages.append({
                    "role": "interviewer", "content": opening,
                    "dimension": None, "is_followup": False,
                })
            st.rerun()
    with col2:
        st.markdown("""
        ### 🎯 单题练习
        自由选题，每道题答完**即时获取评估**。
        - 🎲 随机从题库抽题，自由选择维度
        - 📊 提交后立即获得：评分 + 优缺点 + 示范回答
        - 🔗 提供**追问方向建议**
        - ⏱ 每道题约 5 分钟 · 不限次数
        """)
        if st.button("🎯 开始单题练习", type="primary", use_container_width=True):
            st.session_state.mode = "single_practice"
            st.session_state.messages = []
            st.session_state.used_question_ids = set()
            st.session_state.single_practice_dim = None
            st.session_state.single_practice_count = 0
            st.session_state.page = "interview"
            st.rerun()


def _render_top_bar():
    scenario = get_scenario(st.session_state.scenario_key)
    profile = st.session_state.profile or {}
    total_q = sum(st.session_state.question_counts)
    main_answers = sum(1 for m in st.session_state.messages if m["role"] == "user" and not m.get("is_followup_response", False))
    st.markdown(
        f"🎓 **{scenario['name']}** · {profile.get('target_school', '')} · "
        f"{profile.get('discipline', profile.get('target_major', ''))}  |  "
        f"📊 进度：约 {main_answers}/{total_q} 题  |  📝 对话：{len(st.session_state.messages)} 轮"
    )
    st.progress(min(main_answers / max(total_q, 1), 1.0))
    st.divider()


def render_full_simulation():
    _render_top_bar()
    state = st.session_state.interview_state
    scenario = get_scenario(st.session_state.scenario_key)
    dims = scenario["dimensions"]
    counts = st.session_state.question_counts
    profile = st.session_state.profile or {}

    for msg in st.session_state.messages:
        with st.chat_message("assistant" if msg["role"] == "interviewer" else "user"):
            st.write(msg["content"])

    _render_latest_speech()

    if state["phase"] == "done":
        if st.button("📊 生成诊断报告", type="primary", use_container_width=True):
            with st.spinner("🤖 AI 正在分析你的面试表现..."):
                report = generate_full_report(st.session_state.messages, profile, st.session_state.scenario_key)
                st.session_state.report = report
                st.session_state.page = "report"
                save_session({
                    "scenario": st.session_state.scenario_key, "mode": "full_simulation",
                    "profile": profile, "messages": st.session_state.messages, "report": report,
                })
            st.rerun()
        return

    voice_widget_key = (
        f"full_voice_{len(st.session_state.messages)}_"
        f"{state.get('phase', '')}_{state.get('current_dim_idx', 0)}_"
        f"{state.get('current_q_idx', 0)}"
    )
    voice_text, _ = _capture_voice_transcript(voice_widget_key)
    text_input = st.chat_input("输入你的回答...")
    voice_send = False
    if voice_text:
        voice_send = st.button(
            "📨 发送语音回答",
            type="primary",
            use_container_width=True,
            key=f"voice_send_{hashlib.sha1(voice_widget_key.encode()).hexdigest()[:12]}",
        )

    user_input = text_input or (voice_text if voice_send else None)
    if not user_input:
        return

    _clear_voice_state()

    dim_idx = state["current_dim_idx"]
    current_dim = dims[dim_idx] if dim_idx < len(dims) else None
    is_fu_resp = state["follow_up_round"] > 0

    st.session_state.messages.append({
        "role": "user", "content": user_input,
        "dimension": current_dim, "is_followup_response": is_fu_resp,
    })

    if state["phase"] == "opening":
        state["phase"] = "questioning"
        state["current_dim_idx"] = 0
        state["current_q_idx"] = 0
        state["follow_up_round"] = 0
        next_q = ask_next_question(
                    st.session_state.question_pool, dims[0],
                    st.session_state.used_question_ids,
                    st.session_state.messages,
                    st.session_state.profile or {},
                    st.session_state.scenario_key,
                )
        st.session_state.messages.append({
            "role": "interviewer", "content": next_q["question"],
            "dimension": next_q["dimension"], "is_followup": False,
            "question_id": next_q["question_id"],
        })
        st.rerun()

    elif state["phase"] in ("questioning", "followup"):
        last_q_msg = None
        for m in reversed(st.session_state.messages):
            if m["role"] == "interviewer" and m.get("dimension") == current_dim and not m.get("is_followup", False):
                last_q_msg = m
                break
        if last_q_msg is None:
            last_q_msg = {"content": current_dim or "当前题目"}

        decision = decide_follow_up(
            user_answer=user_input,
            current_question=last_q_msg["content"],
            interview_history=st.session_state.messages,
            scenario_key=st.session_state.scenario_key,
            round_number=state["follow_up_round"],
        )

        if decision["should_follow_up"]:
            state["follow_up_round"] += 1
            state["phase"] = "followup"
            st.session_state.messages.append({
                "role": "interviewer", "content": decision["follow_up_question"],
                "dimension": current_dim, "is_followup": True,
            })
            st.rerun()
        else:
            state["follow_up_round"] = 0
            state["current_q_idx"] += 1
            current_count = counts[dim_idx] if dim_idx < len(counts) else 0

            if state["current_q_idx"] >= current_count:
                state["current_dim_idx"] += 1
                state["current_q_idx"] = 0
                next_dim_idx = state["current_dim_idx"]

                if next_dim_idx >= len(dims):
                    # 进入反问环节
                    state["phase"] = "reverse_questioning"
                    reverse_q = start_reverse_questioning(st.session_state.scenario_key, profile)
                    st.session_state.messages.append({
                        "role": "interviewer", "content": reverse_q,
                        "dimension": "反问环节", "is_followup": False,
                    })
                    st.rerun()

                next_dim = dims[next_dim_idx]
                transition = generate_transition(
                    current_dim, next_dim, st.session_state.scenario_key,
                    st.session_state.messages,
                )
                st.session_state.messages.append({
                    "role": "interviewer", "content": transition,
                    "dimension": None, "is_followup": False,
                })
                state["phase"] = "questioning"
                first_q = ask_next_question(
                    st.session_state.question_pool, next_dim,
                    st.session_state.used_question_ids,
                    st.session_state.messages,
                    st.session_state.profile or {},
                    st.session_state.scenario_key,
                )
                st.session_state.messages.append({
                    "role": "interviewer", "content": first_q["question"],
                    "dimension": next_dim, "is_followup": False,
                    "question_id": first_q["question_id"],
                })
                st.rerun()
            else:
                state["phase"] = "questioning"
                if decision["transition_text"] and decision["transition_text"] != "好的，下一题。":
                    st.session_state.messages.append({
                        "role": "interviewer", "content": decision["transition_text"],
                        "dimension": current_dim, "is_followup": True,
                    })
                next_q = ask_next_question(
                    st.session_state.question_pool, current_dim,
                    st.session_state.used_question_ids,
                    st.session_state.messages,
                    st.session_state.profile or {},
                    st.session_state.scenario_key,
                )
                st.session_state.messages.append({
                    "role": "interviewer", "content": next_q["question"],
                    "dimension": next_q["dimension"], "is_followup": False,
                    "question_id": next_q["question_id"],
                })
                st.rerun()

    # ===== 反问环节 =====
    elif state["phase"] in ("reverse_questioning", "reverse_answering"):
        # 用户输入可能是提问，也可能是"没有了"
        user_text = user_input.strip()
        no_more_keywords = ["没有了", "没有", "没问题", "没啦", "无", "谢谢老师", "暂时没有", "没了"]
        is_done = any(kw in user_text for kw in no_more_keywords) and len(user_text) < 15

        if is_done:
            # 反问环节结束
            closing = close_interview(st.session_state.scenario_key)
            st.session_state.messages.append({
                "role": "interviewer", "content": closing,
                "dimension": "反问环节", "is_followup": False,
            })
            state["phase"] = "done"
            st.rerun()
        else:
            # AI回答考生的问题
            answer = respond_to_candidate_question(
                user_input, st.session_state.scenario_key,
                profile, st.session_state.messages,
            )
            st.session_state.messages.append({
                "role": "interviewer", "content": answer,
                "dimension": "反问环节", "is_followup": True,
            })
            state["phase"] = "reverse_answering"
            st.rerun()


def render_single_practice():
    _render_top_bar()
    scenario = get_scenario(st.session_state.scenario_key)
    dims = scenario["dimensions"]

    selected_dim = st.selectbox(
        "选择练习维度：", dims, key="sp_dim_select",
        index=dims.index(st.session_state.single_practice_dim) if st.session_state.single_practice_dim in dims else 0,
    )
    st.session_state.single_practice_dim = selected_dim

    if "sp_current_q" not in st.session_state:
        q_result = ask_next_question(
        st.session_state.question_pool, selected_dim,
        st.session_state.used_question_ids,
        st.session_state.messages,
        st.session_state.profile or {},
        st.session_state.scenario_key,
    )
        st.session_state.sp_current_q = q_result
        st.session_state.sp_answer_submitted = False
        st.session_state.sp_evaluation = None

    current_q = st.session_state.sp_current_q
    st.markdown(f"### 📝 {selected_dim} · 第 {st.session_state.single_practice_count + 1} 题")
    with st.chat_message("assistant"):
        st.write(current_q["question"])
    _render_latest_speech(current_q["question"])

    if not st.session_state.get("sp_answer_submitted", False):
        voice_widget_key = f"single_voice_{st.session_state.single_practice_count}_{current_q['question_id']}"
        voice_text, voice_new = _capture_voice_transcript(voice_widget_key)
        if voice_new and voice_text:
            st.session_state.sp_answer = voice_text
        user_answer = st.text_area("你的回答：", height=150, key="sp_answer", placeholder="在这里输入你的回答...")
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("📤 提交回答", type="primary", use_container_width=True):
                if not user_answer.strip():
                    st.warning("请输入你的回答")
                else:
                    with st.spinner("🤖 AI 评估中..."):
                        evaluation = evaluate_answer(current_q["question"], user_answer, selected_dim, st.session_state.profile or {})
                    st.session_state.sp_evaluation = evaluation
                    st.session_state.sp_user_answer = user_answer
                    st.session_state.sp_answer_submitted = True
                    st.session_state.single_practice_count += 1
                    _clear_voice_state()
                    st.rerun()
        with col2:
            if st.button("🔄 换一题", use_container_width=True):
                new_q = replace_question(st.session_state.question_pool, selected_dim, current_q["question_id"], st.session_state.profile or {}, st.session_state.scenario_key)
                st.session_state.sp_current_q = {"question": new_q["text"], "dimension": selected_dim, "question_id": new_q["id"]}
                st.session_state.sp_answer_submitted = False
                st.session_state.sp_evaluation = None
                _clear_voice_state()
                st.rerun()
    else:
        st.markdown(f"**你的回答：** {st.session_state.sp_user_answer}")
        eval_data = st.session_state.sp_evaluation or {}
        st.divider()
        st.subheader("📊 即时评估")
        score = eval_data.get("score", 5)
        st.metric("⭐ 综合评分", f"{score}/10")

        # 四要素子评分
        sub_scores = {
            "内容准确": eval_data.get("accuracy_score", 0),
            "深度细节": eval_data.get("depth_score", 0),
            "逻辑结构": eval_data.get("structure_score", 0),
            "个人见解": eval_data.get("insight_score", 0),
        }
        if any(v > 0 for v in sub_scores.values()):
            sub_cols = st.columns(4)
            for i, (label, val) in enumerate(sub_scores.items()):
                with sub_cols[i]:
                    st.metric(label, f"{val}/10")

        st.markdown("**👍 优点：**")
        for s in eval_data.get("strengths", []):
            st.markdown(f"- {s}")
        st.markdown("**🔧 改进建议：**")
        for w in eval_data.get("weaknesses", []):
            st.markdown(f"- {w}")
        if eval_data.get("model_answer"):
            with st.expander("💡 示范回答（点击展开）"):
                st.write(eval_data["model_answer"])
        if eval_data.get("follow_up_suggestions"):
            st.markdown("**🔗 追问方向（如果在真实面试中）：**")
            for fs in eval_data["follow_up_suggestions"]:
                st.markdown(f"- {fs}")
        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("▶️ 下一题", type="primary", use_container_width=True):
                q_result = ask_next_question(
        st.session_state.question_pool, selected_dim,
        st.session_state.used_question_ids,
        st.session_state.messages,
        st.session_state.profile or {},
        st.session_state.scenario_key,
    )
                st.session_state.sp_current_q = q_result
                st.session_state.sp_answer_submitted = False
                st.session_state.sp_evaluation = None
                _clear_voice_state()
                st.rerun()
        with col2:
            if st.button("🔄 换一题", use_container_width=True):
                new_q = replace_question(st.session_state.question_pool, selected_dim, current_q["question_id"], st.session_state.profile or {}, st.session_state.scenario_key)
                st.session_state.sp_current_q = {"question": new_q["text"], "dimension": selected_dim, "question_id": new_q["id"]}
                st.session_state.sp_answer_submitted = False
                st.session_state.sp_evaluation = None
                _clear_voice_state()
                st.rerun()
        with col3:
            if st.button("🏠 返回首页", use_container_width=True):
                st.session_state.page = "profile"
                st.rerun()


def _build_report_markdown(report: dict, scenario_key: str) -> str:
    """生成报告 Markdown 内容，供导出下载。"""
    scenario = get_scenario(scenario_key)
    lines = [
        f"# 🎓 AI 面试诊断报告",
        f"",
        f"**面试类型**：{scenario['name']}",
        f"**生成时间**：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"",
        f"## 🎯 总体评分",
        f"",
        f"**{report.get('overall_score', 0)}/100**",
        f"",
    ]

    dim_scores = report.get("dimension_scores", {})
    if dim_scores:
        lines.append("## 📈 维度得分")
        lines.append("")
        lines.append("| 维度 | 得分 | 等级 |")
        lines.append("|------|------|------|")
        for dim, score in dim_scores.items():
            level = "优秀" if score >= 85 else "良好" if score >= 70 else "一般" if score >= 55 else "较弱"
            lines.append(f"| {dim} | {score} | {level} |")
        lines.append("")

    highlights = report.get("highlights", [])
    if highlights:
        lines.append("## ✅ 亮点")
        lines.append("")
        for h in highlights:
            lines.append(f"- {h}")
        lines.append("")

    improvements = report.get("improvements", [])
    if improvements:
        lines.append("## ⚠️ 待改进")
        lines.append("")
        for imp in improvements:
            lines.append(f"- {imp}")
        lines.append("")

    per_q = report.get("per_question_feedback", [])
    if per_q:
        lines.append("## 📋 逐题反馈")
        lines.append("")
        for i, fb in enumerate(per_q):
            lines.append(f"**Q{i+1}** [{fb.get('dimension', '')}] — ⭐{fb.get('score', '-')}")
            lines.append(f"> {fb.get('question', '')[:80]}...")
            lines.append(f"")
            lines.append(f"{fb.get('comment', '无评价')}")
            lines.append("")

    plan = report.get("improvement_plan", [])
    if plan:
        lines.append("## 🗓 改进计划")
        lines.append("")
        for i, p in enumerate(plan):
            lines.append(f"{i+1}. {p}")
        lines.append("")

    lines.append("---")
    lines.append("*报告由 AI 学术面试教练自动生成 · 仅供参考*")
    return "\n".join(lines)


def render_report_page():
    report = st.session_state.report
    if not report:
        st.warning("暂无报告")
        return
    st.title("📊 面试诊断报告")
    overall = report.get("overall_score", 0)
    st.metric("🎯 总体评分", f"{overall}/100")
    dim_scores = report.get("dimension_scores", {})
    if dim_scores:
        st.subheader("📈 维度得分")
        cols = st.columns(len(dim_scores))
        for i, (dim, score) in enumerate(dim_scores.items()):
            with cols[i]:
                bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
                level = "优秀" if score >= 85 else "良好" if score >= 70 else "一般" if score >= 55 else "较弱"
                st.markdown(f"**{dim}**\n\n{bar} {score} {level}")
    highlights = report.get("highlights", [])
    if highlights:
        st.subheader("✅ 亮点")
        for h in highlights:
            st.markdown(f"- {h}")
    improvements = report.get("improvements", [])
    if improvements:
        st.subheader("⚠️ 待改进")
        for imp in improvements:
            st.markdown(f"- {imp}")
    per_q = report.get("per_question_feedback", [])
    if per_q:
        st.subheader("📋 逐题反馈")
        for i, fb in enumerate(per_q):
            with st.expander(f"Q{i+1} [{fb.get('dimension', '')}] {fb.get('question', '')[:50]}... — ⭐{fb.get('score', '-')}"):
                st.write(fb.get("comment", "无评价"))
    plan = report.get("improvement_plan", [])
    if plan:
        st.subheader("🗓 改进计划")
        for i, p in enumerate(plan):
            st.markdown(f"{i+1}. {p}")
    # 导出 Markdown
    md_content = _build_report_markdown(report, st.session_state.scenario_key)
    st.download_button(
        label="📥 导出 Markdown 报告",
        data=md_content,
        file_name=f"AI面试诊断报告_{st.session_state.scenario_key}.md",
        mime="text/markdown",
        use_container_width=True,
    )

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 再来一场", use_container_width=True):
            for key in DEFAULTS:
                if key != "page":
                    st.session_state[key] = DEFAULTS[key]
            st.session_state.page = "profile"
            st.rerun()
    with col2:
        if st.button("🏠 返回首页", use_container_width=True):
            st.session_state.page = "profile"
            st.rerun()


def render_history_list_page():
    st.title("📚 历史面试记录")
    sessions = list_sessions()
    if not sessions:
        st.info("暂无面试记录。去[新建面试]开始你的第一场AI模拟面试吧！")
        return

    # ===== D: 进步追踪 =====
    # 筛选有评分的面试会话（排除 pool_generation）
    scored = [s for s in sessions if s.get("score") is not None and s.get("mode") != "pool_generation"]
    if len(scored) >= 2:
        with st.expander("📈 进步追踪（展开查看趋势）", expanded=len(scored) >= 3):
            # 按时间升序排列
            scored_asc = list(reversed(scored))
            chart_data = {"面试": [f"#{i+1}" for i in range(len(scored_asc))],
                          "总体评分": [s["score"] for s in scored_asc]}
            st.line_chart(chart_data, x="面试", y="总体评分", use_container_width=True)
            st.caption("趋势线反映历次全模拟面试的总体评分变化。")
    elif len(scored) == 1:
        st.info("📈 进步追踪需要至少完成2次全模拟面试才会显示趋势图。")

    st.divider()
    scenario_names = {s["key"]: s["name"] for s in list_scenarios()}
    for sess in sessions:
        scenario_name = scenario_names.get(sess.get("scenario", ""), sess.get("scenario", "未知"))
        mode = sess.get("mode", "")
        created = sess.get("created_at", "")[:16].replace("T", " ")

        # 题库生成事件 vs 面试会话
        if mode == "pool_generation":
            pool_summary = sess.get("pool_summary", {})
            summary_text = " · ".join([f"{dim}:{cnt}题" for dim, cnt in pool_summary.items()])
            label = f"📝 题库生成 — {scenario_name}"
            detail = summary_text
            score_str = ""
            show_detail_btn = False
        else:
            score = sess.get("score")
            score_str = f"⭐{score}" if score is not None else "未评分"
            mode_label = "全模拟" if mode == "full_simulation" else "单题练习" if mode == "single_practice" else mode
            label = f"**{scenario_name}** — {created}"
            detail = mode_label
            show_detail_btn = True

        with st.container():
            col1, col2, col3, col4 = st.columns([3, 1, 2, 1])
            with col1:
                st.markdown(f"{label}")
                if mode == "pool_generation":
                    st.caption(detail)
            with col2:
                st.markdown(score_str)
            with col3:
                if not show_detail_btn:
                    st.markdown(detail)
            with col4:
                if show_detail_btn:
                    if st.button("查看", key=f"detail_{sess['session_id']}"):
                        st.session_state.view_session_id = sess["session_id"]
                        st.session_state.page = "history_detail"
                        st.rerun()
        st.divider()


def render_history_detail_page():
    sid = st.session_state.get("view_session_id", "")
    data = load_session(sid)
    if not data:
        st.warning("记录不存在或已删除")
        st.session_state.page = "history_list"
        st.rerun()
    scenario = get_scenario(data.get("scenario", "postgraduate"))
    mode = data.get("mode", "")

    st.title(f"📜 {scenario['name']} — 面试回顾")
    st.caption(f"时间：{data.get('created_at', '')}  ·  模式：{mode}")

    report = data.get("report")

    # ===== 完整报告（优先展示）=====
    if report:
        overall = report.get("overall_score", 0)
        st.metric("🎯 总体评分", f"{overall}/100")

        dim_scores = report.get("dimension_scores", {})
        if dim_scores:
            st.subheader("📈 维度得分")
            cols = st.columns(len(dim_scores))
            for i, (dim, score) in enumerate(dim_scores.items()):
                with cols[i]:
                    bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
                    level = "优秀" if score >= 85 else "良好" if score >= 70 else "一般" if score >= 55 else "较弱"
                    st.markdown(f"**{dim}**\n\n{bar} {score} {level}")

        highlights = report.get("highlights", [])
        improvements = report.get("improvements", [])
        col_a, col_b = st.columns(2)
        if highlights:
            with col_a:
                st.markdown("### ✅ 亮点")
                for h in highlights:
                    st.markdown(f"- {h}")
        if improvements:
            with col_b:
                st.markdown("### ⚠️ 待改进")
                for imp in improvements:
                    st.markdown(f"- {imp}")

        per_q = report.get("per_question_feedback", [])
        if per_q:
            st.subheader("📋 逐题反馈")
            for i, fb in enumerate(per_q):
                with st.expander(f"Q{i+1} [{fb.get('dimension', '')}] {fb.get('question', '')[:60]}... — ⭐{fb.get('score', '-')}"):
                    st.write(fb.get("comment", "无评价"))

        plan = report.get("improvement_plan", [])
        if plan:
            st.subheader("🗓 改进计划")
            for i, p in enumerate(plan):
                st.markdown(f"{i+1}. {p}")

    st.divider()

    # ===== 对话记录（可折叠）=====
    with st.expander("📝 查看完整对话记录", expanded=False):
        for msg in data.get("messages", []):
            with st.chat_message("assistant" if msg["role"] == "interviewer" else "user"):
                dim_tag = f"[{msg.get('dimension', '')}] " if msg.get("dimension") else ""
                fu_tag = "🔁追问 " if msg.get("is_followup") else ""
                st.caption(f"{fu_tag}{dim_tag}")
                st.write(msg["content"])

    if st.button("← 返回列表"):
        st.session_state.page = "history_list"
        st.rerun()


def render_interview_page():
    if st.session_state.mode == "full_simulation":
        render_full_simulation()
    else:
        render_single_practice()


def render_page():
    page = st.session_state.page
    if page == "profile":
        render_profile_page()
    elif page == "mode_select":
        render_mode_select_page()
    elif page == "interview":
        render_interview_page()
    elif page == "report":
        render_report_page()
    elif page == "history_list":
        render_history_list_page()
    elif page == "history_detail":
        render_history_detail_page()


render_page()
