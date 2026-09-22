from __future__ import annotations

from functools import lru_cache
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
SKILLS_DIR = BASE_DIR / "skills"


@lru_cache(maxsize=8)
def resume_optimizer_prompt() -> str:
    files = [
        SKILLS_DIR / "resume-optimizer-main" / "SKILL.md",
        SKILLS_DIR / "resume-optimizer-main" / "references" / "audit-checklist.md",
        SKILLS_DIR / "resume-optimizer-main" / "references" / "narrative-tools.md",
        SKILLS_DIR / "resume-optimizer-main" / "references" / "red-flags.md",
    ]
    return _join_skill_files(files, max_chars=9000)


@lru_cache(maxsize=8)
def tech_interview_prompt() -> str:
    files = [
        SKILLS_DIR / "tech-interview-skill-main" / "interview-coach" / "SKILL.md",
        SKILLS_DIR / "tech-interview-skill-main" / "tech-interview" / "SKILL.md",
        SKILLS_DIR / "tech-interview-skill-main" / "tech-interview" / "references" / "question-patterns.md",
    ]
    return _join_skill_files(files, max_chars=10000)


def _join_skill_files(files: list[Path], max_chars: int) -> str:
    chunks = []
    remaining = max_chars
    for path in files:
        if remaining <= 0:
            break
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8", errors="ignore").strip()
        if not content:
            continue
        chunk = f"\n\n# 本地Skill文件：{path.relative_to(BASE_DIR)}\n{content}"
        chunks.append(chunk[:remaining])
        remaining -= len(chunks[-1])
    return "\n".join(chunks).strip()
