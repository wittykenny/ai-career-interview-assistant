from __future__ import annotations

from dataclasses import dataclass, field

from .llm import DashScopeLLM, llm_api_configured
from .skill_prompts import tech_interview_prompt


QUESTION_BANK = {
    "产品经理": [
        "请用一个项目说明你如何发现并验证用户需求？",
        "如果研发资源不足，你如何做需求优先级排序？",
        "讲一次你推动跨部门协作的经历。",
        "如何判断一个功能上线后的效果是否达标？",
        "如果用户反馈和数据结论冲突，你会怎么处理？",
    ],
    "数据分析师": [
        "请介绍一次你用 SQL 解决业务问题的经历。",
        "如何设计一个核心业务指标体系？",
        "发现数据异常时你会如何定位原因？",
        "请解释 JOIN、窗口函数在分析中的使用场景。",
        "如何把分析结论转化为业务建议？",
    ],
    "AI应用开发": [
        "请介绍你的 RAG 或大模型应用项目，重点讲清楚完整链路。",
        "如果向量检索结果不相关，你会从哪些环节排查？",
        "模型 API 超时或返回为空时，你的系统如何兜底？",
        "你如何评估一个 AI 求职助手的回答质量？",
        "如果把这个项目生产化，你会补哪些工程能力？",
    ],
    "后端开发工程师": [
        "请介绍一个你设计过的接口，重点说明入参、出参和异常处理。",
        "你如何设计一个简历解析接口的幂等和限流？",
        "SQL 查询慢时你会如何定位和优化？",
        "如何设计服务日志、监控和告警？",
        "如果上游服务不稳定，后端如何保证用户体验？",
    ],
}


@dataclass(frozen=True)
class ScoreReport:
    dimensions: dict[str, int]
    total_score: int
    match_percent: int
    feedback: list[str]


@dataclass
class InterviewSession:
    role: str
    resume_skills: list[str] = field(default_factory=list)
    resume_text: str = ""
    answers: list[str] = field(default_factory=list)
    asked_questions: list[str] = field(default_factory=list)
    answer_feedbacks: list[str] = field(default_factory=list)

    def next_question(self) -> str:
        questions = QUESTION_BANK.get(self.role, QUESTION_BANK["产品经理"])
        if len(self.asked_questions) >= 5:
            return "面试已完成，请查看评分报告。"
        question = _ai_next_question(self.role, self.resume_skills, self.resume_text, self.asked_questions, self.answers)
        if not question:
            question = questions[len(self.asked_questions) % len(questions)]
        self.asked_questions.append(question)
        return question

    def answer_current(self, answer: str) -> str:
        if not answer.strip():
            raise ValueError("回答不能为空")
        if not self.asked_questions:
            self.next_question()
        clean_answer = answer.strip()
        self.answers.append(clean_answer)
        feedback = _ai_immediate_feedback(self.role, self.asked_questions[-1], clean_answer, self.resume_skills, self.resume_text)
        if not feedback:
            feedback = _immediate_feedback(clean_answer, _answer_quality(clean_answer), self.resume_skills)
        self.answer_feedbacks.append(feedback)
        return feedback

    def retry_last_answer(self) -> bool:
        if not self.answers:
            return False
        self.answers.pop()
        if self.answer_feedbacks:
            self.answer_feedbacks.pop()
        return True

    @property
    def is_complete(self) -> bool:
        return len(self.answers) >= 5

    def score_report(self, include_ai: bool = True) -> ScoreReport:
        self.ensure_feedbacks()
        combined = " ".join(self.answers)
        quality_scores = [_answer_quality(answer) for answer in self.answers]
        invalid_count = sum(score < 20 for score in quality_scores)
        average_quality = round(sum(quality_scores) / max(1, len(quality_scores)))
        valid_count = sum(score >= 45 for score in quality_scores)
        completion_bonus = min(10, valid_count * 2)

        expression = _clamp(20 + average_quality * 0.50 + completion_bonus + _keyword_bonus(combined, ["首先", "其次", "最后", "结构化", "第一", "第二"]) * 2)
        professional = _clamp(18 + average_quality * 0.45 + completion_bonus + _keyword_bonus(combined, self.resume_skills) * 6 + _keyword_bonus(combined, ["数据分析", "用户调研", "SQL", "Python", "指标", "RAG", "API"]) * 3)
        logic = _clamp(18 + average_quality * 0.45 + completion_bonus + _keyword_bonus(combined, ["目标", "原因", "方案", "结果", "复盘", "数据"]) * 4)
        motivation = _clamp(23 + average_quality * 0.42 + completion_bonus + _keyword_bonus(combined, ["岗位", "业务", "用户", "价值", "成长"]) * 4)
        dimensions = {
            "表达能力": expression,
            "专业匹配": professional,
            "逻辑结构": logic,
            "岗位动机": motivation,
        }

        circuit_breaker_feedback = _circuit_breaker_feedback(invalid_count, len(self.answers))
        if circuit_breaker_feedback:
            capped_score = 3 if invalid_count == len(self.answers) else 10
            dimensions = {name: min(score, capped_score) for name, score in dimensions.items()}

        total = round(sum(dimensions.values()) / len(dimensions))
        if circuit_breaker_feedback:
            match_percent = 3 if invalid_count == len(self.answers) else min(14, total + 4)
        else:
            match_percent = max(total + 4, _clamp(round(total * 0.72 + professional * 0.18 + min(100, len(self.resume_skills) * 10) * 0.10)))
        feedback = []
        if circuit_breaker_feedback:
            feedback.append(circuit_breaker_feedback)
        if valid_count <= 1:
            feedback.append("多数回答无效或过短，请围绕问题给出具体经历、行动和结果。")
        elif valid_count < len(self.answers):
            feedback.append("部分回答过短或信息不足，建议每题至少说明背景、行动和结果。")
        else:
            feedback.append("回答中已经体现结构化思路，建议继续增加具体业务指标和技术/方法细节。")
        feedback.append("每题尽量补充情境、任务、行动、结果，形成完整 STAR 闭环。")
        if professional < 75:
            feedback.append("专业关键词和岗位证据出现偏少，建议结合简历技能补充工具、方法和行业知识。")
        ai_feedback = _ai_report_feedback(self.role, self.asked_questions, self.answers, dimensions, total) if include_ai else ""
        if ai_feedback:
            feedback.append(ai_feedback)
        return ScoreReport(dimensions=dimensions, total_score=total, match_percent=match_percent, feedback=feedback)

    def ensure_feedbacks(self) -> None:
        while len(self.answer_feedbacks) < len(self.answers):
            answer = self.answers[len(self.answer_feedbacks)]
            self.answer_feedbacks.append(_immediate_feedback(answer, _answer_quality(answer), self.resume_skills))


