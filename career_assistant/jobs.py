from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .database import fetch_rows
from .interview import ScoreReport
from .resume import ROLE_KEYWORDS, ResumeProfile


@dataclass(frozen=True)
class JobMatch:
    title: str
    industry: str
    required_skills: list[str]
    matched_skills: list[str]
    missing_skills: list[str]
    match_score: int
    salary_range: str
    description: str
    detail: str
    reference_url: str


@dataclass(frozen=True)
class SalaryPrediction:
    role: str
    low: int
    high: int
    basis: str


def match_jobs(profile: ResumeProfile, db_path: str | Path, interview_report: ScoreReport | None = None) -> list[JobMatch]:
    rows = fetch_rows(db_path, "SELECT title, industry, required_skills, salary_low, salary_high, description FROM jobs")
    matches = []
    profile_skills = set(profile.skills)
    for row in rows:
        required = [skill.strip() for skill in str(row["required_skills"]).split(",")]
        matched = sorted(profile_skills & set(required))
        missing = [skill for skill in required if skill not in profile_skills]
        score = calculate_job_match_score(profile, str(row["title"]), required, matched, interview_report)
        matches.append(
            JobMatch(
                title=str(row["title"]),
                industry=str(row["industry"]),
                required_skills=required,
                matched_skills=matched,
                missing_skills=missing,
                match_score=score,
                salary_range=f"{row['salary_low']}-{row['salary_high']} 元/月",
                description=str(row["description"]),
                detail=_job_detail(str(row["title"]), str(row["description"]), required),
                reference_url=_job_reference_url(str(row["title"])),
            )
        )
    return sorted(matches, key=lambda item: item.match_score, reverse=True)


