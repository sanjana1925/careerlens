"""Aggregates skill demand across collected job postings for a target role."""

from dataclasses import dataclass

from app.utils.skills import extract_skills


@dataclass
class SkillDemand:
    skill: str
    percentage: float
    job_count: int


def analyze_market(job_descriptions: list[str], resume_text: str = "") -> tuple[list[SkillDemand], list[str]]:
    total = len(job_descriptions)
    if total == 0:
        return [], []

    skill_counts: dict[str, int] = {}
    for description in job_descriptions:
        for skill in extract_skills(description):
            skill_counts[skill] = skill_counts.get(skill, 0) + 1

    demand = sorted(
        (SkillDemand(skill=skill, percentage=round(100 * count / total, 1), job_count=count)
         for skill, count in skill_counts.items()),
        key=lambda d: d.percentage,
        reverse=True,
    )

    skill_gaps = []
    if resume_text:
        resume_skills = extract_skills(resume_text)
        skill_gaps = [d.skill for d in demand if d.skill not in resume_skills][:10]

    return demand, skill_gaps
