from __future__ import annotations

import importlib
from pathlib import Path

import streamlit as st

from career_assistant.database import DATA_SOURCE_NOTE, initialize_database
from career_assistant.document_loader import SUPPORTED_RESUME_TYPES, ResumeParseError, extract_resume_text
from career_assistant.interview import InterviewSession
from career_assistant.jobs import generate_learning_path, match_jobs, predict_salary_range
from career_assistant.llm import active_llm_label, active_model_name, llm_api_configured
from career_assistant.rag import InterviewRAG, parse_interview_bank_markdown
from career_assistant.resume import ROLE_KEYWORDS, analyze_resume, skill_tag_weights
from career_assistant.text2sql import execute_nl_query
from career_assistant.ui import (
    feedback_card_html,
    hero_html,
    metric_card_html,
    note_panel_html,
    page_styles,
    section_header_html,
    source_card_html,
)
from career_assistant.visualization import bar_chart, donut_chart, line_chart, radar_chart, tag_cloud_html


BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "career_demo.sqlite3"
CHROMA_DIR = BASE_DIR / ".runtime_chroma_db"
ROLE_OPTIONS = list(ROLE_KEYWORDS.keys())
TEST_RESUME = (
    "张三\n"
    "求职目标：AI应用开发\n"
    "教育经历：中南财经政法大学 信息管理与信息系统\n"
    "项目经历：使用 Python、SQL、Streamlit、RAG、Prompt 完成就业数据分析助手\n"
    "实习经历：负责 API 调用、数据清洗、可视化报告和业务复盘\n"
    "技能：Python、SQL、Streamlit、机器学习、数据分析、RAG、Prompt"
)
DEFAULT_RESUME = (
    "张三\n"
    "求职目标：数据分析师\n"
    "教育经历：中南财经政法大学 信息管理与信息系统\n"
    "项目经历：使用 Python、SQL、Streamlit 完成就业数据分析看板\n"
    "实习经历：负责指标拆解、数据清洗、可视化报告和业务复盘"
)
QUICK_SQL_QUESTIONS = [
    "各学院就业率排名",
    "法学院本科就业率",
    "不同行业薪资对比",
    "私营单位行业薪资对比",
    "AI应用开发热门技能趋势",
    "哪些岗位薪资最高",
]


st.set_page_config(page_title="职途 AI 面试助手", page_icon="🎯", layout="wide")


@st.cache_resource
def get_rag() -> InterviewRAG:
    rag = InterviewRAG(CHROMA_DIR)
    rag.index_documents(load_interview_bank())
    return rag


@st.cache_resource
def get_database() -> Path:
    return initialize_database(DB_PATH)


def load_interview_bank() -> list[dict[str, str]]:
    bank_path = DATA_DIR / "interview_bank.md"
    if not bank_path.exists():
        return []
    return parse_interview_bank_markdown(bank_path.read_text(encoding="utf-8"))


def read_resume_upload() -> str:
    uploaded = st.file_uploader(
        "上传简历文件（pdf/docx/txt/md/rtf，可选）",
        type=SUPPORTED_RESUME_TYPES,
    )
    if not uploaded:
        return ""
    try:
        return extract_resume_text(uploaded.name, uploaded.getvalue())
    except ResumeParseError as exc:
        st.warning(str(exc))
        return ""


def current_profile():
    return st.session_state.get("profile")


def ensure_profile():
    profile = current_profile()
    if profile is None:
        st.info("请先在“简历优化”页粘贴或上传简历并点击分析。")
    return profile


def get_interview_session():
    session = st.session_state.get("interview")
    if session is not None and not hasattr(session, "answer_feedbacks"):
        session.answer_feedbacks = []
    if session is not None and hasattr(session, "ensure_feedbacks"):
        session.ensure_feedbacks()
    return session


def render_weighted_skill_cloud(profile) -> str:
    try:
        return tag_cloud_html(skill_tag_weights(profile.skills, profile.target_role))
    except TypeError:
        import career_assistant.resume as resume_module
        import career_assistant.visualization as visualization_module

        importlib.reload(resume_module)
        importlib.reload(visualization_module)
        return visualization_module.tag_cloud_html(
            resume_module.skill_tag_weights(profile.skills, profile.target_role)
        )


