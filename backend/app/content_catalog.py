from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Course, CourseUnit, Lesson, utc_now

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
    return f"core-{normalized.lower()}" if normalized in LEVEL_THEMES else "core-b1"


def _core_lessons(level: str, theme: str, focus: str) -> list[dict[str, str]]:
    return [
        {
            "title": f"Từ vựng: {theme}",
            "skill": "vocabulary",
            "content_type": "vocabulary",
            "summary": f"Từ và cụm từ nền tảng về {focus}.",
            "body": (
                f"Ghi lại 8 từ mới về {focus}. Với mỗi từ, viết nghĩa tiếng Việt, "
                "một câu ví dụ và đọc câu đó thành tiếng."
            ),
        },
        {
            "title": f"Ngữ pháp trong ngữ cảnh: {theme}",
            "skill": "grammar",
            "content_type": "grammar",
            "summary": "Một điểm ngữ pháp được đặt trong tình huống giao tiếp thực tế.",
            "body": (
                f"Đọc ví dụ về {focus}, gạch chân cấu trúc chính, sau đó tự viết 5 câu mới. "
                "Kiểm tra chủ ngữ, thì và trật tự từ trước khi hoàn thành."
            ),
        },
        {
            "title": f"Đọc hiểu: {theme}",
            "skill": "reading",
            "content_type": "reading",
            "summary": "Đọc một đoạn ngắn, tìm ý chính và bằng chứng trong bài.",
            "body": (
                f"Reading text ({level}): {theme} is connected to {focus}. "
                "Good learners notice the main idea, supporting details and useful words. "
                "Write a two-sentence summary and answer: What is the writer's main point?"
            ),
        },
        {
            "title": f"Nghe và nói: {theme}",
            "skill": "listening",
            "content_type": "audio",
            "summary": "Nghe theo transcript, ghi từ khóa rồi nói lại nội dung.",
            "body": (
                f"Listen to the short script about {focus}. First listen for the general idea, "
                "then listen again for three details. Finally, retell it in 45–60 seconds."
            ),
            "transcript": (
                f"Today we are talking about {focus}. Notice the key words, connect the ideas, "
                "and explain one example in your own words."
            ),
        },
        {
            "title": f"Video theo ngữ cảnh: {theme}",
            "skill": "listening",
            "content_type": "video",
            "summary": "Xem một đoạn video ngắn, ghi lại ý chính và ngôn ngữ giao tiếp tự nhiên.",
            "body": (
                f"Watch the short lesson about {focus}. Pause after each idea, write three key expressions, "
                "then explain what happened in your own words."
            ),
            "transcript": (
                f"This short video introduces {focus}. Listen for the situation, the speaker's intention, "
                "and one useful expression."
            ),
        },
        {
            "title": f"Nói lại sau khi học: {theme}",
            "skill": "speaking",
            "content_type": "speaking",
            "summary": "Dùng từ mới để nói lại ý chính trong 45–60 giây.",
            "body": (
                f"Retell the lesson about {focus} in 45–60 seconds. Include the main idea, one detail "
                "and one personal example."
            ),
        },
    ]


def _ielts_lessons() -> list[dict[str, str]]:
    return [
        {
            "title": "Reading: skimming và scanning",
            "skill": "reading",
            "content_type": "reading",
            "summary": "Đọc nhanh để tìm ý chính, tên riêng, số liệu và từ khóa.",
            "body": (
                "Đọc tiêu đề và câu đầu mỗi đoạn trong 60 giây. Dự đoán ý chính, "
                "sau đó quay lại tìm bằng chứng cho từng câu hỏi."
            ),
        },
        {
            "title": "Listening: nghe từ khóa và paraphrase",
            "skill": "listening",
            "content_type": "audio",
            "summary": "Nhận ra cách đề bài diễn đạt lại thông tin trong audio.",
            "body": (
                "Đọc câu hỏi trước, khoanh từ khóa, dự đoán loại đáp án và ghi lại từ đồng nghĩa khi nghe."
            ),
            "transcript": (
                "The speaker changes the wording, but the meaning stays the same. "
                "Listen for the idea, not only the exact word."
            ),
        },
        {
            "title": "Writing Task 2: lập luận rõ ràng",
            "skill": "writing",
            "content_type": "writing",
            "summary": "Xây thesis, topic sentence và ví dụ cho bài luận.",
            "body": (
                "Viết thesis một câu, lập dàn ý hai đoạn thân bài và thêm một ví dụ "
                "cụ thể cho mỗi luận điểm. Sau đó viết 180–220 từ."
            ),
        },
        {
            "title": "Speaking: trả lời theo cấu trúc",
            "skill": "speaking",
            "content_type": "speaking",
            "summary": "Mở rộng câu trả lời bằng ý chính, lý do và ví dụ.",
            "body": (
                "Nói 60–90 giây theo công thức answer–reason–example. Ghi âm, nghe lại "
                "và tự đánh dấu chỗ ngập ngừng."
            ),
        },
    ]


