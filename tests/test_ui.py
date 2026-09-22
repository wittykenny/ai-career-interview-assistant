from career_assistant.ui import feedback_card_html, metric_card_html, status_pill_html


def test_metric_card_html_escapes_text_and_renders_value():
    html = metric_card_html("匹配<度>", "88%", "基于简历关键词")

    assert "匹配&lt;度&gt;" in html
    assert "88%" in html
    assert "基于简历关键词" in html
    assert "app-metric-card" in html


def test_status_pill_html_rejects_unknown_tone_and_escapes_text():
    html = status_pill_html("<挑战档>", tone="unexpected")

    assert "&lt;挑战档&gt;" in html
    assert "pill-blue" in html
    assert "unexpected" not in html


def test_feedback_card_html_formats_round_feedback_safely():
    html = feedback_card_html(2, "回答过短，需要补充 STAR 案例")

    assert "第2轮" in html
    assert "回答过短" in html
    assert "app-feedback-card" in html
