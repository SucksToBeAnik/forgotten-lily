"""Forgotten Lily server. FastAPI app that serves the custom frontend and the
JSON game API. Inference is routed through app.inference (mock by default).

Run locally:
    USE_MOCK=1 .venv/bin/uvicorn app.server:app --reload --port 7860

On HuggingFace Spaces (Phase 9) a minimal gr.Blocks is mounted onto this app for
Gradio-SDK eligibility; the player only ever sees the custom frontend.
"""
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import game
from app.game import active_tone_ids
from app.inference import infer

USE_MOCK = os.environ.get("USE_MOCK", "1") != "0"

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


# Diegetic response for harmful input (PLAN 8.2/8.3). Mirrors the mock's choice in
# app/mock_inference.py so live and offline play behave identically: harmful -> she
# withdraws (∅ + "silent"). There is deliberately NO off-topic gate — the game is
# about asking Lily about her life, so a one-line classifier flagged core questions
# ("are you a musician?") as off-topic and swallowed them into a lone pause. Genuine
# tangents are now handled in-character by the model instead of a canned deflection.
_MODERATED = {
    "harmful": {"tones": ["truth_nothing"], "topic_signal": None,
                "internal_emotion": "absent", "special": "silent"},
}


def _moderate(message: str) -> str:
    """Classify player input via Nemotron (live only — the mock moderates inside
    its own infer()). Returns 'normal' on any failure so a moderation hiccup never
    breaks a turn or the fiction."""
    try:
        from app.nemotron_inference import moderate
        return moderate(message)
    except Exception as exc:  # pragma: no cover - resilience guard
        print(f"\033[33m[moderate] failed, treating as normal:\033[0m {exc}")
        return "normal"


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
            # her last utterance, hand-authored (played in order, uncapped): "I wanted
            # to reach the world — and us, together — love — let go — the end."
            resp["tones"] = ["self_i", "act_want", "link_to", "other_world",
                             "link_and", "other_us", "emo_love", "act_fall",
                             "truth_nothing"]
    else:
        # Live moderation gate (Phase 6): classify input BEFORE spending a Gemma
        # call. Harmful/off-topic short-circuit to a diegetic response. The mock
        # path already moderates inside its own infer(), so only gate when live.
        verdict = _moderate(msg) if (not USE_MOCK and msg.strip()) else "normal"
        if verdict in _MODERATED:
            resp = dict(_MODERATED[verdict])
        else:
            resp = infer({
                "session_id": st["session_id"],
                "message": msg,
                "turn": st["turn"],
                "act": st["act"],
                "mood": st.get("mood", "warm"),  # carried emotional state, colors the reply
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


@app.get("/api/artifacts")
def artifacts(session_id: str):
    return game.artifacts_view(_get(session_id))


@app.post("/api/guess")
def guess(body: GuessIn):
    st = _get(body.session_id)
    result = game.set_guess(st, body.tone_id, body.guess)
    if result is None:
        raise HTTPException(400, "unknown tone")
    if not USE_MOCK:
        from app.nemotron_inference import score_guess as nemotron_score
        contexts = st.get("tone_contexts", {}).get(body.tone_id, [])
        conf = nemotron_score(body.tone_id, body.guess, contexts)
        result["confidence"] = conf
        st["lexicon"][body.tone_id]["confidence"] = conf
    return result


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
