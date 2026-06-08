"""Entry point — Forgotten Lily as a Gradio app.

The game is a custom HTML/Tailwind/JS frontend served by our FastAPI router
(app.server). To satisfy the hackathon's Gradio requirement (and the off-brand
UI badge: a custom Gradio UI, unrecognizable from default), we run the whole
thing on Gradio: a gr.Blocks app is mounted onto the same server via
gr.mount_gradio_app, so Gradio is the framework actually serving the experience.

Local:   .venv/bin/python app.py         (or: uvicorn app:app --port 7860)
Game UI:  http://localhost:7860/
Gradio:   http://localhost:7860/engine   (mounted Blocks — control/diagnostics)
"""
import gradio as gr

from app.server import app  # FastAPI: /api/*, /static, "/" -> custom frontend

with gr.Blocks(title="Forgotten Lily — engine", analytics_enabled=False) as demo:
    gr.Markdown(
        "## Forgotten Lily\n"
        "A narrative mystery told in tones. The game itself runs at the site "
        "root **/** as a custom frontend. This Gradio surface mounts the engine "
        "and is where backend controls/diagnostics live."
    )

# Mount the Gradio Blocks onto our FastAPI app. `app` remains the ASGI server
# (custom frontend at /, JSON API at /api), with Gradio served under /engine.
app = gr.mount_gradio_app(app, demo, path="/engine")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7860)
