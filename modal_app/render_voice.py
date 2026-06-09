"""One-off Kokoro TTS render for Lily's single spoken line in the ending (PLAN 7.3).

This is NOT a serving endpoint — the game never calls TTS at runtime. We render the
one fixed line once and commit the result as a static asset the Space serves, so the
climax has a real voice with zero cold-start risk:

    .venv/bin/modal run modal_app/kokoro.py            # -> app/static/audio/lily_final.wav
    .venv/bin/modal run modal_app/kokoro.py --voice af_sky   # try another voice

Kokoro-82M (hexgrad/Kokoro-82M, Apache-2.0) is small and runs fine on CPU.
"""
import modal

app = modal.App("forgotten-lily-kokoro")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("espeak-ng")
    .pip_install("kokoro>=0.9.2", "soundfile", "numpy", "torch")
)

# One sentence per line -> the pipeline yields a chunk per line and we insert a real
# breath between them, so it lands as a slow, reflective last thought rather than a
# read-aloud. Slow `speed` makes each phrase deliberate. (Kokoro is a neutral TTS, so
# the "emotion" comes from pacing + the pauses, not a happy/sad style knob.)
LINE = (
    "I just wanted to see the world.\n"
    "All three of us.\n"
    "Watching the sun come up."
)


@app.function(image=image, timeout=900)
def synth(text: str = LINE, voice: str = "af_bella", speed: float = 0.78, gap_s: float = 0.55) -> bytes:
    import io

    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline

    pipe = KPipeline(lang_code="a")  # American English
    parts = [np.zeros(int(0.25 * 24000), dtype=np.float32)]  # a breath before she speaks
    for line in [ln for ln in text.split("\n") if ln.strip()]:
        for _, _, audio in pipe(line, voice=voice, speed=speed):
            arr = audio.detach().cpu().numpy() if hasattr(audio, "detach") else np.asarray(audio)
            parts.append(arr.astype(np.float32))
        parts.append(np.zeros(int(gap_s * 24000), dtype=np.float32))  # reflective pause between phrases
    wav = np.concatenate(parts) if parts else np.zeros(1, dtype=np.float32)
    buf = io.BytesIO()
    sf.write(buf, wav, 24000, format="WAV", subtype="PCM_16")
    return buf.getvalue()


@app.local_entrypoint()
def main(voice: str = "af_bella", speed: float = 0.78, gap_s: float = 0.55):
    data = synth.remote(voice=voice, speed=speed, gap_s=gap_s)
    out = "app/static/audio/lily_final.wav"
    with open(out, "wb") as f:
        f.write(data)
    print(f"wrote {len(data)} bytes -> {out}  (voice={voice}, speed={speed}, gap={gap_s}s)")
