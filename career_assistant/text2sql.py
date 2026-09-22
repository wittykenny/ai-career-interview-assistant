from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .database import fetch_rows
from .llm import DashScopeLLM, llm_api_configured


@dataclass(frozen=True)
class SQLQueryResult:
    question: str
    sql: str
    rows: list[dict[str, object]]
    chart_type: str
    explanation: str


@dataclass(frozen=True)
class SQLSpec:
    sql: str
    chart_type: str
    params: tuple = ()
    explanation: str = ""


def nl_to_sql(question: str) -> SQLSpec:
    normalized = question.lower()
    if _contains_any(question, ["技能趋势", "技能需求", "热门技能", "AI技能", "岗位技能", "招聘技能"]):
        role = _detect_role(question)
        if role:
            return SQLSpec(
                sql="""
                    SELECT year, role, skill_group, hot_skills, trend_summary, source_url
                    FROM skill_trends
                    WHERE role = ?
                    ORDER BY year DESC
                """,
                chart_type="table",
                params=(role,),
                explanation="技能趋势来自公开招聘技能需求研究数据集摘要，用于展示岗位能力要求变化方向。",
            )
        return SQLSpec(
            sql="""
                SELECT year, role, skill_group, hot_skills, trend_summary, source_url
                FROM skill_trends
                ORDER BY role
            """,
            chart_type="table",
            explanation="技能趋势来自公开招聘技能需求研究数据集摘要，用于展示岗位能力要求变化方向。",
        )
    if _contains_any(question, ["行业薪资", "行业工资", "行业收入", "不同行业", "薪资对比", "工资对比"]):
        salary_type_filter = "城镇私营单位行业平均工资" if _contains_any(question, ["私营", "民企"]) else "城镇非私营单位行业平均工资"
        return SQLSpec(
            sql="""
                SELECT year, industry, ROUND(AVG(monthly_avg), 0) AS monthly_avg,
                       MIN(salary_low) AS salary_low, MAX(salary_high) AS salary_high,
                       source_name, source_url
                FROM salary_reference
                WHERE year = (SELECT MAX(year) FROM salary_reference)
                  AND salary_type = ?
                GROUP BY year, industry, source_name, source_url
                ORDER BY monthly_avg DESC
            """,
            chart_type="bar",
            params=(salary_type_filter,),
            explanation="按国家统计局分行业平均工资聚合展示不同行业的社会薪资参考。",
        )
    if _contains_any(question, ["最高薪资", "薪资最高", "工资最高", "收入最高"]):
        return SQLSpec(
            sql="""
                SELECT role, industry, MAX(year) AS latest_year, MAX(monthly_avg) AS monthly_avg,
                       MAX(salary_high) AS salary_high, source_name, source_url
                FROM salary_reference
                GROUP BY role, industry, source_name, source_url
                ORDER BY monthly_avg DESC
            """,
            chart_type="bar",
            explanation="按国家统计局社会平均工资映射后的岗位月均薪资排序，仅作社会薪资参考。",
        )
    if _contains_any(question, ["薪资", "工资", "收入"]) or "salary" in normalized:
        role = _detect_role(question)
        return SQLSpec(
            sql="""
                SELECT year, role, industry, annual_avg, monthly_avg, salary_low, salary_high, source_name, source_url
                FROM salary_reference
                WHERE role = ?
                ORDER BY year
            """,
            chart_type="line",
            params=(role,),
            explanation="薪资数据参照国家统计局社会平均工资，按岗位常见行业映射，不代表学校官方薪资。",
        )
    if _contains_any(question, ["就业率", "就业", "签约", "升学", "出国"]):
        colleges = _detect_colleges(question)
        if len(colleges) > 1:
            placeholders = ", ".join("?" for _ in colleges)
            return SQLSpec(
                sql=f"""
                    SELECT year, college, role, employment_rate, signed_rate, further_study_rate,
                           overseas_rate, entrepreneurship_rate, source_name, source_url
                    FROM employment_stats
                    WHERE college IN ({placeholders})
                    ORDER BY employment_rate DESC
                """,
                chart_type="bar",
                params=tuple(colleges),
                explanation="就业数据来自中南财经政法大学官方就业质量报告，用于多学院对比。",
            )
        if colleges:
            return SQLSpec(
                sql="""
                    SELECT year, college, role, employment_rate, signed_rate, further_study_rate,
                           overseas_rate, entrepreneurship_rate, source_name, source_url
                    FROM employment_stats
                    WHERE college = ?
                    ORDER BY year
                """,
                chart_type="bar",
                params=(colleges[0],),
                explanation="就业数据来自中南财经政法大学官方就业质量报告。",
            )
        return SQLSpec(
            sql="""
                SELECT year, college, role, employment_rate, signed_rate, further_study_rate,
                       overseas_rate, entrepreneurship_rate, source_name, source_url
                FROM employment_stats
                ORDER BY employment_rate DESC
            """,
            chart_type="bar",
            explanation="就业数据来自中南财经政法大学官方就业质量报告。",
        )
    if _contains_any(question, ["岗位", "职位"]):
        return SQLSpec(
            sql="""
                SELECT title, industry, required_skills, salary_low, salary_high
                FROM jobs
                ORDER BY salary_high DESC
            """,
            chart_type="bar",
            explanation="岗位薪资区间参照国家统计局行业平均工资折算，仅作社会薪资参考。",
        )
    return SQLSpec(
        sql="""
            SELECT year, college, role, employment_rate, signed_rate, further_study_rate,
                   overseas_rate, entrepreneurship_rate, source_name, source_url
            FROM employment_stats
            ORDER BY employment_rate DESC
        """,
        chart_type="table",
        explanation="默认展示中南财经政法大学官方就业质量报告中的学院就业数据。",
    )


