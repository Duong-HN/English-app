"""Seed the fixed curriculum from versioned content packs.

The A2→B1 course is intentionally stored as JSON so lesson authors can edit
learning content without changing the catalog/seeding code. The small legacy
catalog remains available for the other levels until those tracks receive the
same content treatment.
"""

import json
from collections.abc import Iterable
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .models import Course, CourseUnit, Lesson, utc_now

FOCUSED_COURSE_CODE = "core-b1"
CONTENT_PACK_PATH = Path(__file__).with_name("content") / "english_a2_b1.json"

LEVEL_THEMES = {
    "A1": ("Everyday foundations", "introductions, routines and simple needs"),
    "A2": ("Everyday independence", "past events, plans and practical conversations"),
    "B1": ("Confident communication", "opinions, experiences and connected speech"),
    "B2": ("Clear professional English", "nuance, argument and natural interaction"),
    "C1": ("Advanced expression", "precision, synthesis and complex viewpoints"),
}


def recommended_course_code(level: str | None, goal: str | None = None) -> str | None:
    if goal == "ielts":
        return "ielts-band-5-6"
    normalized = (level or "B1").upper()
    if normalized in {"A2", "B1"}:
        return FOCUSED_COURSE_CODE
    return f"core-{normalized.lower()}" if normalized in LEVEL_THEMES else FOCUSED_COURSE_CODE


