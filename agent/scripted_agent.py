"""
The offline "scripted agent".

No AI model here. When there is no GEMINI_API_KEY, Study Helper uses these
hand-written replies so you can still see A2UI working.

Important: these are REAL A2UI v1.0 messages. They are written exactly the
way a model would write them (JSON inside <a2ui-json> tags), and they go
through the same official SDK parser and validator as a Gemini reply.
"""

import json

from a2ui.core.basic_catalog import BasicCatalog
from a2ui.core.schema import ProtocolVersion

BASIC = BasicCatalog(ProtocolVersion.V1_0).catalog_id


def a2ui_block(messages: list[dict]) -> str:
    """Wrap A2UI messages the way the model is told to: <a2ui-json>[...]</a2ui-json>."""
    return "<a2ui-json>\n" + json.dumps(messages, indent=2) + "\n</a2ui-json>"


# ---------------------------------------------------------------------------
# 1. "Make me a 3-question fractions quiz"  ->  a tappable quiz form
# ---------------------------------------------------------------------------

QUIZ_ANSWER_KEY = {"q1": "3/4", "q2": "2/3", "q3": "3/4"}


def quiz_reply(surface_id: str) -> str:
    def question(qid: str, label: str, options: list[str]) -> dict:
        return {
            "id": qid,
            "component": "ChoicePicker",
            "label": label,
            "variant": "mutuallyExclusive",  # pick exactly one
            "displayStyle": "chips",
            "options": [{"label": o, "value": o} for o in options],
            "value": {"@path": f"/answers/{qid}"},  # the tap is stored here
        }

    messages = [
        # Message 1: "Please make a new surface (a new piece of screen)."
        {"version": "1.0", "createSurface": {"surfaceId": surface_id, "catalogId": BASIC}},
        # Message 2: "Here are the pieces, and how they fit together."
        {
            "version": "1.0",
            "updateComponents": {
                "surfaceId": surface_id,
                "components": [
                    {"id": "root", "component": "Column",
                     "children": ["title", "intro", "q1", "q2", "q3", "check"]},
                    {"id": "title", "component": "Text", "text": "### Fractions quiz"},
                    {"id": "intro", "component": "Text", "variant": "caption",
                     "text": "Tap one answer for each question, then press Check my answers."},
                    question("q1", "1. What is 1/2 + 1/4?", ["2/6", "3/4", "1/8"]),
                    question("q2", "2. Which is bigger: 2/3 or 3/5?", ["2/3", "3/5", "They are equal"]),
                    question("q3", "3. What is 6/8 in its simplest form?", ["3/8", "2/3", "3/4"]),
                    {"id": "check", "component": "Button", "variant": "primary",
                     "child": "check_label",
                     "action": {"event": {
                         "name": "grade_quiz",
                         # When pressed, send the agent what the student picked.
                         "context": {
                             "q1": {"@path": "/answers/q1"},
                             "q2": {"@path": "/answers/q2"},
                             "q3": {"@path": "/answers/q3"},
                         },
                     }}},
                    {"id": "check_label", "component": "Text", "text": "Check my answers"},
                ],
            },
        },
        # Message 3: "Here is the starting data." (nothing picked yet)
        {
            "version": "1.0",
            "updateDataModel": {
                "surfaceId": surface_id,
                "value": {"answers": {"q1": [], "q2": [], "q3": []}},
            },
        },
    ]
    return "Here is a 3-question fractions quiz. Tap your answers.\n" + a2ui_block(messages)


