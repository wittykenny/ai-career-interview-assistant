import pytest

from career_assistant.interview import InterviewSession


def test_interview_session_runs_five_rounds_and_scores_answers():
    session = InterviewSession(role="产品经理", resume_skills=["SQL", "用户调研", "Python"])

    questions = []
    for index in range(5):
        question = session.next_question()
        questions.append(question)
        feedback = session.answer_current(
            f"第{index + 1}题回答：我会先澄清目标，再用数据分析、用户调研和结构化拆解推进方案。"
        )
        assert "本轮反馈" in feedback

    assert len(set(questions)) == 5
    assert len(session.answer_feedbacks) == 5
    assert session.is_complete

    report = session.score_report()
    assert report.total_score >= 70
    assert {"表达能力", "专业匹配", "逻辑结构", "岗位动机"}.issubset(report.dimensions)
    assert report.match_percent >= 60


def test_interview_session_scores_realistic_chinese_answers_high():
    session = InterviewSession(role="产品经理", resume_skills=["SQL", "用户调研", "Python"])
    answers = [
        "我会先明确用户场景和业务目标，再通过用户调研和数据分析验证需求价值，最后用小流量实验复盘结果。",
        "我会按照业务价值、用户影响、实现成本和风险四个维度排序，并同步研发确认排期。",
        "我会先对齐共同目标，再拆解各部门责任和时间节点，定期同步风险，最后复盘协作结果。",
        "我会设置转化率、留存率和满意度指标，并结合用户反馈判断上线效果是否达标。",
        "我会先核查数据口径，再补充访谈样本，最终围绕业务目标、用户价值和风险做权衡。",
    ]

    for answer in answers:
        session.next_question()
        session.answer_current(answer)

    report = session.score_report()

    assert report.total_score >= 70
    assert report.match_percent >= 74
    assert not any("低质量熔断" in item for item in report.feedback)


def test_interview_session_scores_realistic_data_analyst_answers_high():
    session = InterviewSession(role="数据分析师", resume_skills=["SQL", "Python", "数据分析"])
    answers = [
        "我会先明确业务目标，再用 SQL 提取核心指标，并用 Python 清洗异常值，最后用图表解释结论。",
        "在项目中我负责搭建指标看板，先定义口径，再做数据校验，帮助团队发现转化率下降原因。",
        "遇到缺失值我会区分随机缺失和业务缺失，结合均值填充、删除或单独建模，并说明影响。",
        "我理解数据分析师要把业务问题转化成可验证假设，通过数据支持决策，而不是只出图。",
        "如果结论被质疑，我会回到数据来源、SQL 口径和样本范围逐项复核，并给出复盘记录。",
    ]

    for answer in answers:
        session.next_question()
        session.answer_current(answer)

    report = session.score_report()

    assert report.total_score >= 70
    assert report.match_percent >= 74
    assert not any("低质量熔断" in item for item in report.feedback)


def test_interview_session_scores_nonsense_answers_low():
    session = InterviewSession(role="产品经理", resume_skills=["SQL", "用户调研", "Python"])

    for answer in ["asdf qwer", "不知道", "哈哈哈哈", "12345", "随便"]:
        session.next_question()
        session.answer_current(answer)

    report = session.score_report()

    assert report.total_score <= 40
    assert report.match_percent <= 45
    assert any("无效" in item or "过短" in item for item in report.feedback)


def test_interview_session_triggers_score_circuit_breaker_for_all_numeric_answers():
    session = InterviewSession(role="产品经理", resume_skills=["SQL", "用户调研", "Python"])

    for _ in range(5):
        session.next_question()
        session.answer_current("12345")

    report = session.score_report()

    assert report.total_score <= 5
    assert report.match_percent <= 10
    assert all(score <= 5 for score in report.dimensions.values())
    assert any("低质量熔断" in item for item in report.feedback)


def test_interview_session_caps_score_when_most_answers_are_invalid():
    session = InterviewSession(role="产品经理", resume_skills=["SQL", "用户调研", "Python"])
    answers = [
        "12345",
        "随便",
        "asdf qwer",
        "我会先明确目标，再用用户调研和数据分析拆解问题，最后复盘结果。",
        "我会结合业务价值、实现成本和风险排序需求，并同步关键干系人。",
    ]

    for answer in answers:
        session.next_question()
        session.answer_current(answer)

    report = session.score_report()

    assert report.total_score <= 10
    assert report.match_percent <= 14
    assert any("低质量熔断" in item for item in report.feedback)


def test_interview_session_rejects_blank_answers():
    session = InterviewSession(role="产品经理", resume_skills=["SQL"])
    session.next_question()

    with pytest.raises(ValueError, match="回答不能为空"):
        session.answer_current("   ")

    assert session.answers == []
    assert not session.is_complete


def test_interview_session_gives_low_quality_immediate_feedback():
    session = InterviewSession(role="产品经理", resume_skills=["SQL"])
    session.next_question()

    feedback = session.answer_current("随便")

    assert "过短" in feedback or "具体经历" in feedback
    assert session.answer_feedbacks == [feedback]


def test_interview_session_can_backfill_missing_feedbacks():
    session = InterviewSession(role="产品经理", resume_skills=["SQL"])
    session.answers.append("我会先明确目标，再用数据分析判断优先级，最后复盘结果。")

    session.ensure_feedbacks()

    assert len(session.answer_feedbacks) == 1
    assert "本轮反馈" in session.answer_feedbacks[0]


def test_interview_session_can_retry_last_answer():
    session = InterviewSession(role="数据分析师", resume_skills=["SQL"])
    first_question = session.next_question()
    session.answer_current("我会先明确目标，再用 SQL 分析数据并复盘结果。")

    removed = session.retry_last_answer()

    assert removed
    assert session.answers == []
    assert session.answer_feedbacks == []
    assert session.asked_questions == [first_question]
    assert not session.is_complete