get_database()
rag = get_rag()

st.markdown(page_styles(), unsafe_allow_html=True)
st.markdown(
    hero_html(
        "职途 AI 面试助手",
        "从简历诊断、面试练习到岗位选择，把投递前准备整理成一条清晰路径。",
        [
            ("简历诊断", "blue"),
            ("模拟面试", "green"),
            ("岗位匹配", "amber"),
            (f"服务状态：{active_llm_label()}", "slate"),
        ],
    ),
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### 准备进度")
    profile_for_progress = current_profile()
    interview_for_progress = get_interview_session()
    progress_items = [
        ("简历诊断", profile_for_progress is not None),
        ("面试题库", st.session_state.get("rag_answer") is not None),
        ("模拟面试", bool(interview_for_progress and interview_for_progress.answers)),
        ("岗位匹配", profile_for_progress is not None),
        ("就业数据", st.session_state.get("last_sql_result") is not None),
        ("竞争力复盘", profile_for_progress is not None),
    ]
    for label, done in progress_items:
        st.write(f"{'✓' if done else '□'} {label}")
    st.markdown("---")
    st.markdown("### 服务状态")
    st.write(active_llm_label())
    if llm_api_configured():
        st.caption(active_model_name())
    else:
        st.caption("未连接")

tabs = st.tabs(["简历", "题库", "面试", "岗位", "数据", "竞争力"])

with tabs[0]:
    st.markdown(section_header_html("简历诊断", "上传或粘贴简历，查看岗位匹配、技能标签和修改清单。"), unsafe_allow_html=True)
    col_left, col_right = st.columns([1.2, 1])
    with col_left:
        target_role = st.selectbox("目标岗位", ROLE_OPTIONS)
        uploaded_text = read_resume_upload()
        if "resume_text_value" not in st.session_state:
            st.session_state.resume_text_value = uploaded_text or DEFAULT_RESUME
        elif uploaded_text:
            st.session_state.resume_text_value = uploaded_text
        if st.button("一键填入测试简历"):
            st.session_state.resume_text_value = TEST_RESUME
        resume_text = st.text_area(
            "粘贴简历内容",
            key="resume_text_value",
            height=220,
        )
        if st.button("分析简历", type="primary"):
            st.session_state.profile = analyze_resume(resume_text, target_role)
    with col_right:
        profile = current_profile()
        if profile:
            st.markdown(
                metric_card_html("简历匹配度", f"{profile.match_score}%", "目标岗位适配评估"),
                unsafe_allow_html=True,
            )
            st.markdown("**技能词云**", unsafe_allow_html=True)
            st.markdown(render_weighted_skill_cloud(profile), unsafe_allow_html=True)
            st.markdown("**修改清单**")
            for suggestion in profile.suggestions:
                st.write(f"- {suggestion}")
            export_text = "\n".join(
                [
                    f"# {profile.name} 简历修改清单",
                    "",
                    f"- 目标岗位：{profile.target_role}",
                    f"- 简历匹配度：{profile.match_score}%",
                    f"- 技能标签：{'、'.join(profile.skills) or '暂无'}",
                    "",
                    "## 修改清单",
                    *[f"- {suggestion}" for suggestion in profile.suggestions],
                ]
            )
            st.download_button(
                "导出修改清单",
                data=export_text,
                file_name="resume_suggestions.md",
                mime="text/markdown",
            )
        else:
            st.markdown(note_panel_html("完成分析后，这里会显示技能标签、匹配度和修改清单。"), unsafe_allow_html=True)

with tabs[1]:
    st.markdown(section_header_html("面试题库", "查询岗位问题、参考回答和追问方向。"), unsafe_allow_html=True)
    question = st.text_input("输入岗位/行业面试问题", "数据分析师 SQL 面试会问什么？")
    col_fast, col_polish, _ = st.columns([0.12, 0.12, 0.76])
    with col_fast:
        fast_clicked = st.button("快速检索", type="primary")
    with col_polish:
        polish_clicked = st.button("AI检索")
    if fast_clicked:
        st.session_state.rag_answer = rag.answer(question)
        st.session_state.rag_answer_mode = "快速检索"
    if polish_clicked:
        st.session_state.rag_answer = rag.polish_answer(question)
        st.session_state.rag_answer_mode = "AI检索"
    answer = st.session_state.get("rag_answer")
    if answer:
        st.caption(st.session_state.get("rag_answer_mode", "快速回答"))
        st.write(answer.content)
        st.markdown("**参考资料**")
        for source in answer.sources:
            st.markdown(source_card_html(source.title, f"{source.content[:180]}..."), unsafe_allow_html=True)

with tabs[2]:
    st.markdown(section_header_html("模拟面试", "完成五轮问答，查看评分、点评和复盘记录。"), unsafe_allow_html=True)
    profile = ensure_profile()
    col_setup, col_chat = st.columns([0.85, 1.15])
    with col_setup:
        role = st.selectbox("模拟岗位", ROLE_OPTIONS, key="interview_role")
        if st.button("开始/重置面试"):
            skills = profile.skills if profile else []
            st.session_state.interview = InterviewSession(
                role=role,
                resume_skills=skills,
                resume_text=st.session_state.get("resume_text_value", ""),
            )
            st.session_state.force_interview_report = False
        session = get_interview_session()
        retry_disabled = session is None or not session.answers
        if st.button("重新回答上一轮", disabled=retry_disabled):
            if session and session.retry_last_answer():
                st.session_state.force_interview_report = False
                st.rerun()
        if st.button("结束面试并查看报告", disabled=retry_disabled):
            st.session_state.force_interview_report = True
            st.rerun()
        if session:
            st.markdown(metric_card_html("已回答轮次", f"{len(session.answers)}/5", "完成后查看报告"), unsafe_allow_html=True)
    with col_chat:
        session = get_interview_session()
        if session:
            if session.answer_feedbacks:
                st.markdown("**本轮点评**")
                for index, feedback in enumerate(session.answer_feedbacks, start=1):
                    st.markdown(feedback_card_html(index, feedback), unsafe_allow_html=True)
            show_report = session.is_complete or bool(st.session_state.get("force_interview_report"))
            if not show_report:
                question = session.next_question() if len(session.asked_questions) == len(session.answers) else session.asked_questions[-1]
                st.write(f"**面试官：** {question}")
                answer_key = f"answer_{len(session.answers)}"
                with st.form(key=f"interview_form_{len(session.answers)}", clear_on_submit=True):
                    answer = st.text_area("你的回答", key=answer_key, height=140)
                    submitted = st.form_submit_button("提交本轮回答")
                if submitted:
                    if not answer.strip():
                        st.warning("请先输入本轮回答，再提交。")
                    else:
                        session.answer_current(answer)
                        st.rerun()
            else:
                report = session.score_report()
                report_title = "面试完成" if session.is_complete else "阶段性面试报告"
                st.success(f"{report_title}，总分：{report.total_score}")
                st.plotly_chart(radar_chart(report.dimensions), width="stretch")
                st.plotly_chart(donut_chart(report.match_percent), width="stretch")
                for item in report.feedback:
                    st.write(f"- {item}")
        else:
            st.markdown(note_panel_html("点击左侧按钮开始 5 轮模拟面试。"), unsafe_allow_html=True)

with tabs[3]:
    st.markdown(section_header_html("岗位推荐", "查看适合岗位、补强技能和薪资参考。"), unsafe_allow_html=True)
    profile = ensure_profile()
    if profile:
        interview_session = get_interview_session()
        interview_report = (
            interview_session.score_report(include_ai=False)
            if interview_session and interview_session.answers
            else None
        )
        matches = match_jobs(profile, DB_PATH, interview_report)
        if interview_report:
            st.info(f"已纳入当前面试表现：总分 {interview_report.total_score}，匹配度 {interview_report.match_percent}。")
        for match in matches:
            with st.container(border=True):
                col_a, col_b = st.columns([0.75, 0.25])
                with col_a:
                    st.markdown(f"### {match.title} · {match.industry}")
                    st.write(match.description)
                    st.write(f"匹配技能：{'、'.join(match.matched_skills) or '暂无'}")
                    st.write(f"待补强：{'、'.join(match.missing_skills) or '已基本覆盖'}")
                    with st.expander("岗位详情"):
                        st.write(match.detail)
                with col_b:
                    st.markdown(metric_card_html("匹配度", f"{match.match_score}%", "综合评估"), unsafe_allow_html=True)
                    st.markdown(metric_card_html("薪资区间", match.salary_range, "社会参考"), unsafe_allow_html=True)
                    if st.button("查看岗位详情", key=f"job_detail_{match.title}"):
                        st.session_state.selected_job_detail = match.title
                    if st.button("查看学习路径", key=f"learning_path_{match.title}"):
                        st.session_state.learning_role = match.title
                    st.link_button("查看岗位参考", match.reference_url)
                if st.session_state.get("learning_role") == match.title:
                    st.markdown("**该岗位学习路径**")
                    for item in generate_learning_path(profile, match.title):
                        st.write(f"- {item}")
        salary = predict_salary_range(profile, profile.target_role, DB_PATH)
        st.markdown(note_panel_html(f"{salary.role} 预测薪资：{salary.low}-{salary.high} 元/月。{salary.basis}"), unsafe_allow_html=True)
        selected_job = st.session_state.get("selected_job_detail")
        if selected_job:
            selected_match = next((match for match in matches if match.title == selected_job), None)
            if selected_match:
                st.markdown("### 岗位详情")
                st.markdown(note_panel_html(selected_match.detail), unsafe_allow_html=True)
                st.markdown("**岗位补强路径**")
                for item in generate_learning_path(profile, selected_match.title):
                    st.write(f"- {item}")

with tabs[4]:
    st.markdown(section_header_html("就业数据", "查看就业率、薪资参考和岗位技能趋势。"), unsafe_allow_html=True)
    st.markdown(note_panel_html(DATA_SOURCE_NOTE), unsafe_allow_html=True)
    if "nl_question_value" not in st.session_state:
        st.session_state.nl_question_value = "数据分析师近两年薪资变化"
    st.markdown("**快捷查询**")
    quick_cols = st.columns(len(QUICK_SQL_QUESTIONS))
    for col, quick_question in zip(quick_cols, QUICK_SQL_QUESTIONS):
        with col:
            if st.button(quick_question):
                st.session_state.nl_question_value = quick_question
    nl_question = st.text_input("自然语言查询", key="nl_question_value")
    if st.button("查询数据"):
        result = execute_nl_query(nl_question, DB_PATH)
        st.session_state.last_sql_result = result
        st.write(result.explanation)
        st.dataframe(result.rows, width="stretch")
        if result.rows and result.chart_type == "line" and "year" in result.rows[0]:
            y_field = "monthly_avg" if "monthly_avg" in result.rows[0] else "avg_salary"
            st.plotly_chart(line_chart(result.rows, "year", y_field, "平均薪资趋势"), width="stretch")
        elif result.rows and "role" in result.rows[0] and "monthly_avg" in result.rows[0]:
            st.plotly_chart(bar_chart(result.rows, "role", "monthly_avg", "岗位月均薪资参考"), width="stretch")
        elif result.rows and "industry" in result.rows[0] and "monthly_avg" in result.rows[0]:
            st.plotly_chart(bar_chart(result.rows, "industry", "monthly_avg", "行业月均薪资参考"), width="stretch")
        elif result.rows and "college" in result.rows[0] and "employment_rate" in result.rows[0]:
            st.plotly_chart(bar_chart(result.rows, "college", "employment_rate", "学院就业率"), width="stretch")

with tabs[5]:
    st.markdown(section_header_html("竞争力复盘", "汇总能力短板，整理下一步训练路径。"), unsafe_allow_html=True)
    profile = ensure_profile()
    if profile:
        learning_role = st.session_state.get("learning_role", profile.target_role)
        st.plotly_chart(donut_chart(profile.match_score, "简历-岗位匹配度"), width="stretch")
        st.markdown(f"**个性化学习路径：{learning_role}**")
        for item in generate_learning_path(profile, learning_role):
            st.write(f"- {item}")
        demo_dimensions = {
            "技能匹配": profile.match_score,
            "项目表达": 78,
            "行业理解": 72,
            "面试准备": 75,
        }
        st.plotly_chart(radar_chart(demo_dimensions), width="stretch")