def execute_nl_query(question: str, db_path: str | Path) -> SQLQueryResult:
    spec = nl_to_sql(question)
    validate_readonly_sql(spec.sql)
    rows = fetch_rows(db_path, spec.sql, spec.params)
    explanation = f"{spec.explanation} 已转换为只读SQL，共返回 {len(rows)} 条记录。"
    ai_insight = build_ai_data_insight(question, rows, explanation)
    if ai_insight:
        explanation = f"{explanation}\n\n就业建议：{ai_insight}"
    return SQLQueryResult(
        question=question,
        sql=" ".join(spec.sql.split()),
        rows=rows,
        chart_type=spec.chart_type,
        explanation=explanation,
    )


def build_ai_data_insight(question: str, rows: list[dict[str, object]], base_explanation: str) -> str:
    if not llm_api_configured() or not rows:
        return ""
    sample_rows = rows[:8]
    prompt = f"""
你是就业数据分析助手。请基于自然语言问题、SQL查询说明和结果样例，给应届生一段就业建议。

用户问题：{question}
查询说明：{base_explanation}
结果样例：{sample_rows}

要求：
1. 不要夸大数据，不要说这是企业录用薪资。
2. 明确指出趋势/对比结论。
3. 给出1-2条求职行动建议。
4. 不超过140字。
"""
    response = DashScopeLLM().generate(prompt)
    if response.offline:
        return ""
    return " ".join(response.content.split())[:220]


def validate_readonly_sql(sql: str) -> None:
    compact = re.sub(r"\s+", " ", sql.strip()).upper()
    if not compact.startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed.")
    forbidden = [" INSERT ", " UPDATE ", " DELETE ", " DROP ", " ALTER ", " CREATE ", " PRAGMA ", " ATTACH "]
    padded = f" {compact} "
    if any(token in padded for token in forbidden):
        raise ValueError("Unsafe SQL operation rejected.")


def _detect_role(question: str) -> str:
    role_keywords = {
        "后端开发工程师": ["后端", "后端开发", "Java", "接口", "API"],
        "商业分析师": ["商业分析", "经营分析", "策略分析"],
        "风控专员": ["风控", "风险管理", "风险"],
        "会计审计专员": ["会计", "审计", "财务核算"],
        "法务专员": ["法务", "法律", "合同", "合规"],
        "运营专员": ["运营", "用户增长", "活动"],
        "市场营销专员": ["市场", "营销", "渠道"],
    }
    for role, keywords in role_keywords.items():
        if any(keyword in question for keyword in keywords):
            return role
    if "金融" in question:
        return "金融分析师"
    if "产品" in question:
        return "产品经理"
    if "AI" in question or "人工智能" in question or "开发" in question:
        return "AI应用开发"
    return "数据分析师"


def _detect_college(question: str) -> str:
    colleges = _detect_colleges(question)
    return colleges[0] if colleges else ""


def _detect_colleges(question: str) -> list[str]:
    college_keywords = {
        "外国语学院": ["外国语学院", "外语", "英语"],
        "经济学院": ["经济学院", "经济"],
        "金融学院": ["金融学院", "金融"],
        "法学院": ["法学院", "法学", "法律"],
        "刑事司法学院": ["刑事司法学院", "刑事司法", "司法"],
        "信息与安全工程学院": ["信息与安全工程学院", "信息学院", "信息", "数据"],
        "工商管理学院": ["工商管理学院", "工商", "产品"],
        "财政税务学院": ["财政税务学院", "财政", "税务"],
        "会计学院": ["会计学院", "会计"],
        "公共管理学院": ["公共管理学院", "公共管理", "公管"],
        "新闻与文化传播学院": ["新闻与文化传播学院", "新闻", "传播"],
        "哲学院": ["哲学院", "哲学"],
        "统计与数学学院": ["统计与数学学院", "统计学院", "统计", "数学"],
        "中韩新媒体学院": ["中韩新媒体学院", "中韩", "新媒体"],
        "文澜学院": ["文澜学院", "文澜"],
    }
    matches = []
    for college, keywords in college_keywords.items():
        if any(keyword in question for keyword in keywords):
            matches.append(college)
    return matches


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)
