"""Inference dispatcher. USE_MOCK=1 (default) routes to the rule-based mock so
the game runs with zero GPU cost; unset/0 will route to the Modal/Gemma function
once Phase 3 lands. Both expose `infer(request) -> response` per docs/CONTRACT.md.
"""
import os

if os.environ.get("USE_MOCK", "1") != "0":
    from app.mock_inference import infer  # noqa: F401
else:  # pragma: no cover - wired in Phase 3.4
    from app.modal_inference import infer  # noqa: F401
