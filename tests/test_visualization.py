from career_assistant.visualization import tag_cloud_html


def test_tag_cloud_html_renders_uniform_skill_labels_and_escapes_text():
    html = tag_cloud_html(
        [
            {"skill": "Python<script>", "weight": 100, "matched": True},
            {"skill": "Excel", "weight": 40, "matched": False},
        ]
    )

    assert "skill-cloud" in html
    assert "skill-cloud-chip" in html
    assert "font-size:" not in html
    assert "目标岗位核心技能" in html
    assert "Python&lt;script&gt;" in html
    assert "Python<script>" not in html
