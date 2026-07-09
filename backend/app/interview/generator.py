"""EMBEDHUNT AI — Interview Question Generator"""
import asyncio
from dataclasses import dataclass, field
from app.config.logging import get_logger
from app.config.settings import settings
from app.interview.question_bank import get_questions_for_skills, get_all_questions_flat

logger = get_logger(__name__)

@dataclass
class InterviewKit:
    job_title: str; company: str; readiness_score: int
    questions_by_skill: dict[str, list[dict]]
    all_questions: list[dict]
    focus_skills: list[str]
    coding_topics: list[str]
    checklist: list[str]
    total_questions: int
    preparation_summary: str

CODING_TOPICS = {
    "c": ["Bit manipulation","Linked list","Ring buffer","State machine","Sorting algorithms"],
    "c++": ["Templates","STL containers","Smart pointers","Design patterns","Move semantics"],
    "python": ["File I/O","Regular expressions","Data structures","OOP","Testing with pytest"],
    "rtos": ["Task synchronization","Deadlock prevention","ISR-safe operations","Timer callbacks"],
    "linux kernel": ["Kernel module","Character driver","Proc filesystem","Sysfs attributes"],
    "arm": ["Startup code","Linker script","Assembly instructions","Cache management"],
}

INTERVIEW_CHECKLIST = [
    "Review all matched skills with depth",
    "Practice coding problems without IDE assistance",
    "Study company's product domain (automotive/semiconductor/IoT)",
    "Prepare 2-3 project examples demonstrating embedded experience",
    "Review system design for embedded systems",
    "Practice explaining trade-offs (latency vs throughput, power vs performance)",
    "Study recent papers/patents from target company",
    "Prepare questions for the interviewer about tech stack and team",
]

def generate_interview_kit(job_title: str, company: str, matched_skills: list[str], match_score: int) -> InterviewKit:
    questions_by_skill = get_questions_for_skills(matched_skills, max_per_skill=3)
    all_questions = get_all_questions_flat(matched_skills)
    coding_topics = []
    for skill in matched_skills:
        coding_topics.extend(CODING_TOPICS.get(skill, []))
    coding_topics = list(dict.fromkeys(coding_topics))[:10]
    readiness = min(99, match_score + (len(questions_by_skill) * 2))
    summary = (
        f"You matched {len(matched_skills)} required skills for {job_title} at {company}. "
        f"Estimated interview readiness: {readiness}/99. "
        f"Focus on: {', '.join(matched_skills[:4])}."
    )
    return InterviewKit(
        job_title=job_title, company=company, readiness_score=readiness,
        questions_by_skill=questions_by_skill, all_questions=all_questions,
        focus_skills=matched_skills[:5], coding_topics=coding_topics,
        checklist=INTERVIEW_CHECKLIST, total_questions=len(all_questions),
        preparation_summary=summary,
    )


async def generate_interview_kit_ai(
    job_title: str, company: str, matched_skills: list[str], match_score: int,
    *, db, user_id: str,
) -> InterviewKit:
    """Static ``generate_interview_kit`` enriched with company-specific AI questions.

    AI-generated questions are prepended to the static bank (AI first, then
    static). The kit shape is unchanged. Any failure or the master toggle being
    off returns the static kit unchanged.
    """
    kit = generate_interview_kit(job_title, company, matched_skills, match_score)
    if not settings.LLM_ENRICHMENT_ENABLED:
        logger.info("interview_generator_path", path="fallback", reason="disabled")
        return kit
    skill = matched_skills[0] if matched_skills else "embedded"
    try:
        from app.agents.interview_agent import InterviewAgent

        ai_questions = await asyncio.wait_for(
            InterviewAgent(db).generate_questions(
                user_id, skill, company, difficulty="medium",
            ),
            timeout=settings.LLM_ENRICHMENT_TIMEOUT_SECONDS,
        )
        converted = [
            {
                "q": q.text,
                "type": q.type or "core",
                "difficulty": q.difficulty or "medium",
                "expected": q.expected_answer_outline,
                "skill": skill,
                "source": "ai",
            }
            for q in ai_questions if q.text
        ]
        if converted:
            existing = kit.questions_by_skill.get(skill, [])
            kit.questions_by_skill[skill] = converted + existing
            kit.all_questions = converted + kit.all_questions
            kit.total_questions = len(kit.all_questions)
        logger.info("interview_generator_path", path="ai_enriched", ai_questions=len(converted))
    except Exception as e:  # noqa: BLE001 — enrichment must never break the endpoint
        logger.warning("ai_enrichment_failed", module=__name__, error=str(e))
        return kit
    return kit
