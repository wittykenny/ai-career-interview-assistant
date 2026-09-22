from __future__ import annotations

from html import escape


_TONES = {"blue", "green", "amber", "slate"}


def page_styles() -> str:
    return """
<style>
    :root {
        --bg: #eef6f7;
        --bg-2: #f7f3ea;
        --surface: rgba(255, 255, 255, 0.82);
        --surface-strong: #ffffff;
        --surface-soft: #f4faf8;
        --border: #cfdedb;
        --border-strong: #a9c5c0;
        --text: #142338;
        --muted: #65758a;
        --blue: #365f9f;
        --blue-soft: #e6efff;
        --teal: #12736d;
        --teal-soft: #dff5ef;
        --amber: #9a6515;
        --amber-soft: #fff1cb;
        --rose-soft: #f9e9e6;
        --slate-soft: #eaf0f2;
        --shadow: 0 18px 48px rgba(31, 68, 72, 0.10);
    }

    html, body, [class*="css"], .stApp, .stMarkdown, .stTextInput, .stTextArea, .stSelectbox, button {
        font-family: "Inter", "Segoe UI", "Microsoft YaHei", "PingFang SC", Arial, sans-serif !important;
        letter-spacing: 0 !important;
    }

    .stApp {
        background:
            radial-gradient(circle at 8% 3%, rgba(218, 242, 236, 0.95) 0, rgba(218, 242, 236, 0.0) 34%),
            radial-gradient(circle at 94% 2%, rgba(255, 232, 184, 0.72) 0, rgba(255, 232, 184, 0.0) 30%),
            linear-gradient(135deg, var(--bg) 0%, #f8fbf8 52%, var(--bg-2) 100%);
        color: var(--text);
    }

    .block-container {
        max-width: 1240px;
        padding: 24px 28px 44px;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #15333b 0%, #10263a 100%);
        border-right: 0;
    }

    [data-testid="stSidebar"] * {
        color: #e5edf7 !important;
    }

    [data-testid="stSidebar"] .stMarkdown p {
        color: #b8c4d6 !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        border-bottom: 0;
        background: rgba(255, 255, 255, 0.56);
        border: 1px solid rgba(169, 197, 192, 0.72);
        border-radius: 999px;
        padding: 7px;
        width: fit-content;
        box-shadow: 0 10px 26px rgba(35, 84, 87, 0.08);
        margin-bottom: 14px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 40px;
        border-radius: 999px;
        color: var(--muted);
        font-weight: 760;
        padding: 0 18px;
        border: 1px solid transparent;
        background: transparent;
        transition: all 160ms ease;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(223, 245, 239, 0.68);
        color: var(--teal);
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #ffffff 0%, #e5f7f1 100%);
        color: var(--text);
        border: 1px solid #91c9bd;
        box-shadow: 0 8px 18px rgba(18, 115, 109, 0.16);
    }

    .stButton > button,
    .stDownloadButton > button,
    .stFormSubmitButton > button,
    [data-testid="stLinkButton"] a {
        border-radius: 6px !important;
        border: 1px solid var(--border-strong) !important;
        font-weight: 700 !important;
        min-height: 38px;
        background: rgba(255, 255, 255, 0.86) !important;
        color: var(--text) !important;
    }

    .stButton > button[kind="primary"],
    .stFormSubmitButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2d67a4 0%, #158178 100%) !important;
        border-color: #1c7b87 !important;
        color: #fff !important;
        box-shadow: 0 10px 22px rgba(21, 129, 120, 0.18);
    }

    .stTextInput input,
    .stTextArea textarea,
    .stSelectbox div[data-baseweb="select"] > div,
    .stFileUploader section {
        border-radius: 10px !important;
        border-color: var(--border) !important;
        background: rgba(255, 255, 255, 0.86) !important;
        box-shadow: 0 8px 22px rgba(35, 84, 87, 0.045);
    }

    .stSelectbox div[data-baseweb="select"] > div {
        min-height: 42px;
        border-color: #a9d2ca !important;
    }

    .stSelectbox div[data-baseweb="select"] svg {
        color: var(--teal);
    }

    .app-hero {
        background:
            linear-gradient(135deg, rgba(255, 255, 255, 0.90) 0%, rgba(232, 247, 244, 0.88) 58%, rgba(255, 247, 223, 0.80) 100%);
        border: 1px solid rgba(169, 197, 192, 0.76);
        border-radius: 18px;
        box-shadow: var(--shadow);
        padding: 26px 30px;
        margin-bottom: 20px;
        display: grid;
        grid-template-columns: 1.5fr 1fr;
        gap: 20px;
        align-items: end;
        position: relative;
        overflow: hidden;
    }

    .app-hero::before {
        content: "";
        position: absolute;
        inset: 0;
        background:
            linear-gradient(90deg, rgba(54, 95, 159, 0.08), transparent 38%),
            linear-gradient(180deg, transparent 0%, rgba(255,255,255,0.35) 100%);
        pointer-events: none;
    }

    .app-hero > * {
        position: relative;
        z-index: 1;
    }

    .app-hero-title {
        margin: 0;
        color: var(--text);
        font-size: 34px;
        line-height: 1.24;
        font-weight: 850;
    }

    .app-hero-subtitle {
        margin: 8px 0 0;
        color: var(--muted);
        font-size: 15px;
        line-height: 1.7;
    }

    .app-hero-right {
        display: flex;
        justify-content: flex-end;
        align-items: center;
    }

    .app-pill-row {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        justify-content: flex-end;
    }

    .app-pill {
        display: inline-flex;
        align-items: center;
        border-radius: 999px;
        border: 1px solid rgba(169, 197, 192, 0.82);
        padding: 6px 11px;
        font-size: 12px;
        font-weight: 750;
        line-height: 1.2;
        white-space: nowrap;
    }

    .pill-blue { background: var(--blue-soft); color: #214a8f; border-color: #b9ccf2; }
    .pill-green { background: var(--teal-soft); color: #0d665f; border-color: #a8dcd2; }
    .pill-amber { background: var(--amber-soft); color: #854d0e; border-color: #f6dd9b; }
    .pill-slate { background: var(--slate-soft); color: #334155; border-color: #c9d7db; }

    .app-section {
        margin: 16px 0 14px;
    }

    .app-section h2 {
        margin: 0;
        font-size: 20px;
        line-height: 1.35;
        color: var(--text);
        font-weight: 800;
    }

    .app-section p {
        margin: 4px 0 0;
        color: var(--muted);
        font-size: 13px;
        line-height: 1.65;
    }

    .app-metric-card,
    .app-note-panel,
    .app-feedback-card,
    .app-source-card {
        border: 1px solid rgba(169, 197, 192, 0.72);
        border-radius: 12px;
        background: var(--surface);
        padding: 14px 16px;
        margin-bottom: 12px;
        backdrop-filter: blur(8px);
    }

    .app-metric-card {
        box-shadow: 0 8px 22px rgba(15, 23, 42, 0.04);
    }

    .app-metric-label,
    .app-card-kicker {
        color: var(--muted);
        font-size: 12px;
        font-weight: 750;
    }

    .app-metric-value {
        color: var(--text);
        font-size: 27px;
        line-height: 1.25;
        font-weight: 820;
        margin-top: 5px;
    }

    .app-metric-caption,
    .app-note-panel,
    .app-source-card {
        color: var(--muted);
        font-size: 13px;
        line-height: 1.65;
    }

    .app-feedback-card {
        border-left: 4px solid var(--teal);
    }

    .app-feedback-title {
        color: var(--text);
        font-size: 13px;
        font-weight: 780;
        margin-bottom: 6px;
    }

    .app-feedback-body {
        color: #334155;
        font-size: 13px;
        line-height: 1.7;
    }

    .app-source-card {
        background: rgba(244, 250, 248, 0.88);
    }

    .skill-cloud {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        align-items: center;
        padding: 12px;
        border: 1px solid rgba(169, 197, 192, 0.72);
        border-radius: 12px;
        background: rgba(244, 250, 248, 0.86);
        margin-bottom: 14px;
    }

    .skill-cloud-chip {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-height: 34px;
        padding: 7px 12px;
        border: 1px solid;
        border-radius: 999px;
        font-size: 13px;
        font-weight: 750;
        line-height: 1.2;
        white-space: nowrap;
        letter-spacing: 0;
    }

    .skill-cloud-empty {
        color: var(--muted);
        font-size: 13px;
        padding: 14px 0;
    }

    @media (max-width: 820px) {
        .block-container { padding: 18px 14px 36px; }
        .app-hero { grid-template-columns: 1fr; padding: 20px; }
        .app-hero-right, .app-pill-row { justify-content: flex-start; }
        .app-hero-title { font-size: 24px; }
    }
</style>
""".strip()


