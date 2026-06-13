"""
AI 学术面试教练 — Streamlit 前端
================================
页面状态机：profile → mode_select → interview → report
"""

import sys
import os
import time
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

from modules.scenarios import get_scenario, list_scenarios
from modules.profiler import analyze_profile, generate_question_pool, replace_question
from modules.interviewer import (
    start_interview, ask_next_question, decide_follow_up, generate_transition,
)
from modules.evaluator import evaluate_answer, generate_full_report
from modules.history import save_session, list_sessions, load_session, delete_session


st.set_page_config(page_title="AI 学术面试教练", page_icon="🎓", layout="wide")

DEFAULTS = {
    "page": "profile", "mode": None, "scenario_key": "postgraduate",
    "profile": None, "question_pool": None, "question_counts": [6, 4, 4, 2],
    "messages": [], "interview_state": None, "used_question_ids": set(),
    "report": None, "single_practice_dim": None, "single_practice_count": 0,
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

if isinstance(st.session_state.used_question_ids, list):
    st.session_state.used_question_ids = set(st.session_state.used_question_ids)


with st.sidebar:
    st.title("🎓 AI 学术面试教练")
    st.divider()
    pages = {"profile": "📋 新建面试", "history_list": "📚 历史记录"}
    selected = st.radio("导航", list(pages.keys()), format_func=lambda x: pages[x], label_visibility="collapsed")
    if selected != st.session_state.page and selected == "profile":
        for key in DEFAULTS:
            if key != "page":
                st.session_state[key] = DEFAULTS[key]
        st.session_state.page = "profile"
        st.rerun()
    elif selected == "history_list":
        st.session_state.page = "history_list"
        st.rerun()
    st.divider()
    st.caption(f"📊 状态：{st.session_state.page}")


def render_profile_page():
    st.title("📋 构建你的面试画像")
    st.markdown("填写以下信息，AI 将为你生成**个性化面试题库**。越详细，题目越有针对性。")

    col1, col2 = st.columns(2)
    with col1:
        target_major = st.text_input("🎯 报考/申请专业 *", placeholder="如：信息与通信工程", key="f_target_major")
        undergrad_major = st.text_input("📖 本科专业 *", placeholder="如：电子信息工程", key="f_undergrad_major")
        scenario_display = st.selectbox("📝 面试类型 *", options=[s["name"] for s in list_scenarios()], key="f_scenario_display")
        scenario_map = {s["name"]: s["key"] for s in list_scenarios()}
        scenario_key = scenario_map.get(scenario_display, "postgraduate")
        target_school = st.text_input("🏫 目标院校 *", placeholder="如：华中科技大学", key="f_target_school")

    with col2:
        target_advisor = st.text_input("👨‍🏫 目标导师（选填）", placeholder="导师姓名或研究方向", key="f_advisor")
        research_exp = st.text_area("🔬 科研经历（推荐填写）", placeholder="如：参与国家级大创，方向是图像分割，使用U-Net模型...", height=120, key="f_research")
        competitions = st.text_input("🏆 竞赛/论文（选填）", placeholder="如：数学建模省二等奖", key="f_competitions")
        english_level = st.text_input("🇬🇧 英语水平（选填）", placeholder="如：CET-6 520", key="f_english")

    self_intro = st.text_area("✍️ 自我介绍草稿（选填，AI会据此出题）", placeholder="如果你已经有了自我介绍草稿，贴在这里...", height=100, key="f_self_intro")

    st.divider()
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
    st.divider()

    if st.button("🚀 生成我的个性化题库", type="primary", use_container_width=True):
        if not target_major or not undergrad_major or not target_school:
            st.error("请填写必填项（标注 * 的字段）")
            return
        with st.spinner("🤖 AI 正在分析你的画像..."):
            form_data = {
                "target_major": target_major, "undergrad_major": undergrad_major,
                "scenario": scenario_key, "target_school": target_school,
                "target_advisor": target_advisor, "research_exp": research_exp,
                "competitions": competitions, "english_level": english_level,
                "self_intro_draft": self_intro,
            }
            profile = analyze_profile(form_data)
            st.session_state.profile = profile
            st.session_state.profile.update({
                "target_major": target_major, "undergrad_major": undergrad_major,
                "target_school": target_school, "target_advisor": target_advisor,
            })
        with st.spinner("📝 AI 正在生成个性化题目..."):
            question_pool = generate_question_pool(profile, scenario_key, counts)
            st.session_state.question_pool = question_pool
            st.session_state.question_counts = counts
            st.session_state.scenario_key = scenario_key
        total = sum(len(v) for v in question_pool.values())
        st.success(f"✅ 题库生成完毕！共 **{total}** 道个性化题目，覆盖 {len(dims)} 个维度。")
        st.session_state.page = "mode_select"
        st.rerun()


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

    user_input = st.chat_input("输入你的回答...")
    if not user_input:
        return

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
        next_q = ask_next_question(st.session_state.question_pool, dims[0], st.session_state.used_question_ids)
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
                    state["phase"] = "done"
                    st.session_state.messages.append({
                        "role": "interviewer",
                        "content": "好的，今天的面试到这里就结束了。感谢你的参与！请点击下方按钮查看你的面试诊断报告。",
                        "dimension": None, "is_followup": False,
                    })
                    st.rerun()

                next_dim = dims[next_dim_idx]
                transition = generate_transition(current_dim, next_dim, st.session_state.scenario_key)
                st.session_state.messages.append({
                    "role": "interviewer", "content": transition,
                    "dimension": None, "is_followup": False,
                })
                state["phase"] = "questioning"
                first_q = ask_next_question(st.session_state.question_pool, next_dim, st.session_state.used_question_ids)
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
                next_q = ask_next_question(st.session_state.question_pool, current_dim, st.session_state.used_question_ids)
                st.session_state.messages.append({
                    "role": "interviewer", "content": next_q["question"],
                    "dimension": next_q["dimension"], "is_followup": False,
                    "question_id": next_q["question_id"],
                })
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
        q_result = ask_next_question(st.session_state.question_pool, selected_dim, st.session_state.used_question_ids)
        st.session_state.sp_current_q = q_result
        st.session_state.sp_answer_submitted = False
        st.session_state.sp_evaluation = None

    current_q = st.session_state.sp_current_q
    st.markdown(f"### 📝 {selected_dim} · 第 {st.session_state.single_practice_count + 1} 题")
    with st.chat_message("assistant"):
        st.write(current_q["question"])

    if not st.session_state.get("sp_answer_submitted", False):
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
                    st.rerun()
        with col2:
            if st.button("🔄 换一题", use_container_width=True):
                new_q = replace_question(st.session_state.question_pool, selected_dim, current_q["question_id"], st.session_state.profile or {}, st.session_state.scenario_key)
                st.session_state.sp_current_q = {"question": new_q["text"], "dimension": selected_dim, "question_id": new_q["id"]}
                st.session_state.sp_answer_submitted = False
                st.session_state.sp_evaluation = None
                st.rerun()
    else:
        st.markdown(f"**你的回答：** {st.session_state.sp_user_answer}")
        eval_data = st.session_state.sp_evaluation or {}
        st.divider()
        st.subheader("📊 即时评估")
        score = eval_data.get("score", 5)
        st.metric("⭐ 评分", f"{score}/10")
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
                q_result = ask_next_question(st.session_state.question_pool, selected_dim, st.session_state.used_question_ids)
                st.session_state.sp_current_q = q_result
                st.session_state.sp_answer_submitted = False
                st.session_state.sp_evaluation = None
                st.rerun()
        with col2:
            if st.button("🔄 换一题", use_container_width=True):
                new_q = replace_question(st.session_state.question_pool, selected_dim, current_q["question_id"], st.session_state.profile or {}, st.session_state.scenario_key)
                st.session_state.sp_current_q = {"question": new_q["text"], "dimension": selected_dim, "question_id": new_q["id"]}
                st.session_state.sp_answer_submitted = False
                st.session_state.sp_evaluation = None
                st.rerun()
        with col3:
            if st.button("🏠 返回首页", use_container_width=True):
                st.session_state.page = "profile"
                st.rerun()


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
    scenario_names = {s["key"]: s["name"] for s in list_scenarios()}
    for sess in sessions:
        scenario_name = scenario_names.get(sess.get("scenario", ""), sess.get("scenario", "未知"))
        score = sess.get("score")
        score_str = f"⭐{score}" if score is not None else "未评分"
        created = sess.get("created_at", "")[:16].replace("T", " ")
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 1, 2, 1])
            with col1:
                st.markdown(f"**{scenario_name}** — {created}")
            with col2:
                st.markdown(score_str)
            with col3:
                st.markdown(sess.get("mode", ""))
            with col4:
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
    st.title(f"📜 {scenario['name']} — 面试回顾")
    st.caption(f"时间：{data.get('created_at', '')}")
    for msg in data.get("messages", []):
        with st.chat_message("assistant" if msg["role"] == "interviewer" else "user"):
            dim_tag = f"[{msg.get('dimension', '')}] " if msg.get("dimension") else ""
            fu_tag = "🔁追问 " if msg.get("is_followup") else ""
            st.caption(f"{fu_tag}{dim_tag}")
            st.write(msg["content"])
    report = data.get("report")
    if report:
        st.divider()
        st.subheader(f"📊 总体评分：{report.get('overall_score', 'N/A')}/100")
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