def _load_focused_course() -> dict:
    try:
        payload = json.loads(CONTENT_PACK_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Unable to load curriculum content pack: {CONTENT_PACK_PATH}") from exc

    course = payload.get("course")
    if not isinstance(course, dict):
        raise RuntimeError("Curriculum content pack must contain a course object")
    lessons = course.get("lessons")
    units = course.get("units")
    if not isinstance(lessons, list) or not isinstance(units, list):
        raise RuntimeError("Curriculum content pack must contain lessons and units")

    lessons_by_key = {item.get("key"): item for item in lessons if isinstance(item, dict)}
    normalized_units: list[dict] = []
    for unit in units:
        if not isinstance(unit, dict):
            raise RuntimeError("Curriculum unit must be an object")
        lesson_keys = unit.get("lesson_keys", [])
        unit_lessons = [lessons_by_key[key] for key in lesson_keys if key in lessons_by_key]
        if len(unit_lessons) != len(lesson_keys):
            raise RuntimeError(f"Curriculum unit contains an unknown lesson key: {unit.get('title', '')}")
        normalized_units.append(
            {
                "unit_number": int(unit["unit_number"]),
                "title": unit["title"],
                "objective": unit["objective"],
                "lessons": unit_lessons,
            }
        )

    return {
        "code": course["code"],
        "title": course["title"],
        "description": course["description"],
        "kind": course.get("kind", "core"),
        "level": course.get("level"),
        "band_min": course.get("band_min"),
        "band_max": course.get("band_max"),
        "units": normalized_units,
    }


def _legacy_core_lessons(level: str, theme: str, focus: str) -> list[dict[str, str]]:
    """Keep the other levels available while the focused pack is developed."""
    return [
        {
            "title": f"Vocabulary: {theme}",
            "skill": "vocabulary",
            "content_type": "vocabulary",
            "summary": f"Learn useful words and phrases about {focus}.",
            "body": (
                f"Write down eight new words about {focus}. Add a Vietnamese meaning, "
                "an example sentence and a short pronunciation practice for each word."
            ),
        },
        {
            "title": f"Grammar in context: {theme}",
            "skill": "grammar",
            "content_type": "grammar",
            "summary": "Put one grammar point into a practical communication situation.",
            "body": (
                f"Read examples about {focus}, underline the main structure and write five new sentences. "
                "Check the subject, tense and word order before finishing."
            ),
        },
        {
            "title": f"Reading: {theme}",
            "skill": "reading",
            "content_type": "reading",
            "summary": "Find the main idea, supporting details and useful words in a short text.",
            "body": (
                f"Reading text ({level}): {theme} is connected to {focus}. Identify the main idea and "
                "two supporting details, then write a two-sentence summary."
            ),
        },
        {
            "title": f"Listening and retelling: {theme}",
            "skill": "listening",
            "content_type": "audio",
            "summary": "Listen for the general idea and retell a short script.",
            "body": (
                f"Listen to a short script about {focus}. First listen for the general idea, then listen "
                "again for three details. Finally, retell it in 45–60 seconds."
            ),
            "transcript": (
                f"Today we are talking about {focus}. Notice the key words, connect the ideas and explain "
                "one example in your own words."
            ),
        },
        {
            "title": f"Video in context: {theme}",
            "skill": "listening",
            "content_type": "video",
            "summary": "Watch a short context video and identify natural expressions.",
            "body": (
                f"Watch a short lesson about {focus}. Pause after each idea, write three key expressions "
                "and explain what happened in your own words."
            ),
            "transcript": (
                f"This short video introduces {focus}. Listen for the situation, the speaker's intention "
                "and one useful expression."
            ),
        },
        {
            "title": f"Speaking after learning: {theme}",
            "skill": "speaking",
            "content_type": "speaking",
            "summary": "Use new language to retell the main idea in 45–60 seconds.",
            "body": (
                f"Retell the lesson about {focus} in 45–60 seconds. Include the main idea, one detail "
                "and one personal example."
            ),
        },
    ]


def _legacy_ielts_lessons() -> list[dict[str, str]]:
    return [
        {
            "title": "Reading: skimming and scanning",
            "skill": "reading",
            "content_type": "reading",
            "summary": "Find the main idea, names, numbers and keywords quickly.",
            "body": (
                "Read the title and the first sentence of each paragraph in 60 seconds. Predict the main "
                "idea, then return to the text for evidence."
            ),
        },
        {
            "title": "Listening: keywords and paraphrase",
            "skill": "listening",
            "content_type": "audio",
            "summary": "Recognise paraphrases when information is presented in an audio passage.",
            "body": (
                "Read the questions first, circle keywords, predict the answer type and write synonyms "
                "while listening."
            ),
            "transcript": (
                "The speaker changes the wording, but the meaning stays the same. Listen for the idea, "
                "not only the exact word."
            ),
        },
        {
            "title": "Writing Task 2: clear argument",
            "skill": "writing",
            "content_type": "writing",
            "summary": "Build a thesis, topic sentence and specific example for an argument.",
            "body": (
                "Write a one-sentence thesis, plan two body paragraphs and add one specific example to "
                "each point. Then write 180–220 words."
            ),
        },
        {
            "title": "Speaking: structured answers",
            "skill": "speaking",
            "content_type": "speaking",
            "summary": "Extend an answer with a main point, a reason and an example.",
            "body": (
                "Speak for 60–90 seconds using answer–reason–example. Record yourself, listen again and "
                "mark pauses."
            ),
        },
    ]


def _legacy_course_definitions() -> Iterable[dict]:
    for level, (theme, focus) in LEVEL_THEMES.items():
        if level == "B1":
            continue
        lessons = _legacy_core_lessons(level, theme, focus)
        yield {
            "code": f"core-{level.lower()}",
            "title": f"English Core {level} · {theme}",
            "description": f"Fixed curriculum for {level}, focused on {focus}.",
            "kind": "core",
            "level": level,
            "band_min": None,
            "band_max": None,
            "units": [
                {
                    "unit_number": 1,
                    "title": f"Chapter 1 · {theme}",
                    "objective": (
                        f"Build a foundation in {focus} through vocabulary, grammar, reading and listening."
                    ),
                    "lessons": lessons[:3],
                },
                {
                    "unit_number": 2,
                    "title": "Chapter 2 · Use it in context",
                    "objective": "Turn knowledge into short spoken and written responses.",
                    "lessons": lessons[3:],
                },
            ],
        }
    for code, title, band_min, band_max in (
        ("ielts-band-4-5", "IELTS Foundation · Band 4.5–5.5", 4.5, 5.5),
        ("ielts-band-5-6", "IELTS Foundation · Band 5.0–6.0", 5.0, 6.0),
        ("ielts-band-6-7", "IELTS Progress · Band 6.0–7.0", 6.0, 7.0),
        ("ielts-band-7-8", "IELTS Advanced · Band 7.0–8.0", 7.0, 8.0),
    ):
        lessons = _legacy_ielts_lessons()
        yield {
            "code": code,
            "title": title,
            "description": f"IELTS band track {band_min:.1f}–{band_max:.1f} with four-skill practice.",
            "kind": "ielts",
            "level": None,
            "band_min": band_min,
            "band_max": band_max,
            "units": [
                {
                    "unit_number": 1,
                    "title": "Chapter 1 · Reading & Listening",
                    "objective": "Read quickly, listen for keywords and recognise paraphrase.",
                    "lessons": lessons[:2],
                },
                {
                    "unit_number": 2,
                    "title": "Chapter 2 · Writing & Speaking",
                    "objective": "Build an argument and extend a spoken answer.",
                    "lessons": lessons[2:],
                },
            ],
        }


def _course_definitions() -> Iterable[dict]:
    yield _load_focused_course()
    yield from _legacy_course_definitions()


def _apply_lesson_definition(lesson: Lesson, definition: dict, lesson_number: int) -> None:
    lesson.lesson_number = lesson_number
    lesson.title = definition["title"]
    lesson.skill = definition["skill"]
    lesson.content_type = definition["content_type"]
    lesson.summary = definition["summary"]
    lesson.body = definition["body"]
    lesson.transcript = definition.get("transcript")
    lesson.content_pack = definition.get("content_pack") or {}
    lesson.source_attribution = definition.get("source_attribution")
    lesson.license_name = definition.get("license_name")
    lesson.duration_minutes = definition.get("duration_minutes", 15)


def _new_course(definition: dict) -> Course:
    course = Course(
        code=definition["code"],
        title=definition["title"],
        description=definition["description"],
        kind=definition["kind"],
        level=definition["level"],
        band_min=definition["band_min"],
        band_max=definition["band_max"],
        created_at=utc_now(),
    )
    for unit_definition in definition["units"]:
        unit = CourseUnit(
            unit_number=unit_definition["unit_number"],
            title=unit_definition["title"],
            objective=unit_definition["objective"],
        )
        for lesson_number, lesson_definition in enumerate(unit_definition["lessons"], start=1):
            lesson = Lesson(
                lesson_number=lesson_number,
                title=lesson_definition["title"],
                skill=lesson_definition["skill"],
                content_type=lesson_definition["content_type"],
                summary=lesson_definition["summary"],
                body=lesson_definition["body"],
                transcript=lesson_definition.get("transcript"),
                content_pack=lesson_definition.get("content_pack") or {},
                source_attribution=lesson_definition.get("source_attribution"),
                license_name=lesson_definition.get("license_name"),
                duration_minutes=lesson_definition.get("duration_minutes", 15),
            )
            unit.lessons.append(lesson)
        course.units.append(unit)
    return course


def _refresh_focused_course(course: Course, definition: dict) -> bool:
    """Upgrade an older generic B1 seed without changing lesson IDs/progress."""
    changed = (
        course.title != definition["title"]
        or course.description != definition["description"]
        or course.level != definition["level"]
    )
    course.title = definition["title"]
    course.description = definition["description"]
    course.kind = definition["kind"]
    course.level = definition["level"]
    course.band_min = definition["band_min"]
    course.band_max = definition["band_max"]

    ordered_units = sorted(course.units, key=lambda item: item.unit_number)
    for unit_index, unit_definition in enumerate(definition["units"]):
        if unit_index >= len(ordered_units):
            return changed
        unit = ordered_units[unit_index]
        changed = (
            changed
            or unit.title != unit_definition["title"]
            or unit.objective != unit_definition["objective"]
        )
        unit.unit_number = unit_definition["unit_number"]
        unit.title = unit_definition["title"]
        unit.objective = unit_definition["objective"]
        ordered_lessons = sorted(unit.lessons, key=lambda item: item.lesson_number)
        for lesson_index, lesson_definition in enumerate(unit_definition["lessons"]):
            if lesson_index >= len(ordered_lessons):
                return changed
            lesson = ordered_lessons[lesson_index]
            before = (lesson.title, lesson.body, lesson.content_pack, lesson.source_attribution)
            _apply_lesson_definition(lesson, lesson_definition, lesson_index + 1)
            changed = changed or before != (
                lesson.title,
                lesson.body,
                lesson.content_pack,
                lesson.source_attribution,
            )
    return changed


def ensure_catalog(db: Session) -> None:
    courses = db.scalars(
        select(Course).options(selectinload(Course.units).selectinload(CourseUnit.lessons))
    ).all()
    existing = {course.code: course for course in courses}
    changed = False
    for definition in _course_definitions():
        course = existing.get(definition["code"])
        if course is not None:
            if definition["code"] == FOCUSED_COURSE_CODE:
                changed = _refresh_focused_course(course, definition) or changed
            continue
        course = _new_course(definition)
        db.add(course)
        existing[definition["code"]] = course
        changed = True
    if changed:
        db.commit()
