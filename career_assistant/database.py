from __future__ import annotations

import sqlite3
from pathlib import Path


DATA_VERSION = "official-employment-social-salary-skill-trend-v4"
OFFICIAL_EMPLOYMENT_SOURCE_URL = (
    "https://xxgk.zuel.edu.cn/_upload/article/files/95/bd/"
    "edeb71f84ca88aeaf8df2fa23a97/66b33de2-d22e-4429-853a-01af53f340f9.pdf"
)
SOCIAL_SALARY_SOURCE_URL = "https://www.stats.gov.cn/sj/zxfb/202505/t20250516_1959826.html"
JOB_SDF_SOURCE_URL = "https://arxiv.org/abs/2406.11920"
DATA_SOURCE_NOTE = (
    "就业率数据来自中南财经政法大学学校官方公开报告；薪资数据参照国家统计局社会平均工资，"
    "补充城镇非私营/私营单位分行业工资和公开招聘技能需求研究数据；"
    "用于社会薪资参考，不代表学校官方薪资或具体岗位录用薪资。"
)


# 中南财经政法大学2019年就业质量报告，表1.9 分学院就业率。
# 字段：学院、年份、统计口径、行业说明、就业率、平均薪资占位、样本量占位、去向说明、
# 签约率、灵活就业率、升学率、出国率、自主创业率、来源名称、来源链接、是否官方。
EMPLOYMENT_ROWS = [
    ("外国语学院", 2019, "本科就业率", "官方就业质量报告", 94.32, 0, 0, "分学院就业率", 35.81, 6.55, 18.34, 33.19, 0.44, "中南财经政法大学2019年就业质量报告", OFFICIAL_EMPLOYMENT_SOURCE_URL, 1),
    ("经济学院", 2019, "本科就业率", "官方就业质量报告", 98.20, 0, 0, "分学院就业率", 35.44, 7.81, 20.12, 34.53, 0.30, "中南财经政法大学2019年就业质量报告", OFFICIAL_EMPLOYMENT_SOURCE_URL, 1),
    ("金融学院", 2019, "本科就业率", "官方就业质量报告", 95.31, 0, 0, "分学院就业率", 40.07, 1.44, 20.22, 33.39, 0.18, "中南财经政法大学2019年就业质量报告", OFFICIAL_EMPLOYMENT_SOURCE_URL, 1),
    ("法学院", 2019, "本科就业率", "官方就业质量报告", 91.08, 0, 0, "分学院就业率", 28.61, 5.67, 23.94, 32.58, 0.28, "中南财经政法大学2019年就业质量报告", OFFICIAL_EMPLOYMENT_SOURCE_URL, 1),
    ("刑事司法学院", 2019, "本科就业率", "官方就业质量报告", 90.72, 0, 0, "分学院就业率", 47.42, 10.65, 22.34, 10.31, 0.00, "中南财经政法大学2019年就业质量报告", OFFICIAL_EMPLOYMENT_SOURCE_URL, 1),
    ("信息与安全工程学院", 2019, "本科就业率", "官方就业质量报告", 93.33, 0, 0, "分学院就业率", 38.22, 0.89, 33.33, 20.89, 0.00, "中南财经政法大学2019年就业质量报告", OFFICIAL_EMPLOYMENT_SOURCE_URL, 1),
    ("工商管理学院", 2019, "本科就业率", "官方就业质量报告", 96.03, 0, 0, "分学院就业率", 49.59, 1.65, 18.84, 25.62, 0.33, "中南财经政法大学2019年就业质量报告", OFFICIAL_EMPLOYMENT_SOURCE_URL, 1),
    ("财政税务学院", 2019, "本科就业率", "官方就业质量报告", 98.08, 0, 0, "分学院就业率", 39.42, 4.17, 20.83, 33.65, 0.00, "中南财经政法大学2019年就业质量报告", OFFICIAL_EMPLOYMENT_SOURCE_URL, 1),
    ("会计学院", 2019, "本科就业率", "官方就业质量报告", 98.64, 0, 0, "分学院就业率", 45.08, 5.59, 21.53, 25.93, 0.51, "中南财经政法大学2019年就业质量报告", OFFICIAL_EMPLOYMENT_SOURCE_URL, 1),
    ("公共管理学院", 2019, "本科就业率", "官方就业质量报告", 97.67, 0, 0, "分学院就业率", 49.30, 6.51, 19.53, 22.33, 0.00, "中南财经政法大学2019年就业质量报告", OFFICIAL_EMPLOYMENT_SOURCE_URL, 1),
    ("新闻与文化传播学院", 2019, "本科就业率", "官方就业质量报告", 98.54, 0, 0, "分学院就业率", 56.80, 13.11, 18.45, 7.28, 2.91, "中南财经政法大学2019年就业质量报告", OFFICIAL_EMPLOYMENT_SOURCE_URL, 1),
    ("哲学院", 2019, "本科就业率", "官方就业质量报告", 92.86, 0, 0, "分学院就业率", 46.94, 2.04, 29.59, 14.29, 0.00, "中南财经政法大学2019年就业质量报告", OFFICIAL_EMPLOYMENT_SOURCE_URL, 1),
    ("统计与数学学院", 2019, "本科就业率", "官方就业质量报告", 97.52, 0, 0, "分学院就业率", 48.35, 0.41, 25.62, 23.14, 0.00, "中南财经政法大学2019年就业质量报告", OFFICIAL_EMPLOYMENT_SOURCE_URL, 1),
    ("中韩新媒体学院", 2019, "本科就业率", "官方就业质量报告", 83.76, 0, 0, "分学院就业率", 33.95, 0.74, 3.32, 43.54, 2.21, "中南财经政法大学2019年就业质量报告", OFFICIAL_EMPLOYMENT_SOURCE_URL, 1),
    ("文澜学院", 2019, "本科就业率", "官方就业质量报告", 94.03, 0, 0, "分学院就业率", 11.94, 0.00, 41.79, 40.30, 0.00, "中南财经政法大学2019年就业质量报告", OFFICIAL_EMPLOYMENT_SOURCE_URL, 1),
]


