"""
The Study Helper agent.

It reads what the student asked and DECIDES what UI to answer with:
a quiz form, a checklist, a summary card... It writes that UI as A2UI v1.0
messages, and the official SDK checks them before they leave the server.

Two brains, same pipeline:
  * Gemini      - used when GEMINI_API_KEY is set.
  * Scripted    - offline, hand-written replies (see scripted_agent.py).
"""

import json
import os
import time
import uuid

from a2ui.core import A2uiError
from a2ui.core.basic_catalog import BasicCatalog
from a2ui.core.schema import ProtocolVersion
from a2ui.inference_formats import DirectJsonFormatFactory
from a2ui.parser.response_part import A2uiPart, TextPart
from a2ui.processor import A2uiGenerator, CatalogConfig

import scripted_agent

# 1. The catalog: the list of building blocks the agent is allowed to use.
#    We use A2UI v1.0's "basic catalog" (Text, Column, Card, Button, ...).
CATALOG = BasicCatalog(ProtocolVersion.V1_0)

# 2. The generator. "Direct JSON" means the model writes plain A2UI JSON
#    inside <a2ui-json> ... </a2ui-json> tags.
GENERATOR = A2uiGenerator(
    [CatalogConfig(CATALOG)],
    inference_format_factory=DirectJsonFormatFactory(),
)

ROLE = """You are Study Helper, a friendly tutor for school students.
For every request, YOU decide which interface fits the answer best, and you
build it from the catalog below. Do not answer with a wall of text.
Think about what the student will DO with the answer:
- If they will answer questions, build something they can tap. For a quiz, use
  one ChoicePicker per question (value bound to /answers/<qid>) and a primary
  Button whose action is the event "grade_quiz", with the answers in its context.
- If they will work through a set of items, build something they can tick off.
- If they will read and remember, build something easy to scan.
Keep it simple: one clear surface per answer.
Send each new surface as THREE messages, in this order: createSurface (surfaceId
and catalogId only), then updateComponents (the layout), then updateDataModel
(the words and values). Bind component text to the data model with "@path".
Always: one short sentence of normal text first, then one <a2ui-json> block.
Each new answer gets a NEW surface; use the surfaceId you are given.
When you receive a "grade_quiz" action, mark the answers carefully. The answers
arrive in the action's context as lists, e.g. {"q1": ["3/4"]}: compare each one
with the correct option, question by question. Then update the SAME
quiz surface: send updateComponents that re-sends "root" with one extra child,
a Card showing the score and a one-line explanation per question. Put the new
words in the data model with updateDataModel using a "path" (for example
"/results"), so the quiz text and the student's answers stay on screen.
Keep facts correct and simple."""

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
# If the main model is busy (HTTP 503/429), try these next.
FALLBACK_MODELS = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.7-flash"]


def has_gemini_key() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))


class StudySession:
    """One browser tab. Remembers the conversation and the surfaces on screen."""

    def __init__(self, renderer_capabilities: dict):
        # Ask the SDK for a processor that matches what this browser can draw.
        self.processor = GENERATOR.create_processor(renderer_capabilities)
        # The agent's copy of what is on screen, so every reply is checked
        # against it (e.g. "you can't update a surface you never created").
        self.state = self.processor.create_state()
        self.history: list[dict] = []
        self.surface_count = 0
        self.last_model = MODEL

    def new_surface_id(self) -> str:
        self.surface_count += 1
        return f"study-{self.surface_count}"

    # ---- one turn ---------------------------------------------------------

    def handle(self, message: str | None, action: dict | None, text_only: bool) -> dict:
        if action is not None:
            turn = "The student pressed a button. A2UI action message:\n" + json.dumps(
                {"version": "1.0", "action": action})
            surface_id = action["surfaceId"]
        else:
            turn = message or ""
            surface_id = self.new_surface_id()

        if has_gemini_key():
            raw = self._ask_gemini(turn, surface_id, text_only)
            brain = f"gemini ({self.last_model})"
        else:
            raw = self._ask_script(message, action, surface_id, text_only)
            brain = "scripted (offline)"

        if text_only:
            return {"brain": brain, "text": raw, "messages": []}

        # 3. The official SDK parses the reply and VALIDATES every message
        #    against the catalog and the current screen. Invalid UI never
        #    reaches the browser.
        try:
            parts = self.processor.parse_response(raw, state=self.state)
        except A2uiError as error:
            if not has_gemini_key():
                raise
            # Ask the model once more, quoting exactly what the SDK rejected.
            raw = self._ask_gemini(
                f"Your last reply was rejected by the A2UI validator: {error}. "
                "Send the whole reply again, fixed.", surface_id, text_only)
            parts = self.processor.parse_response(raw, state=self.state)
        text = " ".join(p.text.strip() for p in parts if isinstance(p, TextPart)).strip()
        messages = [
            m.model_dump(mode="json", by_alias=True, exclude_none=True)
            for p in parts if isinstance(p, A2uiPart) for m in p.a2ui
        ]
        return {"brain": brain, "text": text, "messages": messages}

    # ---- the two brains ---------------------------------------------------

    def _ask_script(self, message, action, surface_id, text_only) -> str:
        if action is not None:
            if action.get("name") == "grade_quiz":
                return scripted_agent.grade_reply(surface_id, action.get("context", {}))
            return "Thanks, got it."
        return scripted_agent.reply(message or "", surface_id, text_only)

    def _ask_gemini(self, turn: str, surface_id: str, text_only: bool) -> str:
        from google import genai
        from google.genai import types

        if text_only:
            system = "You are Study Helper, a friendly tutor. Answer in plain text only."
            prompt = turn
        else:
            system = ROLE + "\n\n" + self.processor.prompt_snippet
            prompt = f"{turn}\n\n(Use surfaceId \"{surface_id}\".)"

        self.history.append({"role": "user", "parts": [{"text": prompt}]})
        client = genai.Client()  # reads GEMINI_API_KEY from the environment
        result, last_error = None, None
        for model in [MODEL, *FALLBACK_MODELS]:
            for attempt in range(2):
                try:
                    result = client.models.generate_content(
                        model=model,
                        contents=self.history,
                        config=types.GenerateContentConfig(system_instruction=system),
                    )
                    self.last_model = model
                    break
                except genai.errors.APIError as error:
                    last_error = error
                    if error.code not in (429, 500, 503):
                        raise
                    time.sleep(2 * (attempt + 1))  # busy: wait a moment, then retry
            if result is not None:
                break
        if result is None:
            self.history.pop()
            raise last_error
        answer = result.text or ""
        self.history.append({"role": "model", "parts": [{"text": answer}]})
        return answer


SESSIONS: dict[str, StudySession] = {}


def get_session(session_id: str | None, capabilities: dict) -> tuple[str, StudySession]:
    if not session_id or session_id not in SESSIONS:
        session_id = session_id or uuid.uuid4().hex
        SESSIONS[session_id] = StudySession(capabilities)
    return session_id, SESSIONS[session_id]
