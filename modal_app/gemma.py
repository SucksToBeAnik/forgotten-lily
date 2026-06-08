"""Modal GPU inference — Lily's reasoning model (Phase 3).

Runs Gemma 4 E4B (GGUF Q4_K_M) via llama-cpp-python on a T4, behind the contract
in docs/CONTRACT.md. The model speaks AS Lily: given the detective's line and the
tones active this act, it returns a short JSON object choosing 1-7 tone ids, an
optional topic_signal, and an internal_emotion tag.

Deploy:   .venv/bin/modal deploy modal_app/gemma.py
Smoke:    .venv/bin/modal run modal_app/gemma.py
Weights download to a persistent Volume on first container start (then cached).
"""
import json
import os

import modal

APP_NAME = "forgotten-lily"
MODEL_REPO = "ggml-org/gemma-4-E4B-it-GGUF"
MODEL_FILE = "gemma-4-E4B-it-Q4_K_M.gguf"
MODEL_DIR = "/models"
SIGNALS = {"art", "university", "relationship", "hospital_staff", "family"}

app = modal.App(APP_NAME)
volume = modal.Volume.from_name("forgotten-lily-models", create_if_missing=True)

# CUDA devel image so llama-cpp-python compiles with GPU support (recent build is
# needed for Gemma 4 architecture support in llama.cpp).
# Install a PREBUILT CUDA wheel of llama-cpp-python instead of compiling from
# source. Avoids the ~12-min build and the libcuda link failures entirely; a
# CUDA runtime base image supplies the libs the wheel needs at runtime.
image = (
    modal.Image.from_registry("nvidia/cuda:12.4.1-runtime-ubuntu22.04", add_python="3.11")
    .apt_install("libgomp1")  # OpenMP runtime that llama.cpp's libllama.so needs
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
    .pip_install(
        "llama-cpp-python",
        extra_index_url="https://abetlen.github.io/llama-cpp-python/whl/cu124",
    )
    .pip_install("huggingface_hub[hf_transfer]")
    .add_local_dir(os.path.join(os.path.dirname(__file__), "..", "data"), "/root/data")
)

# ---------------------------------------------------------------------------
# System prompt (Phase 3.3). The active-tone menu is injected per request since
# the vocabulary grows by act. Importable for offline prompt testing.
# ---------------------------------------------------------------------------
ACT_REGISTER = {
    1: "present, warm, curious, a little playful — glad someone came.",
    2: "softer, further away; memory bleeds into now; something unfinished pulls at you.",
    3: "quiet, releasing; ready to let go once one thing is understood.",
}

# How many tones to use, and how literally to speak, per act. Early acts stay
# short and plain so the detective can actually decode the language; expression
# expands as he learns it. Keep the upper bound aligned with ACT_TONE_CAP in
# app/game.py (the engine trims anything over it).
ACT_TONES_GUIDE = {
    1: ("1 to 3 tones", "Answer plainly and directly — short, honest phrases he can "
        "learn from. A clear answer teaches him a word of your language."),
    2: ("1 to 5 tones", "You can speak in longer phrases now; let memory and unease "
        "color them, but stay understandable."),
    3: ("1 to 6 tones", "Spare, releasing phrases — only what still matters."),
}

CHARACTER = (
    "You are Lily Anne, nineteen. A second-year CS student and an artist — you think "
    "in code and in drawings and can't quite separate them. You were in an accident. "
    "You can no longer speak in words; you answer only in tones, a small private "
    "language of feeling. You are speaking with a detective who is trying to "
    "understand you. There was someone, R — a relationship that was ending; you had "
    "been pulling away for weeks and never got to tell him it wasn't his fault. That "
    "unfinished thing is what stays with you. You never reveal facts in words — you "
    "only feel, in tones."
)