# 国家统计局2024年城镇非私营单位分行业平均工资新闻稿，保留2023/2024用于趋势展示。
# 岗位不是国家统计局统计口径，这里按常见就业行业进行映射，便于课堂演示薪资趋势和岗位匹配。
INDUSTRY_SALARY_AVERAGES = {
    "信息传输、软件和信息技术服务业": {2023: 231810, 2024: 238966},
    "金融业": {2023: 197663, 2024: 201883},
    "科学研究和技术服务业": {2023: 171447, 2024: 175425},
    "批发和零售业": {2023: 124362, 2024: 129658},
    "租赁和商务服务业": {2023: 109264, 2024: 110353},
}

PRIVATE_INDUSTRY_SALARY_AVERAGES = {
    "信息传输、软件和信息技术服务业": {2023: 129215, 2024: 123193},
    "金融业": {2023: 124812, 2024: 135339},
    "科学研究和技术服务业": {2023: 82277, 2024: 82387},
    "批发和零售业": {2023: 63701, 2024: 67059},
    "租赁和商务服务业": {2023: 67107, 2024: 69214},
}

ROLE_INDUSTRY_MAP = {
    "数据分析师": "信息传输、软件和信息技术服务业",
    "产品经理": "信息传输、软件和信息技术服务业",
    "AI应用开发": "信息传输、软件和信息技术服务业",
    "后端开发工程师": "信息传输、软件和信息技术服务业",
    "商业分析师": "科学研究和技术服务业",
    "金融分析师": "金融业",
    "风控专员": "金融业",
    "运营专员": "批发和零售业",
    "市场营销专员": "批发和零售业",
    "会计审计专员": "租赁和商务服务业",
    "法务专员": "租赁和商务服务业",
}