def _course_definitions() -> Iterable[dict]:
    for level, (theme, focus) in LEVEL_THEMES.items():
        yield {
            "code": f"core-{level.lower()}",
            "title": f"English Core {level} · {theme}",
            "description": f"Giáo trình cố định theo level {level}, tập trung vào {focus}.",
            "kind": "core",
            "level": level,
            "band_min": None,
            "band_max": None,
            "units": [
                {
                    "title": f"Chapter 1 · {theme}",
                    "objective": f"Xây nền tảng {focus} bằng từ vựng, ngữ pháp, đọc và nghe.",
                },
                {
                    "title": "Chapter 2 · Use it in context",
                    "objective": "Chuyển kiến thức thành câu trả lời nói và bài viết ngắn.",
                },
            ],
            "lessons": _core_lessons(level, theme, focus),
        }
    for code, title, band_min, band_max in (
        ("ielts-band-4-5", "IELTS Foundation · Band 4.5–5.5", 4.5, 5.5),
        ("ielts-band-5-6", "IELTS Foundation · Band 5.0–6.0", 5.0, 6.0),
        ("ielts-band-6-7", "IELTS Progress · Band 6.0–7.0", 6.0, 7.0),
        ("ielts-band-7-8", "IELTS Advanced · Band 7.0–8.0", 7.0, 8.0),
    ):
        yield {
            "code": code,
            "title": title,
            "description": (
                f"Khóa IELTS theo band mục tiêu {band_min:.1f}–{band_max:.1f} với chiến lược "
                "và bài luyện bốn kỹ năng."
            ),
            "kind": "ielts",
            "level": None,
            "band_min": band_min,
            "band_max": band_max,
            "units": [
                {
                    "title": "Chapter 1 · Reading & Listening",
                    "objective": "Đọc nhanh, nghe từ khóa và nhận ra paraphrase.",
                },
                {
                    "title": "Chapter 2 · Writing & Speaking",
                    "objective": "Xây lập luận và trả lời nói có mở rộng ý.",
                },
            ],
            "lessons": _ielts_lessons(),
        }


def ensure_catalog(db: Session) -> None:
    existing = set(db.scalars(select(Course.code)).all())
    changed = False
    for definition in _course_definitions():
        if definition["code"] in existing:
            continue
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
        lessons = definition["lessons"]
        unit_count = len(definition["units"])
        for unit_index, unit_definition in enumerate(definition["units"]):
            start = unit_index * len(lessons) // unit_count
            end = (unit_index + 1) * len(lessons) // unit_count
            unit = CourseUnit(
                unit_number=unit_index + 1,
                title=unit_definition["title"],
                objective=unit_definition["objective"],
            )
            lesson_number = 1
            for lesson_definition in lessons[start:end]:
                lesson = Lesson(
                    lesson_number=lesson_number,
                    title=lesson_definition["title"],
                    skill=lesson_definition["skill"],
                    content_type=lesson_definition["content_type"],
                    summary=lesson_definition["summary"],
                    body=lesson_definition["body"],
                    transcript=lesson_definition.get("transcript"),
                    duration_minutes=15,
                )
                unit.lessons.append(lesson)
                lesson_number += 1
            course.units.append(unit)
        db.add(course)
        existing.add(definition["code"])
        changed = True
    if changed:
        db.commit()
