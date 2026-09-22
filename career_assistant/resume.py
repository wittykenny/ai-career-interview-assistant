from __future__ import annotations

import re
from dataclasses import dataclass

from .llm import DashScopeLLM, llm_api_configured
from .skill_prompts import resume_optimizer_prompt


SKILL_ALIASES = {
    "Python": ["python", "py"],
    "SQL": ["sql", "mysql", "sqlite", "postgresql"],
    "机器学习": ["机器学习", "machine learning", "ml"],
    "数据分析": ["数据分析", "数据看板", "指标", "可视化", "analysis"],
    "Streamlit": ["streamlit"],
    "RAG": ["rag", "向量检索", "知识库", "embedding"],
    "Prompt": ["prompt", "提示词"],
    "用户调研": ["用户调研", "访谈", "问卷"],
    "竞品分析": ["竞品", "竞品分析"],
    "需求文档": ["需求文档", "prd", "原型"],
    "沟通协作": ["沟通", "跨部门", "协作"],
    "金融": ["金融", "证券", "银行", "风控"],
    "Excel": ["excel", "透视表"],
    "Tableau": ["tableau", "powerbi", "bi"],
    "Java": ["java", "spring"],
    "后端开发": ["后端开发", "后端", "接口", "服务端"],
    "API": ["api", "接口"],
    "商业分析": ["商业分析", "经营分析", "策略分析"],
    "风险管理": ["风险管理", "风控", "风险监测"],
    "会计": ["会计", "财务核算", "凭证"],
    "审计": ["审计", "底稿", "内控"],
    "财务建模": ["财务建模", "估值", "财务分析"],
    "合规": ["合规", "内控", "监管"],
    "法务": ["法务", "法律", "法学"],
    "合同": ["合同", "协议"],
    "运营": ["运营", "活动策划", "用户增长"],
    "市场营销": ["市场营销", "营销", "渠道"],
}

ROLE_KEYWORDS = {
    "产品经理": ["用户调研", "竞品分析", "需求文档", "数据分析", "沟通协作", "SQL"],
    "数据分析师": ["SQL", "Python", "数据分析", "机器学习", "Excel", "Tableau"],
    "金融分析师": ["金融", "SQL", "Python", "数据分析", "Excel"],
    "AI应用开发": ["Python", "机器学习", "Streamlit", "RAG", "Prompt", "API", "SQL"],
    "后端开发工程师": ["Java", "Python", "SQL", "API", "后端开发"],
    "商业分析师": ["SQL", "Python", "数据分析", "商业分析", "Excel"],
    "风控专员": ["金融", "风险管理", "SQL", "Excel", "数据分析"],
    "运营专员": ["运营", "数据分析", "Excel", "用户调研", "沟通协作"],
    "市场营销专员": ["市场营销", "用户调研", "数据分析", "Excel", "沟通协作"],
    "会计审计专员": ["会计", "审计", "Excel", "财务建模", "合规"],
    "法务专员": ["法务", "合同", "合规", "沟通协作", "风险管理"],
}


@dataclass(frozen=True)
class ResumeProfile:
    name: str
    target_role: str
    skills: list[str]
    education: str
    projects: list[str]
    suggestions: list[str]
    match_score: int


def analyze_resume(text: str, target_role: str = "") -> ResumeProfile:
    clean_text = text.strip()
    role = target_role or _extract_after(clean_text, ["求职目标", "目标岗位", "应聘岗位"]) or "通用岗位"
    skills = extract_skills(clean_text)
    name = _extract_name(clean_text)
    education = _extract_line(clean_text, ["教育经历", "教育背景", "毕业院校"])
    projects = _extract_project_lines(clean_text)
    match_score = calculate_match_score(skills, role, clean_text)
    suggestions = build_suggestions(clean_text, skills, role, match_score)
    suggestions.extend(build_ai_resume_suggestions(clean_text, skills, role, match_score))
    return ResumeProfile(
        name=name,
        target_role=role,
        skills=skills,
        education=education,
        projects=projects,
        suggestions=suggestions,
        match_score=match_score,
    )


def extract_skills(text: str) -> list[str]:
    lowered = text.lower()
    found: list[str] = []
    for skill, aliases in SKILL_ALIASES.items():
        if any(alias.lower() in lowered for alias in aliases):
            found.append(skill)
    return found


def calculate_match_score(skills: list[str], role: str, resume_text: str = "") -> int:
    expected = ROLE_KEYWORDS.get(role, ROLE_KEYWORDS.get("AI应用开发", []))
    if not expected:
        return min(95, 55 + len(skills) * 6)
    matched = len(set(skills) & set(expected))
    coverage = matched / max(1, len(expected))
    evidence_bonus = _resume_evidence_bonus(resume_text)
    breadth_bonus = min(8, max(0, len(skills) - matched) * 2)
    return min(98, 45 + round(coverage * 42) + evidence_bonus + breadth_bonus)


def build_suggestions(text: str, skills: list[str], role: str, match_score: int) -> list[str]:
    suggestions = [
        "把项目经历改写为“动作 + 产物 + 结果”：例如说明你交付了什么系统/看板/流程，以及影响了谁。",
        "补充量化证据：优先写转化率、效率提升、错误率下降、用户数、数据量、处理时长等可验证指标。",
    ]
    expected = ROLE_KEYWORDS.get(role, [])
    missing = [skill for skill in expected if skill not in skills]
    if missing:
        suggestions.append(f"针对{role}补充或强化关键词：{'、'.join(missing[:4])}。")
    if "项目经历" not in text and "项目" not in text:
        suggestions.append("增加 1-2 个项目经历，并为每个项目补一句背景：服务对象、业务问题、你的角色。")
    if match_score < 75:
        suggestions.append("当前匹配度偏中等，建议把简历开头改成三行核心优势摘要，优先呈现目标岗位相关证据。")
    return suggestions


