from dataclasses import dataclass


@dataclass(frozen=True)
class PlacementQuestion:
    id: str
    prompt: str
    options: tuple[str, ...]
    answer: str
    level: str
    skill: str


PLACEMENT_TEST_VERSION = "2026-07-v1"


# This is a short diagnostic, not an official CEFR certification. Questions get
# progressively harder so the result is useful for choosing a starting point.
PLACEMENT_QUESTIONS: tuple[PlacementQuestion, ...] = (
    PlacementQuestion(
        "q1",
        "Choose the correct sentence.",
        ("She work in a bank.", "She works in a bank.", "She working in a bank.", "She is work in a bank."),
        "b",
        "A1",
        "grammar",
    ),
    PlacementQuestion(
        "q2",
        "What is the opposite of 'cheap'?",
        ("Small", "Easy", "Expensive", "Short"),
        "c",
        "A1",
        "vocabulary",
    ),
    PlacementQuestion(
        "q3",
        "Complete: I have lived here ___ 2022.",
        ("for", "since", "during", "from"),
        "b",
        "A2",
        "grammar",
    ),
    PlacementQuestion(
        "q4",
        "If it rains tomorrow, we ___ at home.",
        ("stay", "stayed", "will stay", "would stayed"),
        "c",
        "A2",
        "grammar",
    ),
    PlacementQuestion(
        "q5",
        "Which sentence is most natural?",
        (
            "I am interested to learn English.",
            "I am interested in learning English.",
            "I interested learning English.",
            "I am interest in learn English.",
        ),
        "b",
        "B1",
        "grammar",
    ),
    PlacementQuestion(
        "q6",
        "Complete: By the time we arrived, the film ___.",
        ("starts", "has started", "had started", "was start"),
        "c",
        "B1",
        "grammar",
    ),
    PlacementQuestion(
        "q7",
        "Choose the best connector: The evidence was limited; ___, the team reached a conclusion.",
        ("nevertheless", "because", "unless", "whereas"),
        "a",
        "B2",
        "vocabulary",
    ),
    PlacementQuestion(
        "q8",
        "Which option best completes: The proposal, ___ last week, needs more data.",
        ("discussing", "discussed", "was discussed", "having discuss"),
        "b",
        "B2",
        "grammar",
    ),
    PlacementQuestion(
        "q9",
        "Choose the most precise sentence.",
        (
            "The policy had a big effect on the results.",
            "The policy affected the results big.",
            "The policy exerted a substantial influence on the results.",
            "The policy was effecting the results substantiallyly.",
        ),
        "c",
        "C1",
        "vocabulary",
    ),
    PlacementQuestion(
        "q10",
        "Complete: Were the findings to be replicated, they ___ the current theory.",
        ("challenge", "challenged", "would challenge", "will challenged"),
        "c",
        "C1",
        "grammar",
    ),
    PlacementQuestion(
        "q11",
        "Complete: There ___ two books on the table.",
        ("is", "are", "be", "am"),
        "b",
        "A1",
        "grammar",
    ),
    PlacementQuestion(
        "q12",
        "Mai leaves home at seven and takes the number 8 bus to school. How does Mai travel to school?",
        ("By train", "By bicycle", "By bus", "On foot"),
        "c",
        "A1",
        "reading",
    ),
    PlacementQuestion(
        "q13",
        "What does 'borrow' mean?",
        (
            "To take something and return it later",
            "To give something away forever",
            "To buy something cheaply",
            "To repair something broken",
        ),
        "a",
        "A2",
        "vocabulary",
    ),
    PlacementQuestion(
        "q14",
        "The cafe is open from Monday to Saturday and closes on Sunday. When can you visit it?",
        ("Sunday morning", "Sunday evening", "Monday afternoon", "Only at weekends"),
        "c",
        "A2",
        "reading",
    ),
    PlacementQuestion(
        "q15",
        "If a source is 'reliable', it is ___.",
        ("difficult to find", "safe to depend on", "likely to change", "expensive to use"),
        "b",
        "B1",
        "vocabulary",
    ),
    PlacementQuestion(
        "q16",
        (
            "After the company introduced remote work, productivity stayed stable while employee "
            "satisfaction increased. What is the best conclusion?"
        ),
        (
            "Remote work reduced productivity.",
            "Employees worked fewer hours.",
            "Satisfaction improved without lowering productivity.",
            "The company hired more employees.",
        ),
        "c",
        "B1",
        "reading",
    ),
    PlacementQuestion(
        "q17",
        "Complete: Not until the data were reviewed ___ the researchers notice the error.",
        ("the researchers did", "did", "had", "the researchers had"),
        "b",
        "B2",
        "grammar",
    ),
    PlacementQuestion(
        "q18",
        (
            "Although initial sales were modest, demand rose sharply after the product was redesigned. "
            "What can be inferred?"
        ),
        (
            "The redesign likely made the product more appealing.",
            "The company stopped selling the product.",
            "Demand was highest before the redesign.",
            "The redesign reduced production costs.",
        ),
        "a",
        "B2",
        "reading",
    ),
    PlacementQuestion(
        "q19",
        "Choose the closest meaning of 'mitigate'.",
        ("Intensify", "Predict", "Reduce the severity of", "Completely eliminate"),
        "c",
        "C1",
        "vocabulary",
    ),
    PlacementQuestion(
        "q20",
        (
            "The report concedes that the intervention was costly, yet argues that its long-term social "
            "benefits outweigh the initial expense. Which statement best reflects the author's position?"
        ),
        (
            "The expense makes the intervention unjustifiable.",
            "The intervention has no measurable social benefit.",
            "Short-term cost should be considered alongside longer-term value.",
            "The report avoids making any judgment about the intervention.",
        ),
        "c",
        "C1",
        "reading",
    ),
)


def public_questions() -> list[dict]:
    return [
        {
            "id": item.id,
            "prompt": item.prompt,
            "options": list(item.options),
            "skill": item.skill,
        }
        for item in PLACEMENT_QUESTIONS
    ]


def score_answers(answers: dict[str, str]) -> tuple[int, str, dict[str, dict[str, int | float]]]:
    score = sum(answers.get(item.id, "").lower() == item.answer for item in PLACEMENT_QUESTIONS)
    if score <= 4:
        level = "A1"
    elif score <= 8:
        level = "A2"
    elif score <= 12:
        level = "B1"
    elif score <= 16:
        level = "B2"
    else:
        level = "C1"
    skill_scores: dict[str, dict[str, int | float]] = {}
    for skill in ("grammar", "vocabulary", "reading"):
        questions = [item for item in PLACEMENT_QUESTIONS if item.skill == skill]
        correct = sum(answers.get(item.id, "").lower() == item.answer for item in questions)
        skill_scores[skill] = {
            "correct": correct,
            "total": len(questions),
            "percentage": round(correct * 100 / len(questions), 2),
        }
    return score, level, skill_scores