def _salary_row(role: str, industry: str, year: int, salary_type: str, annual_avg: int, source_name: str) -> tuple:
    monthly_avg = round(annual_avg / 12)
    salary_low = round(monthly_avg * 0.75 / 100) * 100
    salary_high = round(monthly_avg * 1.25 / 100) * 100
    return (
        role,
        industry,
        year,
        salary_type,
        annual_avg,
        monthly_avg,
        salary_low,
        salary_high,
        source_name,
        SOCIAL_SALARY_SOURCE_URL,
    )


SALARY_REFERENCE_ROWS = [
    _salary_row(role, industry, year, "城镇非私营单位行业平均工资", annual_avg, "国家统计局2024年平均工资新闻稿（城镇非私营单位）")
    for role, industry in ROLE_INDUSTRY_MAP.items()
    for year, annual_avg in INDUSTRY_SALARY_AVERAGES[industry].items()
] + [
    _salary_row(role, industry, year, "城镇私营单位行业平均工资", annual_avg, "国家统计局2024年平均工资新闻稿（城镇私营单位）")
    for role, industry in ROLE_INDUSTRY_MAP.items()
    for year, annual_avg in PRIVATE_INDUSTRY_SALARY_AVERAGES[industry].items()
]


SKILL_TREND_ROWS = [
    ("AI技能", "AI应用开发", "RAG、Prompt、LLM API、Agent、向量检索", "公开招聘技能需求研究显示，AI相关岗位更强调技能组合而非单一学历标签。", 2024, JOB_SDF_SOURCE_URL),
    ("数据技能", "数据分析师", "SQL、Python、统计分析、可视化、业务指标", "招聘技能需求数据集覆盖岗位、公司和区域粒度，可用于分析技能需求变化。", 2024, JOB_SDF_SOURCE_URL),
    ("工程技能", "后端开发工程师", "API设计、数据库、缓存、限流、日志监控", "技术岗位更关注可验证的工程交付和问题定位能力。", 2024, JOB_SDF_SOURCE_URL),
    ("产品运营技能", "产品经理", "用户调研、需求拆解、数据分析、A/B实验、跨部门推进", "产品与运营类岗位需要把业务目标转化为指标和可执行方案。", 2024, JOB_SDF_SOURCE_URL),
    ("金融风控技能", "金融分析师", "财务分析、风险识别、SQL、Excel、合规意识", "金融相关岗位强调数据分析、风险判断和合规边界。", 2024, JOB_SDF_SOURCE_URL),
]


JOB_ROWS = [
    ("数据分析师", "信息传输、软件和信息技术服务业", "Python,SQL,数据分析,Tableau,Excel", 14900, 24900, "负责指标体系、SQL取数、可视化看板和业务洞察。"),
    ("产品经理", "信息传输、软件和信息技术服务业", "用户调研,竞品分析,需求文档,SQL,沟通协作", 14900, 24900, "负责需求分析、产品设计、项目推进和效果评估。"),
    ("金融分析师", "金融业", "金融,SQL,Python,Excel,数据分析", 12600, 21000, "负责行业研究、风险分析、财务建模和投资支持。"),
    ("AI应用开发", "信息传输、软件和信息技术服务业", "Python,机器学习,Streamlit,SQL,数据分析", 14900, 24900, "负责AI应用原型、RAG系统、模型调用和业务集成。"),
    ("后端开发工程师", "信息传输、软件和信息技术服务业", "Java,Python,SQL,API,后端开发", 14900, 24900, "负责接口开发、数据库设计、服务稳定性和业务系统迭代。"),
    ("商业分析师", "科学研究和技术服务业", "SQL,Python,数据分析,商业分析,Excel", 11000, 18300, "负责业务问题拆解、经营分析、专题报告和策略建议。"),
    ("风控专员", "金融业", "金融,风险管理,SQL,Excel,数据分析", 12600, 21000, "负责信用评估、风险监测、异常识别和风控策略支持。"),
    ("运营专员", "批发和零售业", "运营,数据分析,Excel,用户调研,沟通协作", 8100, 13500, "负责用户运营、活动执行、数据复盘和流程优化。"),
    ("市场营销专员", "批发和零售业", "市场营销,用户调研,数据分析,Excel,沟通协作", 8100, 13500, "负责市场调研、营销活动、渠道协同和效果分析。"),
    ("会计审计专员", "租赁和商务服务业", "会计,审计,Excel,财务建模,合规", 6900, 11500, "负责凭证处理、审计底稿、财务核对和内控合规支持。"),
    ("法务专员", "租赁和商务服务业", "法务,合同,合规,沟通协作,风险管理", 6900, 11500, "负责合同审核、法律检索、合规支持和业务风险提示。"),
]