def calculate_job_match_score(
    profile: ResumeProfile,
    job_title: str,
    required_skills: list[str],
    matched_skills: list[str],
    interview_report: ScoreReport | None = None,
) -> int:
    skill_coverage = len(matched_skills) / max(1, len(required_skills))
    resume_component = profile.match_score * 0.30
    skill_component = skill_coverage * 38
    target_component = 24 if job_title == profile.target_role else _related_role_bonus(profile.target_role, job_title)
    evidence_component = min(8, len(profile.projects) * 2 + min(4, len(profile.skills) // 2))
    interview_component = _interview_component(interview_report, job_title)
    return max(5, min(98, round(resume_component + skill_component + target_component + evidence_component + interview_component)))


def generate_learning_path(profile: ResumeProfile, target_role: str = "") -> list[str]:
    role = target_role or profile.target_role
    expected = ROLE_KEYWORDS.get(role, ROLE_KEYWORDS["AI应用开发"])
    missing = [skill for skill in expected if skill not in profile.skills]
    if role == "数据分析师":
        missing = ["SQL进阶", "统计分析"] + [skill for skill in missing if skill not in {"SQL"}]
    if not missing:
        missing = ["高阶项目复盘", "业务指标设计", "面试表达"]
    path = [f"第{i + 1}周：补强 {skill}，完成一个可展示的小作品或案例复盘。" for i, skill in enumerate(missing[:4])]
    path.append("面试前：准备 3 个 STAR 项目故事，分别对应专业能力、协作能力和抗压能力。")
    return path


def predict_salary_range(profile: ResumeProfile, role: str, db_path: str | Path) -> SalaryPrediction:
    rows = fetch_rows(
        db_path,
        """
        SELECT salary_low, salary_high, source_name
        FROM salary_reference
        WHERE role = ?
        ORDER BY year DESC
        LIMIT 1
        """,
        (role,),
    )
    if rows:
        base_low = int(rows[0]["salary_low"])
        base_high = int(rows[0]["salary_high"])
        source_name = str(rows[0]["source_name"])
    else:
        job_rows = fetch_rows(db_path, "SELECT salary_low, salary_high FROM jobs WHERE title = ?", (role,))
        base_low = int(job_rows[0]["salary_low"]) if job_rows else 10000
        base_high = int(job_rows[0]["salary_high"]) if job_rows else 18000
        source_name = "岗位薪资参考表"
    adjustment = int((profile.match_score - 75) * 80)
    low = max(8000, base_low + adjustment)
    high = max(low + 2000, base_high + adjustment)
    basis = f"参照{source_name}中的国家统计局行业社会平均工资，并结合简历匹配度做区间调整；不代表学校官方薪资。"
    return SalaryPrediction(role=role, low=low, high=high, basis=basis)


def _related_role_bonus(target_role: str, job_title: str) -> int:
    if target_role == job_title:
        return 12
    related_groups = [
        {"AI应用开发", "后端开发工程师", "数据分析师"},
        {"产品经理", "运营专员", "市场营销专员", "商业分析师"},
        {"金融分析师", "风控专员", "会计审计专员"},
        {"法务专员", "风控专员", "会计审计专员"},
    ]
    return 6 if any(target_role in group and job_title in group for group in related_groups) else 0


def _interview_component(report: ScoreReport | None, job_title: str) -> int:
    if report is None:
        return 6
    professional = report.dimensions.get("专业匹配", report.total_score)
    logic = report.dimensions.get("逻辑结构", report.total_score)
    expression = report.dimensions.get("表达能力", report.total_score)
    interview_score = professional * 0.45 + logic * 0.30 + expression * 0.25
    role_weight = 1.0
    if job_title in {"产品经理", "商业分析师", "运营专员", "市场营销专员"}:
        role_weight = 1.05
    if job_title in {"AI应用开发", "后端开发工程师", "数据分析师"}:
        role_weight = 1.08
    return round(max(0, min(14, (interview_score - 50) / 50 * 14 * role_weight)))


def _job_detail(title: str, description: str, required_skills: list[str]) -> str:
    detail_map = {
        "数据分析师": "典型工作包括指标体系建设、SQL取数、数据清洗、可视化看板、异常归因和业务复盘。面试重点关注 SQL、统计分析、业务理解和结论表达。",
        "产品经理": "典型工作包括用户调研、需求分析、竞品分析、原型设计、优先级排序和跨部门推进。面试重点关注需求判断、沟通协作、数据意识和项目复盘。",
        "金融分析师": "典型工作包括行业研究、财务分析、风险识别、估值建模和投资支持。面试重点关注财务指标、宏观理解、逻辑严谨性和合规意识。",
        "AI应用开发": "典型工作包括模型 API 调用、RAG 原型、Prompt 设计、向量库检索、工具调用、Streamlit 展示和部署监控。面试重点关注工程闭环、异常兜底和效果评估。",
        "后端开发工程师": "典型工作包括接口开发、数据库设计、服务稳定性、日志监控和业务系统迭代。面试重点关注基础工程能力、SQL、接口设计和排障思路。",
        "商业分析师": "典型工作包括经营指标拆解、专题分析、数据建模、策略建议和管理层汇报。面试重点关注业务理解、分析框架、SQL/Python 和结论表达。",
        "风控专员": "典型工作包括信用评估、风险监测、异常识别、策略复盘和合规协同。面试重点关注风险意识、金融基础、数据分析和边界判断。",
        "运营专员": "典型工作包括用户运营、活动执行、渠道协同、数据复盘和流程优化。面试重点关注执行闭环、用户理解、数据敏感度和沟通协作。",
        "市场营销专员": "典型工作包括市场调研、营销活动、内容策划、渠道管理和效果分析。面试重点关注目标人群、转化路径、数据复盘和创意落地。",
        "会计审计专员": "典型工作包括凭证处理、审计底稿、财务核对、内控测试和合规支持。面试重点关注会计基础、Excel、审慎性和职业规范。",
        "法务专员": "典型工作包括合同审核、法律检索、合规提示、业务沟通和风险跟踪。面试重点关注合同条款、法律检索、表达严谨性和业务理解。",
    }
    base = detail_map.get(title, description)
    return f"{base} 核心技能：{'、'.join(required_skills)}。"


def _job_reference_url(title: str) -> str:
    return f"https://www.baidu.com/s?wd={title}+岗位职责+招聘要求"
