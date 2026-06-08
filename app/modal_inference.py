"""Client wrapper for the deployed Modal Gemma function. Selected by
app.inference when USE_MOCK=0. Honors the same `infer(request) -> response`
signature as the mock (docs/CONTRACT.md), so it drops straight into the server.

Requires `modal deploy modal_app/gemma.py` to have run (the app must be live).
"""
import modal

APP_NAME = "forgotten-lily"
_lily = None


def _get():
    global _lily
    if _lily is None:
        _lily = modal.Cls.from_name(APP_NAME, "Lily")()
    return _lily


def infer(request):
    return _get().infer.remote(request)
