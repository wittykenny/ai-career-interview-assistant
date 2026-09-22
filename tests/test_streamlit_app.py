from streamlit.testing.v1 import AppTest

from career_assistant.resume import analyze_resume


def test_streamlit_app_renders_core_workflow_controls(monkeypatch):
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    app = AppTest.from_file("app.py", default_timeout=10)
    app.run()

    assert not app.exception
    assert any("职途 AI 面试助手" in item.value for item in app.markdown)
    assert any(button.label == "分析简历" for button in app.button)
    assert any(button.label == "快速检索" for button in app.button)
    assert any(button.label == "AI检索" for button in app.button)
    assert any(button.label == "开始/重置面试" for button in app.button)
    assert any(button.label == "查询数据" for button in app.button)
    assert any(button.label == "一键填入测试简历" for button in app.button)
    assert any(button.label == "各学院就业率排名" for button in app.button)
    assert any(button.label == "法学院本科就业率" for button in app.button)
    assert any("面试题库" in item.value for item in app.markdown)
    assert any("服务状态" in item.value for item in app.markdown)
    assert any("准备进度" in item.value for item in app.markdown)
    forbidden = [
        "默认使用本地知识库",
        "在线大模型",
        "离线演示模式",
        "当前RAG模式",
        "AI润色",
        "把简历、面试、岗位和就业数据放在同一个准备台里",
    ]
    assert not any(word in item.value for item in app.markdown for word in forbidden)


def test_streamlit_resume_analysis_unlocks_job_match_controls():
    app = AppTest.from_file("app.py", default_timeout=10)
    app.session_state["profile"] = analyze_resume(
        "张三 Python SQL Streamlit RAG Prompt 项目经历",
        "AI应用开发",
    )
    app.run()

    assert not app.exception
    assert any("查看学习路径" == button.label for button in app.button)
    assert any("查看岗位详情" == button.label for button in app.button)
    assert any("导出修改清单" == button.label for button in app.download_button)


def test_streamlit_interview_controls_include_retry_and_early_report():
    app = AppTest.from_file("app.py", default_timeout=10)
    app.session_state["profile"] = analyze_resume(
        "张三 Python SQL 数据分析 项目经历",
        "数据分析师",
    )
    app.run()

    assert not app.exception
    assert any("重新回答上一轮" == button.label for button in app.button)
    assert any("结束面试并查看报告" == button.label for button in app.button)