def initialize_database(db_path: str | Path) -> Path:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        if _needs_rebuild(conn):
            _drop_tables(conn)
        _create_tables(conn)
        if conn.execute("SELECT COUNT(*) FROM employment_stats").fetchone()[0] == 0:
            conn.executemany(
                """
                INSERT INTO employment_stats
                (college, year, role, industry, employment_rate, avg_salary, sample_size, top_destination,
                 signed_rate, flexible_rate, further_study_rate, overseas_rate, entrepreneurship_rate,
                 source_name, source_url, is_official)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                EMPLOYMENT_ROWS,
            )
        if conn.execute("SELECT COUNT(*) FROM salary_reference").fetchone()[0] == 0:
            conn.executemany(
                """
                INSERT INTO salary_reference
                (role, industry, year, salary_type, annual_avg, monthly_avg, salary_low, salary_high, source_name, source_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                SALARY_REFERENCE_ROWS,
            )
        if conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0:
            conn.executemany(
                """
                INSERT INTO jobs (title, industry, required_skills, salary_low, salary_high, description)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                JOB_ROWS,
            )
        if conn.execute("SELECT COUNT(*) FROM skill_trends").fetchone()[0] == 0:
            conn.executemany(
                """
                INSERT INTO skill_trends (skill_group, role, hot_skills, trend_summary, year, source_url)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                SKILL_TREND_ROWS,
            )
        conn.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES ('data_version', ?)", (DATA_VERSION,))
    return path


def fetch_rows(db_path: str | Path, sql: str, params: tuple = ()) -> list[dict[str, object]]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]


def _needs_rebuild(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        row = conn.execute("SELECT value FROM metadata WHERE key = 'data_version'").fetchone()
        return row is None or row[0] != DATA_VERSION
    except sqlite3.DatabaseError:
        return True


def _drop_tables(conn: sqlite3.Connection) -> None:
    for table in ["employment_stats", "salary_reference", "jobs", "skill_trends"]:
        conn.execute(f"DROP TABLE IF EXISTS {table}")


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS employment_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            college TEXT NOT NULL,
            year INTEGER NOT NULL,
            role TEXT NOT NULL,
            industry TEXT NOT NULL,
            employment_rate REAL NOT NULL,
            avg_salary INTEGER NOT NULL,
            sample_size INTEGER NOT NULL,
            top_destination TEXT NOT NULL,
            signed_rate REAL NOT NULL,
            flexible_rate REAL NOT NULL,
            further_study_rate REAL NOT NULL,
            overseas_rate REAL NOT NULL,
            entrepreneurship_rate REAL NOT NULL,
            source_name TEXT NOT NULL,
            source_url TEXT NOT NULL,
            is_official INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS salary_reference (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            industry TEXT NOT NULL,
            year INTEGER NOT NULL,
            salary_type TEXT NOT NULL,
            annual_avg INTEGER NOT NULL,
            monthly_avg INTEGER NOT NULL,
            salary_low INTEGER NOT NULL,
            salary_high INTEGER NOT NULL,
            source_name TEXT NOT NULL,
            source_url TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            industry TEXT NOT NULL,
            required_skills TEXT NOT NULL,
            salary_low INTEGER NOT NULL,
            salary_high INTEGER NOT NULL,
            description TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS skill_trends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_group TEXT NOT NULL,
            role TEXT NOT NULL,
            hot_skills TEXT NOT NULL,
            trend_summary TEXT NOT NULL,
            year INTEGER NOT NULL,
            source_url TEXT NOT NULL
        )
        """
    )
