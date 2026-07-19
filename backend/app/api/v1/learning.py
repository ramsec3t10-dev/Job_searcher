"""EMBEDHUNT AI — Curriculum API (topic-by-topic learning)."""
from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import get_current_user_id
from app.database.session import get_db
from app.learning import curriculum
from app.learning.curriculum import get_lesson, get_track, lesson_payload, list_tracks

router = APIRouter(prefix="/learning", tags=["Learning"])


@router.get("/tracks", summary="All curriculum tracks with lesson summaries")
async def tracks(user_id: str = Depends(get_current_user_id)):
    return {"tracks": list_tracks()}


@router.get("/tracks/{track_id}", summary="One track with its lesson list")
async def track_detail(track_id: str, user_id: str = Depends(get_current_user_id)):
    t = get_track(track_id)
    if not t:
        raise HTTPException(404, f"Track {track_id} not found.")
    return t.summary()


@router.get("/lessons/{lesson_id}",
            summary="Full lesson: teaching sections + practice questions for exactly this topic")
async def lesson_detail(lesson_id: str, user_id: str = Depends(get_current_user_id)):
    lesson = get_lesson(lesson_id)
    if not lesson:
        raise HTTPException(404, f"Lesson {lesson_id} not found.")
    return lesson_payload(lesson)


@router.get("/plan",
            summary="Personalised plan: only the topics this user lacks for their target jobs")
async def personal_plan(user_id: str = Depends(get_current_user_id),
                        db: AsyncSession = Depends(get_db)):
    """Compares the resume (candidate profile) against the user's top matched
    jobs and marks every lesson: `required` (closes a gap for a target job),
    `optional` (already demonstrated on the resume), or `recommended`."""
    from app.recommendation.engine import run_matching
    from app.services.profile_service import ProfileService

    try:
        profile = await ProfileService(db).get_candidate_profile(user_id)
    except Exception:
        profile = None
    known: set[str] = set()
    gap_reason: dict[str, str] = {}
    if profile is not None and getattr(profile, "all_skills", None):
        known = {s.lower() for s in profile.all_skills}
        result = run_matching(profile, min_score=40, salary_min=0)
        for job in result.jobs[:5]:
            for skill in job.match.missing_skills:
                gap_reason.setdefault(
                    skill.lower(), f"{job.title} at {job.company}")

    plan: list[dict] = []
    tracks_out: list[dict] = []
    list_tracks()  # ensure the lazy registry is loaded
    for t in curriculum.TRACKS:
        lessons_out = []
        for lesson in t.lessons:
            skills = {s.lower() for s in lesson.practice_skills}
            gaps = sorted(skills & set(gap_reason))
            if gaps:
                status, reason = "required", f"Needed for {gap_reason[gaps[0]]}"
            elif skills and skills <= known:
                status, reason = "optional", "Already demonstrated on your resume"
            else:
                status, reason = "recommended", "Strengthens your core profile"
            entry = {"id": lesson.id, "title": lesson.title,
                     "track_id": t.id, "track": t.title,
                     "minutes": lesson.minutes, "status": status,
                     "reason": reason, "gap_skills": gaps}
            lessons_out.append(entry)
            if status == "required":
                plan.append(entry)
        tracks_out.append({"id": t.id, "title": t.title,
                           "emoji": t.emoji, "lessons": lessons_out})
    return {
        "has_profile": profile is not None and bool(known),
        "required": plan,
        "tracks": tracks_out,
    }
