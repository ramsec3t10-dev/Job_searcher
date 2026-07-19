"""EMBEDHUNT AI — Curriculum engine.

Topic-by-topic teaching, the way a good tutor works: one track at a time
(C → data structures → OS → …), each track split into ordered lessons that
teach from basics to advanced with real code, and each lesson ending with
practice questions drawn ONLY from that lesson's topic — including the
company-asked set — so the day's questions always match the day's teaching.

Content lives in ``content_core.py`` / ``content_platform.py`` as plain data.
This module owns the dataclasses, the registry, and question resolution.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.interview.question_bank_extended import ALL_QUESTIONS


@dataclass(frozen=True)
class Section:
    heading: str
    body: str
    code: str = ""          # optional runnable example, C unless noted


@dataclass(frozen=True)
class Lesson:
    id: str
    title: str
    minutes: int                       # honest study estimate
    sections: tuple[Section, ...]
    takeaways: tuple[str, ...]
    practice_skills: tuple[str, ...]   # bank skills this lesson unlocks
    lab_challenge_id: str = ""         # optional coding-lab pairing

    def summary(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "minutes": self.minutes,
            "sections": len(self.sections),
            "has_lab": bool(self.lab_challenge_id),
        }


@dataclass(frozen=True)
class Track:
    id: str
    title: str
    emoji: str
    description: str
    lessons: tuple[Lesson, ...] = field(default_factory=tuple)

    def summary(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "emoji": self.emoji,
            "description": self.description,
            "lesson_count": len(self.lessons),
            "lessons": [l.summary() for l in self.lessons],
        }


def _practice_for(skills: tuple[str, ...], limit: int = 8) -> list[dict]:
    """Questions for exactly these skills — curated & company-asked first,
    templated coverage as filler. Keeps the day's practice on the day's topic."""
    ranked: list[tuple[int, dict]] = []
    for q in ALL_QUESTIONS:
        if q["skill"] not in skills:
            continue
        rank = 0 if q["category"] in ("curated", "company_asked") else 1
        ranked.append((rank, q))
    ranked.sort(key=lambda t: t[0])
    out = []
    for _, q in ranked[:limit]:
        item = dict(q)
        item["question"] = q["q"]
        out.append(item)
    return out


def lesson_payload(lesson: Lesson) -> dict:
    """Full lesson view: teaching content + matched practice questions."""
    return {
        "id": lesson.id,
        "title": lesson.title,
        "minutes": lesson.minutes,
        "sections": [
            {"heading": s.heading, "body": s.body, "code": s.code}
            for s in lesson.sections
        ],
        "takeaways": list(lesson.takeaways),
        "practice_skills": list(lesson.practice_skills),
        "practice_questions": _practice_for(lesson.practice_skills),
        "lab_challenge_id": lesson.lab_challenge_id,
    }


def _registry() -> tuple[Track, ...]:
    # Imported lazily so content modules can import the dataclasses above.
    from app.learning.content_core import CORE_TRACKS
    from app.learning.content_platform import PLATFORM_TRACKS
    return tuple([*CORE_TRACKS, *PLATFORM_TRACKS])


TRACKS: tuple[Track, ...] = ()
_LESSON_INDEX: dict[str, Lesson] = {}
_TRACK_INDEX: dict[str, Track] = {}


def _ensure_loaded() -> None:
    global TRACKS
    if TRACKS:
        return
    TRACKS = _registry()
    for t in TRACKS:
        _TRACK_INDEX[t.id] = t
        for l in t.lessons:
            _LESSON_INDEX[l.id] = l


def list_tracks() -> list[dict]:
    _ensure_loaded()
    return [t.summary() for t in TRACKS]


def get_track(track_id: str) -> Track | None:
    _ensure_loaded()
    return _TRACK_INDEX.get(track_id)


def get_lesson(lesson_id: str) -> Lesson | None:
    _ensure_loaded()
    return _LESSON_INDEX.get(lesson_id)