def build_ai_resume_suggestions(text: str, skills: list[str], role: str, match_score: int) -> list[str]:
    if not llm_api_configured() or not text.strip():
        return []

    system = (
        "你是一名严格但站在求职者一侧的简历审计官。"
        "必须遵守本地 resume-optimizer skill：不编造成果，优先量化，围绕目标岗位做匹配优化。"
        f"\n\n{resume_optimizer_prompt()[:8000]}"
    )
    prompt = f"""
请基于下面的应届生简历，给出 3 条高价值简历优化建议。

目标岗位：{role}
已识别技能：{", ".join(skills) or "暂未识别"}
本地匹配度：{match_score}%
简历内容：
{text[:2200]}

输出要求：
1. 每条建议必须包含“问题/影响/怎么改”。
2. 不能编造项目背景、指标或职责，缺失信息用“待补”说明。
3. 优先指出会影响面试转化率的问题。
4. 只输出 3 条短建议。
"""
    response = DashScopeLLM().generate(prompt, system=system)
    if response.offline:
        return []
    return [f"简历审阅：{item}" for item in _extract_suggestion_lines(response.content, limit=3)]


def skill_tag_weights(skills: list[str], role: str = "") -> list[dict[str, int | str | bool]]:
    expected = ROLE_KEYWORDS.get(role, [])
    expected_rank = {skill: index for index, skill in enumerate(expected)}
    rank_span = max(1, len(expected_rank) - 1)
    weighted: list[dict[str, int | str | bool]] = []
    for index, skill in enumerate(skills):
        if skill in expected_rank:
            priority_bonus = round((rank_span - expected_rank[skill]) / rank_span * 16)
            weight = 84 + priority_bonus
            matched = True
        else:
            weight = max(38, 58 - index * 3)
            matched = False
        weighted.append({"skill": skill, "weight": min(100, weight), "matched": matched})
    return sorted(weighted, key=lambda item: int(item["weight"]), reverse=True)


def _extract_suggestion_lines(content: str, limit: int = 3) -> list[str]:
    suggestions: list[str] = []
    current_title = ""
    current_parts: list[str] = []

    def flush_current() -> None:
        nonlocal current_title, current_parts
        item = _compose_suggestion(current_title, current_parts)
        if item and item not in suggestions:
            suggestions.append(item)
        current_title = ""
        current_parts = []

    for raw_line in content.splitlines():
        line = _clean_suggestion_line(raw_line)
        if not line:
            continue

        heading = _extract_recommendation_heading(line)
        if heading:
            flush_current()
            current_title = heading
            continue

        if _is_resume_review_title(line):
            continue

        if current_title or _is_review_detail_line(line):
            current_parts.append(line)
        elif line not in suggestions:
            suggestions.append(line)

        if len(suggestions) >= limit:
            break

    flush_current()
    if not suggestions and content.strip():
        suggestions.append(_clean_suggestion_line(content.strip())[:260])
    return [_truncate_suggestion(item) for item in suggestions[:limit]]


def _clean_suggestion_line(raw_line: str) -> str:
    line = raw_line.strip()
    line = re.sub(r"^#{1,6}\s*", "", line)
    line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
    line = re.sub(r"^[-*•]\s*", "", line)
    line = re.sub(r"^\d+[.、)]\s*", "", line)
    line = re.sub(r"\s+", " ", line)
    return line.strip()


def _extract_recommendation_heading(line: str) -> str:
    match = re.match(r"^建议\s*[一二三四五六七八九十\d]+\s*[:：]\s*(.+)$", line)
    if match:
        return match.group(1).strip()
    return ""


def _is_resume_review_title(line: str) -> bool:
    titles = ["简历优化建议", "简历审阅", "简历审计", "简历诊断", "优化建议", "修改建议"]
    return any(line.startswith(title) and len(line) <= 40 for title in titles)


def _is_review_detail_line(line: str) -> bool:
    return bool(re.match(r"^(问题|影响|怎么改|修改建议|建议动作|示例|原因|风险|补充)[:：]", line))


def _compose_suggestion(title: str, parts: list[str]) -> str:
    if title and parts:
        return f"{title}：" + " ".join(parts)
    if title:
        return title
    if parts:
        return " ".join(parts)
    return ""


def _truncate_suggestion(item: str, max_length: int = 280) -> str:
    item = item.strip()
    if len(item) <= max_length:
        return item
    return item[: max_length - 1].rstrip("，。；、 ") + "…"


def _resume_evidence_bonus(text: str) -> int:
    if not text:
        return 0
    bonus = 0
    if re.search(r"\d+%|\d+\s*(人|次|条|万|小时|天|周|月|元|秒|ms|qps)", text, re.IGNORECASE):
        bonus += 6
    if any(token in text for token in ["项目经历", "实习经历", "比赛", "看板", "系统", "平台", "报告"]):
        bonus += 4
    if any(token in text for token in ["负责", "主导", "设计", "优化", "推动", "落地", "复盘"]):
        bonus += 3
    return min(12, bonus)


def _extract_name(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(key in stripped for key in ["求职", "教育", "项目", "实习", "技能", "电话", "邮箱"]):
            continue
        if len(stripped) <= 12:
            return stripped
    return "未识别姓名"


def _extract_after(text: str, labels: list[str]) -> str:
    for label in labels:
        match = re.search(rf"{label}\s*[:：]\s*([^\n\r]+)", text)
        if match:
            return match.group(1).strip()
    return ""


def _extract_line(text: str, labels: list[str]) -> str:
    for line in text.splitlines():
        if any(label in line for label in labels):
            return line.strip()
    return ""


def _extract_project_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if "项目" in line or "实习" in line][:5]
