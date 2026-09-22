from pathlib import Path

import pytest

from career_assistant.database import (
    OFFICIAL_EMPLOYMENT_SOURCE_URL,
    SOCIAL_SALARY_SOURCE_URL,
    initialize_database,
)
from career_assistant.jobs import generate_learning_path, match_jobs, predict_salary_range
from career_assistant.resume import analyze_resume
from career_assistant.text2sql import execute_nl_query, validate_readonly_sql


def test_database_contains_expanded_salary_and_job_catalog(tmp_path: Path):
    db_path = tmp_path / "career.db"
    initialize_database(db_path)

    salary_roles = execute_nl_query("哪些岗位薪资最高", db_path)
    job_catalog = execute_nl_query("有哪些岗位可以投递", db_path)

    assert len({row["role"] for row in salary_roles.rows}) >= 10
    assert len(job_catalog.rows) >= 10
    assert {"法务专员", "风控专员", "运营专员", "会计审计专员"}.issubset(
        {row["role"] for row in salary_roles.rows}
    )


def test_database_contains_full_2019_undergraduate_college_employment_table(tmp_path: Path):
    db_path = tmp_path / "career.db"
    initialize_database(db_path)

    result = execute_nl_query("各学院就业率排名", db_path)

    colleges = {row["college"] for row in result.rows}
    assert len(colleges) >= 15
    assert {"法学院", "财政税务学院", "公共管理学院", "中韩新媒体学院", "文澜学院"}.issubset(colleges)


def test_text2sql_detects_new_college_employment_queries(tmp_path: Path):
    db_path = tmp_path / "career.db"
    initialize_database(db_path)

    result = execute_nl_query("法学院本科就业率", db_path)

    assert result.rows
    assert result.rows[0]["college"] == "法学院"
    assert result.rows[0]["employment_rate"] == 91.08
    assert result.rows[0]["source_url"] == OFFICIAL_EMPLOYMENT_SOURCE_URL


def test_text2sql_supports_industry_salary_comparison(tmp_path: Path):
    db_path = tmp_path / "career.db"
    initialize_database(db_path)

    result = execute_nl_query("不同行业薪资对比", db_path)

    assert "salary_reference" in result.sql
    assert "industry" in result.sql
    assert result.chart_type == "bar"
    assert len(result.rows) >= 2
    assert result.rows[0]["monthly_avg"] >= result.rows[-1]["monthly_avg"]


def test_text2sql_detects_new_role_salary_queries(tmp_path: Path):
    db_path = tmp_path / "career.db"
    initialize_database(db_path)

    result = execute_nl_query("法务专员近两年薪资变化", db_path)

    assert result.rows
    assert {row["role"] for row in result.rows} == {"法务专员"}
    assert result.chart_type == "line"


def test_text2sql_salary_query_uses_social_average_salary_reference(tmp_path: Path):
    db_path = tmp_path / "career.db"
    initialize_database(db_path)

    result = execute_nl_query("数据分析师近两年薪资变化", db_path)

    assert "SELECT" in result.sql.upper()
    assert "salary_reference" in result.sql
    assert len(result.rows) >= 2
    assert result.chart_type == "line"
    assert result.rows[-1]["monthly_avg"] > 10000
    assert result.rows[-1]["source_url"] == SOCIAL_SALARY_SOURCE_URL
    assert "社会平均工资" in result.explanation


def test_text2sql_employment_query_uses_official_zuel_report(tmp_path: Path):
    db_path = tmp_path / "career.db"
    initialize_database(db_path)

    result = execute_nl_query("金融学院本科就业率", db_path)

    assert "employment_stats" in result.sql
    assert result.rows[0]["college"] == "金融学院"
    assert result.rows[0]["employment_rate"] == 95.31
    assert result.rows[0]["source_url"] == OFFICIAL_EMPLOYMENT_SOURCE_URL
    assert "官方就业质量报告" in result.explanation


def test_text2sql_salary_ranking_query_returns_highest_salary_roles(tmp_path: Path):
    db_path = tmp_path / "career.db"
    initialize_database(db_path)

    result = execute_nl_query("哪些岗位薪资最高", db_path)

    assert "salary_reference" in result.sql
    assert "monthly_avg" in result.sql
    assert result.rows
    assert result.rows[0]["monthly_avg"] >= result.rows[-1]["monthly_avg"]
    assert result.chart_type == "bar"


def test_text2sql_employment_ranking_query_returns_college_rank(tmp_path: Path):
    db_path = tmp_path / "career.db"
    initialize_database(db_path)

    result = execute_nl_query("各学院就业率排名", db_path)

    assert "employment_stats" in result.sql
    assert "employment_rate" in result.sql
    assert result.rows
    assert result.rows[0]["employment_rate"] >= result.rows[-1]["employment_rate"]
    assert result.chart_type == "bar"


def test_text2sql_compares_multiple_colleges(tmp_path: Path):
    db_path = tmp_path / "career.db"
    initialize_database(db_path)

    result = execute_nl_query("金融学院和会计学院就业率对比", db_path)

    colleges = {row["college"] for row in result.rows}
    assert {"金融学院", "会计学院"}.issubset(colleges)
    assert "IN" in result.sql
    assert result.chart_type == "bar"


def test_text2sql_rejects_write_operations():
    with pytest.raises(ValueError):
        validate_readonly_sql("DROP TABLE employment_stats")


def test_job_matching_learning_path_and_salary_prediction(tmp_path: Path):
    db_path = tmp_path / "career.db"
    initialize_database(db_path)
    profile = analyze_resume("李四\nPython SQL 数据分析 可视化 项目经历", target_role="数据分析师")

    matches = match_jobs(profile, db_path)
    path = generate_learning_path(profile, target_role="数据分析师")
    salary = predict_salary_range(profile, "数据分析师", db_path)

    assert matches[0].match_score >= matches[-1].match_score
    assert matches[0].match_score > 0
    assert any("SQL" in item or "统计" in item for item in path)
    assert salary.low >= 10000
    assert salary.high > salary.low
    assert "国家统计局" in salary.basis


def test_job_matching_prioritizes_declared_target_role_when_reasonably_matched(tmp_path: Path):
    db_path = tmp_path / "career.db"
    initialize_database(db_path)
    profile = analyze_resume(
        "李明\n求职目标：数据分析师\nPython SQL 数据分析 Streamlit 机器学习 项目经历",
        target_role="数据分析师",
    )

    matches = match_jobs(profile, db_path)

    assert matches[0].title == "数据分析师"


def test_job_matching_results_include_detail_and_reference_link(tmp_path: Path):
    db_path = tmp_path / "career.db"
    initialize_database(db_path)
    profile = analyze_resume(
        "李明\n求职目标：AI应用开发\nPython SQL Streamlit RAG Prompt 项目经历",
        target_role="AI应用开发",
    )

    matches = match_jobs(profile, db_path)

    assert matches
    assert matches[0].detail
    assert matches[0].reference_url.startswith("https://")
    assert "AI应用开发" in matches[0].reference_url
