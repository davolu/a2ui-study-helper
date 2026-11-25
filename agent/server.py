"""
A tiny web server: one endpoint for the chat, plus the built React app.

  POST /api/chat   {sessionId, message | action, capabilities, textOnly}
                -> {text, messages: [A2UI v1.0 messages], brain}
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from study_agent import get_session, has_gemini_key

app = FastAPI(title="Study Helper")


@app.get("/api/status")
def status():
    return {"mode": "gemini" if has_gemini_key() else "scripted (offline)"}


@app.post("/api/chat")
def chat(body: dict):
    session_id, session = get_session(body.get("sessionId"), body["capabilities"])
    try:
        reply = session.handle(body.get("message"), body.get("action"), bool(body.get("textOnly")))
    except Exception as error:  # show the problem in the app instead of a blank screen
        return JSONResponse({"sessionId": session_id, "error": str(error)}, status_code=500)
    return {"sessionId": session_id, **reply}


# Serve the React app (built into web/dist by `npm run build`).
dist = Path(__file__).resolve().parent.parent / "web" / "dist"
if dist.exists():
    app.mount("/", StaticFiles(directory=dist, html=True), name="web")