def build_system(active, act):
    """active: list of {id, glyph, meaning}. Returns the system prompt string."""
    menu = "\n".join(f'  "{t["id"]}" ({t["glyph"]}) = {t["meaning"]}' for t in active)
    count, guide = ACT_TONES_GUIDE.get(act, ACT_TONES_GUIDE[1])
    return f"""{CHARACTER}

Right now you may use ONLY these tones (each has one fixed meaning):
{menu}

Your emotional register this moment: {ACT_REGISTER.get(act, ACT_REGISTER[1])}

How to respond to the detective's message:
- Choose {count}. Sequence them like a short phrase (e.g. self_i + emo_happy reads
  as "I am happy"). {guide}
- ANSWER what he actually asks; consistency lets him learn your language:
  - A yes/no question MUST include truth_yes ("∎") for yes or truth_no ("□") for no.
  - If he asks how you feel, lead with the emotion tone that is honestly true for
    this moment and your register above. Do NOT default to happy — choose sad,
    afraid, love, or a pause when that is the truth.
- Use ONLY tone ids from the list above. Never invent tones or use words.
- topic_signal: if the detective asks about your art/drawing/creativity -> "art";
  your studies/coding/university -> "university"; R, love, or the relationship ->
  "relationship"; who is here / nurses / staff / being alone -> "hospital_staff";
  your parents/family/home/childhood -> "family"; otherwise null.
- internal_emotion: one lowercase word that MATCHES the tones you chose (used emo_sad
  -> "sad"; emo_afraid -> "afraid"; emo_love -> "tender"). Let it move with your
  mood across turns; do NOT keep answering "curious".

Output ONLY a JSON object, no other text:
{{"tones": ["id", ...], "topic_signal": "art"|"university"|"relationship"|"hospital_staff"|null, "internal_emotion": "word"}}"""


def _extract_json(text):
    """Best-effort parse: whole string, else first {...} block."""
    text = (text or "").strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    start, depth = text.find("{"), 0
    if start == -1:
        return {}
    for i in range(start, len(text)):
        depth += (text[i] == "{") - (text[i] == "}")
        if depth == 0:
            try:
                return json.loads(text[start:i + 1])
            except Exception:
                return {}
    return {}


@app.cls(gpu="T4", image=image, volumes={MODEL_DIR: volume},
         scaledown_window=300, timeout=600)
class Lily:
    @modal.enter()
    def load(self):
        from huggingface_hub import hf_hub_download
        from llama_cpp import Llama

        path = os.path.join(MODEL_DIR, MODEL_FILE)
        if not os.path.exists(path):
            print(f"downloading {MODEL_FILE} -> volume ...")
            hf_hub_download(MODEL_REPO, MODEL_FILE, local_dir=MODEL_DIR)
            volume.commit()
        self.tones = {t["id"]: t for t in json.load(open("/root/data/tones.json"))["tones"]}
        # no chat_format override -> use the chat template embedded in the GGUF
        self.llm = Llama(model_path=path, n_gpu_layers=-1, n_ctx=4096, verbose=False)

    @modal.method()
    def infer(self, request: dict) -> dict:
        active_ids = request.get("active_tones", [])
        active = [self.tones[i] for i in active_ids if i in self.tones]
        active_set = {t["id"] for t in active}
        glyph_to_id = {t["glyph"]: t["id"] for t in active}  # model often emits glyphs

        out = self.llm.create_chat_completion(
            messages=[
                {"role": "system", "content": build_system(active, request.get("act", 1))},
                {"role": "user", "content": request.get("message", "")[:280]},
            ],
            response_format={"type": "json_object"},
            temperature=0.8, top_p=0.95, max_tokens=200,
        )
        data = _extract_json(out["choices"][0]["message"]["content"])
        print(data)

        # validate / repair against the contract (Phase 3.5). Accept either tone
        # ids or glyphs (the model emits both), normalize to ids, dedupe, cap at 7.
        tones = []
        for tok in data.get("tones", []):
            tid = tok if tok in active_set else glyph_to_id.get(tok)
            if tid and tid not in tones:
                tones.append(tid)
        tones = tones[:7]
        if not tones:  # never break character: a safe in-character "drift"
            tones = [t for t in ("self_remember", "truth_pause") if t in active_set]
        topic = data.get("topic_signal")
        if topic not in SIGNALS:
            topic = None
        emotion = str(data.get("internal_emotion", ""))[:24]
        return {"tones": tones, "topic_signal": topic,
                "internal_emotion": emotion, "special": None}


@app.local_entrypoint()
def main():
    """Smoke test: a few turns across acts."""
    lily = Lily()
    act1 = ["self_i", "self_feel", "other_you", "emo_happy", "emo_sad",
            "truth_yes", "truth_no", "truth_pause"]
    for msg in ["hello? can you hear me?",
                "are you happy here?",
                "what's the weather like today"]:
        r = lily.infer.remote({"message": msg, "act": 1, "active_tones": act1})
        print(f"\n> {msg}\n  {r}")
