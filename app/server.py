"""Forgotten Lily server. FastAPI app that serves the custom frontend and the
JSON game API. Inference is routed through app.inference (mock by default).

Run locally:
    USE_MOCK=1 .venv/bin/uvicorn app.server:app --reload --port 7860

On HuggingFace Spaces (Phase 9) a minimal gr.Blocks is mounted onto this app for
Gradio-SDK eligibility; the player only ever sees the custom frontend.
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import game
from app.game import active_tone_ids
from app.inference import infer

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"

app = FastAPI(title="Forgotten Lily")

# in-memory session store — fine for the slice / single-instance Space.
SESSIONS: dict[str, dict] = {}


def _get(session_id: str) -> dict:
    st = SESSIONS.get(session_id)
    if st is None:
        raise HTTPException(404, "session not found — start a new game")
    return st


class TurnIn(BaseModel):
    session_id: str
    message: str = ""
    special: str | None = None  # server-forced control (e.g. trigger finale)


class GuessIn(BaseModel):
    session_id: str
    tone_id: str
    guess: str


@app.post("/api/new")
def new_game():
    st = game.new_session()
    SESSIONS[st["session_id"]] = st
    return {"session_id": st["session_id"], "act": st["act"]}


@app.post("/api/turn")
def turn(body: TurnIn):
    st = _get(body.session_id)
    msg = (body.message or "")[:280]  # enforce 280-char cap server-side too
    if body.special:  # server-forced beat (finale); skip the model
        resp = {"tones": [], "topic_signal": None,
                "internal_emotion": "release", "special": body.special}
        if body.special == "finale":
            resp["tones"] = ["self_i", "act_fall", "self_remember", "other_you",
                             "emo_happy", "other_him", "truth_no", "truth_nothing"]
    else:
        resp = infer({
            "session_id": st["session_id"],
            "message": msg,
            "turn": st["turn"],
            "act": st["act"],
            "active_tones": active_tone_ids(st["act"]),
            "lexicon_state": {k: v["guess"] for k, v in st["lexicon"].items()},
        })
    return game.apply_turn(st, resp, msg)


@app.get("/api/state")
def state(session_id: str):
    st = _get(session_id)
    return {
        "act": st["act"], "turn": st["turn"],
        "tones_seen": len(st["tones_seen_count"]),
        "lexicon_size": game.lexicon_size(st),
        "notes_unlocked": st["notes_unlocked"],
    }


@app.get("/api/lexicon")
def lexicon(session_id: str):
    return game.lexicon_view(_get(session_id))


@app.get("/api/story")
def story(session_id: str):
    return game.story_view(_get(session_id))


@app.post("/api/guess")
def guess(body: GuessIn):
    st = _get(body.session_id)
    result = game.set_guess(st, body.tone_id, body.guess)
    if result is None:
        raise HTTPException(400, "unknown tone")
    return result


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