def grade_reply(surface_id: str, context: dict) -> str:
    """The student pressed Check. Grade it, then update the SAME surface."""
    lines, score = [], 0
    explain = {
        "q1": "1/2 is 2/4, and 2/4 + 1/4 = 3/4.",
        "q2": "2/3 is 10/15 and 3/5 is 9/15, so 2/3 is bigger.",
        "q3": "Divide top and bottom by 2: 6/8 = 3/4.",
    }
    for n, qid in enumerate(["q1", "q2", "q3"], start=1):
        picked = (context.get(qid) or [None])[0]
        right = QUIZ_ANSWER_KEY[qid]
        if picked == right:
            score += 1
            lines.append(f"- **Q{n}: correct.** {explain[qid]}")
        else:
            lines.append(f"- **Q{n}: you picked {picked or 'nothing'}; the answer is {right}.** {explain[qid]}")

    messages = [
        # Add a result card under the quiz: re-send the root with one more child.
        {
            "version": "1.0",
            "updateComponents": {
                "surfaceId": surface_id,
                "components": [
                    {"id": "root", "component": "Column",
                     "children": ["title", "intro", "q1", "q2", "q3", "check", "result"]},
                    {"id": "result", "component": "Card", "child": "result_body"},
                    {"id": "result_body", "component": "Column",
                     "children": ["result_score", "result_details"]},
                    {"id": "result_score", "component": "Text", "text": {"@path": "/result/score"}},
                    {"id": "result_details", "component": "Text", "text": {"@path": "/result/details"}},
                ],
            },
        },
        # Put the grade into the data model. The Text components above show it.
        {
            "version": "1.0",
            "updateDataModel": {
                "surfaceId": surface_id,
                "path": "/result",
                "value": {"score": f"### You got {score} out of 3", "details": "\n".join(lines)},
            },
        },
    ]
    return f"Marked! {score} out of 3.\n" + a2ui_block(messages)


# ---------------------------------------------------------------------------
# 2. "List 5 topics to revise tonight"  ->  a checklist
# ---------------------------------------------------------------------------

def topics_reply(surface_id: str) -> str:
    topics = [
        ("Fractions: adding and simplifying", "Quick wins, and they show up in most maths tests."),
        ("Photosynthesis", "Learn the word equation and where it happens (the chloroplast)."),
        ("The water cycle", "Four steps: evaporation, condensation, precipitation, collection."),
        ("Parts of a plant cell", "Cell wall, membrane, nucleus, chloroplast, vacuole."),
        ("Writing a strong paragraph", "Point, evidence, explain."),
    ]
    messages = [
        {"version": "1.0", "createSurface": {"surfaceId": surface_id, "catalogId": BASIC}},
        {
            "version": "1.0",
            "updateComponents": {
                "surfaceId": surface_id,
                "components": [
                    {"id": "root", "component": "Column", "children": ["title", "hint", "topics"]},
                    {"id": "title", "component": "Text", "text": "### 5 topics to revise tonight"},
                    {"id": "hint", "component": "Text", "variant": "caption",
                     "text": "About 20 minutes each. Tick them off as you go."},
                    # A List that repeats one template for every item in /topics.
                    {"id": "topics", "component": "List",
                     "children": {"componentId": "topic", "path": "/topics"}},
                    {"id": "topic", "component": "Card", "child": "topic_body"},
                    {"id": "topic_body", "component": "Column", "children": ["topic_check", "topic_why"]},
                    # Paths without a leading "/" point inside the current item.
                    {"id": "topic_check", "component": "CheckBox",
                     "label": {"@path": "title"}, "value": {"@path": "done"}},
                    {"id": "topic_why", "component": "Text", "variant": "caption",
                     "text": {"@path": "why"}},
                ],
            },
        },
        {
            "version": "1.0",
            "updateDataModel": {
                "surfaceId": surface_id,
                "value": {"topics": [{"title": t, "why": w, "done": False} for t, w in topics]},
            },
        },
    ]
    return "Here is a plan for tonight.\n" + a2ui_block(messages)


# ---------------------------------------------------------------------------
# 3. "Summarise photosynthesis"  ->  a summary card
# ---------------------------------------------------------------------------