def _ai_next_question(role: str, resume_skills: list[str], resume_text: str, asked_questions: list[str], answers: list[str]) -> str:
    if not llm_api_configured():
        return ""
    history = "\n".join(
        f"Q{i + 1}: {question}\nA{i + 1}: {answers[i] if i < len(answers) else ''}"
        for i, question in enumerate(asked_questions)
    )
    system = _interview_system(role)
    prompt = f"""
你正在扮演 {role} 岗位面试官，请生成第 {len(asked_questions) + 1} 轮面试问题。

候选人简历技能：{", ".join(resume_skills) or "暂未识别"}
简历片段：{resume_text[:1000] or "暂未提供"}
已问历史：
{history or "暂无"}

要求：
1. 只输出一个问题。
2. 每轮只问一个问题，不要给提示。
3. 问题必须贴合候选人简历和目标岗位。
4. 五轮应覆盖自我介绍、项目深挖、专业能力、工程/业务决策、压力或协作场景，避免重复。
"""
    response = DashScopeLLM().generate(prompt, system=system)
    if response.offline:
        return ""
    question = " ".join(response.content.split())
    if "？" in question:
        question = question.split("？", 1)[0] + "？"
    elif "?" in question:
        question = question.split("?", 1)[0] + "?"
    return question[:180]


def _ai_immediate_feedback(role: str, question: str, answer: str, resume_skills: list[str], resume_text: str) -> str:
    if not llm_api_configured():
        return ""
    prompt = f"""
请作为 {role} 面试官点评候选人的本轮回答。

问题：{question}
回答：{answer[:1200]}
候选人技能：{", ".join(resume_skills) or "暂未识别"}
简历片段：{resume_text[:800] or "暂未提供"}

要求：
1. 如果回答模糊，优先指出缺少的细节或追问方向。
2. 如果有技术错误，直接纠正。
3. 用“优点/问题/改进”三段，每段一句。
4. 不超过 160 字。
"""
    response = DashScopeLLM().generate(prompt, system=_interview_system(role))
    if response.offline:
        return ""
    return f"本轮点评：{' '.join(response.content.split())[:260]}"


