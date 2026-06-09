"""Anonymous gameplay trace logging (PLAN 10.7 / Sharing-is-Caring).

Appends one row per turn to a Hugging Face **dataset** repo: the player's question,
the tones Lily answered with (ids + glyphs), their gloss, the topic signal, and the
moderation verdict. Rows are buffered to a local JSONL and pushed in batches by a
`CommitScheduler` so we never block a turn on a network commit, and never hammer the
Hub. Everything here is best-effort: any failure is swallowed so logging can never
break a turn or the fiction.

Privacy: a session id is a random UUID generated server-side (no account, no PII).
The player's question text IS stored — it's the point of the dataset (question →
tonal reply → gloss) — so the Space surfaces a visible "anonymous gameplay is
logged" note and the dataset card carries the same disclaimer.

Enable by setting two env vars on the Space:
    TRACE_DATASET_REPO   e.g. "your-namespace/forgotten-lily-traces"
    HF_TOKEN             a write token (already a Space secret for live mode)
If either is missing, logging is a silent no-op (local/mock dev stays clean).
"""
import hashlib
import json
import os
import threading
import time
from pathlib import Path

_REPO = os.environ.get("TRACE_DATASET_REPO", "").strip()
_TOKEN = os.environ.get("HF_TOKEN", "").strip()
_ENABLED = bool(_REPO and _TOKEN)

_LOCAL_DIR = Path(os.environ.get("TRACE_LOCAL_DIR", "/tmp/forgotten-lily-traces"))
_DATA_FILE = _LOCAL_DIR / "data" / "turns.jsonl"

_scheduler = None
_init_lock = threading.Lock()
_init_failed = False


def _gloss(tones):
    """First synonym of each tone's meaning, joined — 'I · feel · music'."""
    return " · ".join((t.get("meaning", "") or "").split(" / ")[0] for t in tones)


def _get_scheduler():
    """Lazily create the CommitScheduler (and the dataset repo) on first use."""
    global _scheduler, _init_failed
    if _scheduler is not None or _init_failed:
        return _scheduler
    with _init_lock:
        if _scheduler is not None or _init_failed:
            return _scheduler
        try:
            from huggingface_hub import CommitScheduler

            _DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
            _scheduler = CommitScheduler(
                repo_id=_REPO,
                repo_type="dataset",
                folder_path=str(_LOCAL_DIR),
                path_in_repo=".",
                every=2,  # minutes between batched pushes
                token=_TOKEN,
                squash_history=True,  # keep the dataset repo history small
                private=True,  # created private; flip to public when ready to share
            )
            print(f"\033[36m[trace] logging gameplay -> dataset {_REPO}\033[0m")
        except Exception as exc:  # pragma: no cover - resilience guard
            print(f"\033[33m[trace] disabled (scheduler init failed):\033[0m {exc}")
            _init_failed = True
    return _scheduler


def log_turn(session_id, result, question, moderation):
    """Append one turn's row. `result` is game.apply_turn's payload (has `tones`,
    `topic_signal`, `act`, `turn`). Never raises."""
    if not _ENABLED:
        return
    try:
        sched = _get_scheduler()
        if sched is None:
            return
        tones = result.get("tones", [])
        row = {
            "ts": int(time.time()),
            "session": hashlib.sha1(str(session_id).encode()).hexdigest()[:12],
            "turn": result.get("turn"),
            "act": result.get("act"),
            "question": (question or "")[:280],
            "tone_ids": [t.get("id") for t in tones],
            "glyphs": " ".join(t.get("glyph", "") for t in tones),
            "gloss": _gloss(tones),
            "topic_signal": result.get("topic_signal"),
            "moderation": moderation,
            "special": result.get("special"),
        }
        with sched.lock:  # serialize appends; the scheduler reads this file to push
            with open(_DATA_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception as exc:  # pragma: no cover - never break a turn
        print(f"\033[33m[trace] log_turn skipped:\033[0m {exc}")
