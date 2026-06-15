"""Client wrapper for the deployed Modal Nemotron function (Phase 5.2).
Used by server.py when USE_MOCK=0. Requires `modal deploy modal_app/nemotron.py`.
"""
import modal

APP_NAME = "forgotten-lily-nemotron"  # distinct from Gemma's "forgotten-lily"
_nemotron = None


def _get():
    global _nemotron
    if _nemotron is None:
        _nemotron = modal.Cls.from_name(APP_NAME, "Nemotron")()
    return _nemotron


def warm():
    """Fire-and-forget: pre-boot a Nemotron container + load the model so the first
    guess/moderation call isn't cold. Non-blocking (spawn returns immediately)."""
    _get().warm.spawn()


def score_guess(tone_id: str, guess: str, contexts: list) -> str:
    """Call Nemotron to rate a lexicon guess. Returns 'red'|'amber'|'teal'|'green'."""
    print(f"\033[36m[nemotron →]\033[0m score tone={tone_id!r} guess={guess!r:.40} ctx={len(contexts)}")
    result = _get().score_guess.remote(tone_id, guess, contexts)
    print(f"\033[35m[nemotron ←]\033[0m {result}")
    return result


def moderate(message: str) -> str:
    """Classify a player message. Returns 'normal'|'off_topic'|'harmful'."""
    print(f"\033[36m[nemotron →]\033[0m moderate {message!r:.60}")
    result = _get().moderate.remote(message)
    print(f"\033[35m[nemotron ←]\033[0m {result}")
    return result
