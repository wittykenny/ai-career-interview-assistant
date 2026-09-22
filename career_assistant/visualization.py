from __future__ import annotations

from html import escape

import plotly.graph_objects as go


def radar_chart(dimensions: dict[str, int]) -> go.Figure:
    labels = list(dimensions.keys())
    values = list(dimensions.values())
    fig = go.Figure(
        data=[
            go.Scatterpolar(
                r=values + values[:1],
                theta=labels + labels[:1],
                fill="toself",
                name="竞争力",
            )
        ]
    )
    fig.update_layout(polar={"radialaxis": {"visible": True, "range": [0, 100]}}, showlegend=False, height=360)
    return fig


def donut_chart(percent: int, title: str = "岗位匹配度") -> go.Figure:
    fig = go.Figure(data=[go.Pie(values=[percent, 100 - percent], labels=["匹配", "待提升"], hole=0.72)])
    fig.update_layout(title=title, height=320, annotations=[{"text": f"{percent}%", "showarrow": False, "font": {"size": 28}}])
    return fig


def bar_chart(rows: list[dict[str, object]], x: str, y: str, title: str) -> go.Figure:
    return go.Figure(data=[go.Bar(x=[row[x] for row in rows], y=[row[y] for row in rows])]).update_layout(title=title, height=360)


def line_chart(rows: list[dict[str, object]], x: str, y: str, title: str) -> go.Figure:
    return go.Figure(data=[go.Scatter(x=[row[x] for row in rows], y=[row[y] for row in rows], mode="lines+markers")]).update_layout(title=title, height=360)


def tag_cloud_html(skills: list[str] | list[dict[str, int | str | bool]]) -> str:
    items = sorted(_normalize_tag_cloud_items(skills), key=lambda item: int(item["weight"]), reverse=True)
    if not items:
        return "<div class='skill-cloud-empty'>暂未识别到技能关键词</div>"
    palette = [
        ("#edf3ff", "#1d4ed8", "#bfd2ff"),
        ("#e8f7f4", "#0f766e", "#b6e5de"),
        ("#fff7df", "#92400e", "#f0d48a"),
        ("#f0f4f8", "#334155", "#d7e0eb"),
        ("#f7eefb", "#7e22ce", "#e2c4f0"),
        ("#eef7ec", "#3f6212", "#c9e8be"),
    ]
    chips = []
    for index, item in enumerate(items):
        skill = str(item["skill"])
        matched = bool(item.get("matched", False))
        background, color, border = palette[index % len(palette)]
        border_width = 2 if matched else 1
        title = "目标岗位核心技能" if matched else "简历技能"
        chips.append(
            "<span class='skill-cloud-chip' "
            f"title='{title}' "
            f"style='background:{background};color:{color};border-color:{border};"
            f"border-width:{border_width}px;'>{escape(skill)}</span>"
        )
    return "<div class='skill-cloud'>" + "".join(chips) + "</div>"


def _normalize_tag_cloud_items(skills: list[str] | list[dict[str, int | str | bool]]) -> list[dict[str, int | str | bool]]:
    items: list[dict[str, int | str | bool]] = []
    for index, item in enumerate(skills):
        if isinstance(item, dict):
            skill = str(item.get("skill", "")).strip()
            if not skill:
                continue
            weight = int(item.get("weight", 50))
            items.append(
                {
                    "skill": skill,
                    "weight": max(35, min(100, weight)),
                    "matched": bool(item.get("matched", False)),
                }
            )
        else:
            skill = str(item).strip()
            if skill:
                items.append({"skill": skill, "weight": max(35, 58 - index * 3), "matched": False})
    return items