def _ai_report_feedback(
    role: str,
    asked_questions: list[str],
    answers: list[str],
    dimensions: dict[str, int],
    total_score: int,
) -> str:
    if not llm_api_configured() or not answers:
        return ""
    transcript = "\n".join(f"Q{i + 1}: {q}\nA{i + 1}: {answers[i]}" for i, q in enumerate(asked_questions) if i < len(answers))
    prompt = f"""
请基于下面 5 轮模拟面试记录，生成最终提升建议。

本地评分：{dimensions}
总分：{total_score}
面试记录：
{transcript[:2500]}

要求：输出 1 段话，不超过 180 字，指出最关键短板、下一步训练建议、简历中需要校准的地方。
"""
    response = DashScopeLLM().generate(prompt, system=_interview_system(role))
    if response.offline:
        return ""
    return f"复盘建议：{' '.join(response.content.split())[:260]}"


def _interview_system(role: str) -> str:
    return (
        f"你是一名严格、专业、直接的 {role} 模拟面试官。"
        "遵守本地 tech-interview skill：一次只问一个问题，从简历出发，追问模糊回答，指出夸大和错误。"
        f"\n\n{tech_interview_prompt()[:9000]}"
    )


def _keyword_bonus(text: str, keywords: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for keyword in keywords if keyword and keyword.lower() in lowered)


def _answer_quality(answer: str) -> int:
    stripped = answer.strip()
    lowered = stripped.lower()
    if len(stripped) < 6:
        return 0
    low_signal = ["不知道", "不会", "随便", "哈哈", "asdf", "qwer", "12345", "test"]
    if any(token in lowered for token in low_signal) and len(stripped) < 20:
        return 5
    if stripped.isdigit():
        return 0
    if _has_repeated_noise(stripped):
        return 8
    signal_keywords = [
        "目标",
        "用户",
        "数据",
        "分析",
        "结果",
        "方案",
        "项目",
        "调研",
        "指标",
        "复盘",
        "业务",
        "需求",
        "行动",
        "SQL",
        "Python",
        "STAR",
        "RAG",
        "API",
    ]
    keyword_score = min(56, _keyword_bonus(stripped, signal_keywords) * 9)
    length_score = min(32, len(stripped) // 2)
    structure_score = 14 if any(token in stripped for token in ["首先", "其次", "最后", "第一", "第二", "然后"]) else 0
    method_score = 8 if any(token in stripped for token in ["验证", "排序", "复盘", "指标", "风险", "转化率", "留存率"]) else 0
    return _clamp(8 + keyword_score + length_score + structure_score + method_score)


def _immediate_feedback(answer: str, quality: int, resume_skills: list[str]) -> str:
    if quality < 20:
        return "本轮反馈：回答过短或信息不足，请补充具体经历、行动步骤和结果。"
    skill_hits = _keyword_bonus(answer, resume_skills)
    structure_hits = _keyword_bonus(answer, ["目标", "行动", "结果", "复盘", "数据", "指标"])
    if quality >= 70 and structure_hits >= 2:
        return "本轮反馈：回答结构较清晰，已经体现行动和结果，建议再补充量化指标。"
    if skill_hits > 0:
        return "本轮反馈：已结合简历技能作答，建议用 STAR 结构补全背景、任务、行动和结果。"
    return "本轮反馈：方向基本相关，建议加入岗位关键词、工具方法和可量化成果。"


def _clamp(value: int | float) -> int:
    return max(0, min(100, int(value)))


def _has_repeated_noise(text: str) -> bool:
    compact = "".join(char for char in text.strip() if not char.isspace())
    if len(compact) < 4:
        return False
    if len(set(compact)) <= 2 and len(compact) >= 4:
        return True
    return any(char * 4 in compact for char in set(compact))


def _circuit_breaker_feedback(invalid_count: int, answer_count: int) -> str:
    if answer_count == 0:
        return ""
    if invalid_count == answer_count:
        return "检测到全部回答无效或过短，已触发低质量熔断：总分仅保留最低演示分。"
    if invalid_count >= 3:
        return f"检测到 {invalid_count} 轮回答无效或过短，已触发低质量熔断：总分最高不超过 10 分。"
    return ""