def summary_reply(surface_id: str) -> str:
    messages = [
        {"version": "1.0", "createSurface": {"surfaceId": surface_id, "catalogId": BASIC}},
        {
            "version": "1.0",
            "updateComponents": {
                "surfaceId": surface_id,
                "components": [
                    {"id": "root", "component": "Card", "child": "body"},
                    {"id": "body", "component": "Column",
                     "children": ["title", "overview", "line", "points_title", "points", "equation"]},
                    {"id": "title", "component": "Text", "text": {"@path": "/title"}},
                    {"id": "overview", "component": "Text", "text": {"@path": "/overview"}},
                    {"id": "line", "component": "Divider"},
                    {"id": "points_title", "component": "Text", "text": "**Key points**"},
                    {"id": "points", "component": "List",
                     "children": {"componentId": "point", "path": "/keyPoints"}},
                    {"id": "point", "component": "Text", "text": {"@path": "text"}},
                    {"id": "equation", "component": "Text", "variant": "caption",
                     "text": {"@path": "/equation"}},
                ],
            },
        },
        {
            "version": "1.0",
            "updateDataModel": {
                "surfaceId": surface_id,
                "value": {
                    "title": "### Photosynthesis in one minute",
                    "overview": "Plants, algae and some bacteria use light energy to turn "
                                "carbon dioxide and water into glucose (a sugar). Oxygen is "
                                "released as a by-product.",
                    "keyPoints": [
                        {"text": "🌿 It happens in **chloroplasts**, which contain the green pigment chlorophyll."},
                        {"text": "☀️ **Light-dependent stage:** light splits water, releasing oxygen and storing energy."},
                        {"text": "🔁 **Calvin cycle:** that stored energy is used to turn carbon dioxide into glucose."},
                        {"text": "🍎 The glucose feeds the plant and is the start of most food chains."},
                    ],
                    "equation": "6CO₂ + 6H₂O + light → C₆H₁₂O₆ + 6O₂",
                },
            },
        },
    ]
    return "Here is a short summary.\n" + a2ui_block(messages)


# ---------------------------------------------------------------------------
# The same three answers as plain chat text (for the "text vs UI" comparison)
# ---------------------------------------------------------------------------

TEXT_ONLY = {
    "quiz": (
        "Sure! Here is a 3-question fractions quiz.\n\n"
        "1. What is 1/2 + 1/4? a) 2/6 b) 3/4 c) 1/8\n"
        "2. Which is bigger: 2/3 or 3/5? a) 2/3 b) 3/5 c) They are equal\n"
        "3. What is 6/8 in its simplest form? a) 3/8 b) 2/3 c) 3/4\n\n"
        "Reply with your answers, for example \"1b, 2a, 3c\", and I will mark them."
    ),
    "topics": (
        "Here are 5 topics to revise tonight (about 20 minutes each): "
        "1) Fractions: adding and simplifying. 2) Photosynthesis: the word equation and "
        "the chloroplast. 3) The water cycle: evaporation, condensation, precipitation, "
        "collection. 4) Parts of a plant cell: cell wall, membrane, nucleus, chloroplast, "
        "vacuole. 5) Writing a strong paragraph: point, evidence, explain."
    ),
    "summary": (
        "Photosynthesis is how plants, algae and some bacteria use light energy to turn "
        "carbon dioxide and water into glucose, releasing oxygen. It happens in "
        "chloroplasts, which contain chlorophyll. In the light-dependent stage, light "
        "splits water, releasing oxygen and storing energy. In the Calvin cycle, that "
        "energy turns carbon dioxide into glucose. Equation: 6CO2 + 6H2O + light -> "
        "C6H12O6 + 6O2."
    ),
}


def help_reply(surface_id: str) -> str:
    messages = [
        {"version": "1.0", "createSurface": {
            "surfaceId": surface_id, "catalogId": BASIC,
            # v1.0 lets a surface arrive in ONE message, with its components inline.
            "components": [
                {"id": "root", "component": "Column", "children": ["t", "a", "b", "c"]},
                {"id": "t", "component": "Text", "text": "**Offline mode knows three requests. Try one:**"},
                {"id": "a", "component": "Text", "text": "- Make me a 3-question fractions quiz"},
                {"id": "b", "component": "Text", "text": "- List 5 topics to revise tonight"},
                {"id": "c", "component": "Text", "text": "- Summarise photosynthesis"},
            ],
        }},
    ]
    return "I'm running without a Gemini key, so I only know a few requests.\n" + a2ui_block(messages)


def pick(message: str) -> str:
    """Which canned answer fits this request?"""
    m = message.lower()
    if "quiz" in m:
        return "quiz"
    if "topic" in m or "revise" in m or "list" in m:
        return "topics"
    if "summar" in m or "photosynthesis" in m:
        return "summary"
    return "help"


def reply(message: str, surface_id: str, text_only: bool = False) -> str:
    kind = pick(message)
    if text_only:
        return TEXT_ONLY.get(kind, "Try: a fractions quiz, 5 topics to revise, or a photosynthesis summary.")
    return {"quiz": quiz_reply, "topics": topics_reply,
            "summary": summary_reply, "help": help_reply}[kind](surface_id)
