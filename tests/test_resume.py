from career_assistant.resume import analyze_resume, skill_tag_weights, _extract_suggestion_lines


def test_analyze_resume_extracts_profile_skills_and_suggestions():
    text = """
    张三
    求职目标：产品经理
    教育经历：中南财经政法大学 信息管理与信息系统
    项目经历：使用 Python、SQL、机器学习 和 Streamlit 构建数据分析助手
    实习经历：负责用户调研、竞品分析、需求文档和数据看板
    """

    profile = analyze_resume(text, target_role="产品经理")

    assert profile.name == "张三"
    assert "Python" in profile.skills
    assert "SQL" in profile.skills
    assert profile.target_role == "产品经理"
    assert profile.match_score >= 70
    assert any("量化" in item or "指标" in item for item in profile.suggestions)


def test_extract_suggestion_lines_merges_markdown_sections():
    content = """
    # 简历优化建议（目标岗位：产品经理）

    ## 建议1：求职目标与岗位严重不匹配

    **问题**：求职目标写“AI应用开发”，与产品经理岗位方向冲突。
    **影响**：面试官会怀疑投递动机。
    **怎么改**：把目标改为产品经理，并补充用户调研和需求文档证据。

    ## 建议2：项目结果缺少量化

    **问题**：只写完成系统，没有结果。
    **影响**：难以判断贡献。
    **怎么改**：补充转化率、效率提升或用户规模。
    """

    lines = _extract_suggestion_lines(content, limit=3)

    assert len(lines) == 2
    assert "求职目标与岗位严重不匹配" in lines[0]
    assert "问题：" in lines[0]
    assert "影响：" in lines[0]
    assert "怎么改：" in lines[0]
    assert not lines[0].startswith("#")
    assert "项目结果缺少量化" in lines[1]


def test_extract_suggestion_lines_keeps_normal_bullets():
    content = "- 补充量化指标\n- 强化岗位关键词\n"

    assert _extract_suggestion_lines(content, limit=3) == ["补充量化指标", "强化岗位关键词"]


def test_skill_tag_weights_prioritizes_target_role_skills():
    weights = skill_tag_weights(["Excel", "Python", "SQL", "Streamlit"], "AI应用开发")
    by_skill = {str(item["skill"]): int(item["weight"]) for item in weights}

    assert by_skill["Python"] > by_skill["Excel"]
    assert by_skill["SQL"] > by_skill["Excel"]
    assert weights[0]["matched"] is True