def hero_html(title: str, subtitle: str, pills: list[tuple[str, str]]) -> str:
    pill_html = "".join(status_pill_html(text, tone) for text, tone in pills)
    return (
        "<div class='app-hero'>"
        "<div>"
        f"<h1 class='app-hero-title'>{escape(title)}</h1>"
        f"<p class='app-hero-subtitle'>{escape(subtitle)}</p>"
        "</div>"
        f"<div class='app-hero-right'><div class='app-pill-row'>{pill_html}</div></div>"
        "</div>"
    )


def status_pill_html(text: str, tone: str = "blue") -> str:
    normalized_tone = tone if tone in _TONES else "blue"
    return f"<span class='app-pill pill-{normalized_tone}'>{escape(text)}</span>"


def section_header_html(title: str, subtitle: str = "") -> str:
    subtitle_html = f"<p>{escape(subtitle)}</p>" if subtitle else ""
    return f"<div class='app-section'><h2>{escape(title)}</h2>{subtitle_html}</div>"


def metric_card_html(label: str, value: str, caption: str = "") -> str:
    caption_html = f"<div class='app-metric-caption'>{escape(caption)}</div>" if caption else ""
    return (
        "<div class='app-metric-card'>"
        f"<div class='app-metric-label'>{escape(label)}</div>"
        f"<div class='app-metric-value'>{escape(value)}</div>"
        f"{caption_html}"
        "</div>"
    )


def note_panel_html(text: str) -> str:
    return f"<div class='app-note-panel'>{escape(text)}</div>"


def feedback_card_html(round_index: int, feedback: str) -> str:
    suggestion = "下一轮补充背景、行动、结果和量化指标。"
    if "过短" in feedback or "信息不足" in feedback:
        suggestion = "至少补充一个具体经历，并说明你做了什么、结果如何。"
    elif "量化" in feedback or "结构" in feedback:
        suggestion = "保留当前结构，再增加数据指标或业务结果。"
    return (
        "<div class='app-feedback-card'>"
        f"<div class='app-feedback-title'>第{round_index}轮点评</div>"
        f"<div class='app-feedback-body'><strong>观察：</strong>{escape(feedback)}<br>"
        f"<strong>建议：</strong>{escape(suggestion)}</div>"
        "</div>"
    )


def source_card_html(title: str, content: str) -> str:
    return (
        "<div class='app-source-card'>"
        f"<div class='app-card-kicker'>{escape(title)}</div>"
        f"<div>{escape(content)}</div>"
        "</div>"
    )
