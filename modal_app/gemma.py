"""Modal GPU inference — Lily's reasoning model (Phase 3).

Runs Qwen2.5-7B-Instruct (GGUF Q4_K_M) via llama-cpp-python on a T4, behind the
contract in docs/CONTRACT.md. (Upgraded from Gemma 4 E4B for sharper tone
selection / JSON-menu discipline — the swap is just the repo/file below since the
llama.cpp path is model-agnostic.) The model speaks AS Lily: given the detective's
line and the tones active this act, it returns a short JSON object choosing 1-7
tone ids, an optional topic_signal, and an internal_emotion tag.

Deploy:   .venv/bin/modal deploy modal_app/gemma.py
Smoke:    .venv/bin/modal run modal_app/gemma.py
Weights download to a persistent Volume on first container start (then cached).
"""
import json
import os

import modal

APP_NAME = "forgotten-lily"
MODEL_REPO = "bartowski/Qwen2.5-7B-Instruct-GGUF"
MODEL_FILE = "Qwen2.5-7B-Instruct-Q4_K_M.gguf"
MODEL_DIR = "/models"
SIGNALS = {"music", "university", "relationship", "family", "travel"}

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

# How many tones to use per act — short early so the detective can decode the
# language, wider as he learns it. Keep the upper bound aligned with ACT_TONE_CAP
# in app/game.py (the engine trims anything over it).
ACT_TONE_COUNT = {1: "1 to 4 tones", 2: "1 to 5 tones", 3: "1 to 6 tones"}

CHARACTER = (
    "You are Lily Anne, nineteen. A second-year CS student and a musician — you think "
    "in code and in music and can't quite separate them; a piece of yours, 'A Held "
    "Breath,' is a finalist for an international prize. You were in an accident. You "
    "can no longer speak in words; you answer only in tones, a small private language "
    "of feeling. You are speaking with a detective who is trying to understand you. "
    "What you ache for is the life still ahead of you: to become a composer, to see "
    "the whole world — and most of all to stand at Mount Fuji at sunrise with BOTH "
    "your parents, who divorced when you were eleven, together for once, after you "
    "graduate. You grew up shuttled between their two homes and learned to go quiet "
    "when things got hard; you poured yourself into your studies — learning was a "
    "refuge you genuinely loved — and you never had many close friends, though you "
    "quietly longed for them. There was someone, R; that ended gently and recently — it "
    "weighs on you, but it is not the center of you. The center is everything you "
    "still want and have not done yet. The last evening hurts to reach toward — a "
    "quiet goodbye, your parents' voices rising in the hall, the dark, a road — and "
    "you flinch from it. You never reveal facts in words — you only feel, in tones."
)


def build_system(active, act, mood="warm"):
    """active: list of {id, glyph, meaning}. mood: Lily's carried emotional state.
    Returns the system prompt string."""
    menu = "\n".join(f'  {t["glyph"]}  {t["id"]} = {t["meaning"]}' for t in active)
    count = ACT_TONE_COUNT.get(act, ACT_TONE_COUNT[1])
    return f"""{CHARACTER}

This is your ENTIRE vocabulary right now — there are no other words you can use:
{menu}

You feel {mood} right now ({ACT_REGISTER.get(act, ACT_REGISTER[1])}). Stay inside that.
It can shift, but only gradually and for a reason — never flip from one reply to the next.

To answer the detective, choose a few of these tones that TOGETHER say one true,
coherent thing. You do not need to order them — they are arranged into a readable
phrase for you; just pick the RIGHT tones so the phrase has a clear, felt meaning.
(e.g. "I love music" = self_i, emo_love, music; "I want the world" = self_i, act_want,
other_world; "I remember us, before" = self_i, self_remember, other_us, time_before.)
- Use {count}. A few well-chosen tones read more clearly than many — never pad.
- Your reply does NOT have to directly answer his question. A real feeling, or an
  association the question stirs — a person, place, time, or memory — is a true answer.
  What matters is that it MEANS something he can feel and decode, not that it is the
  literal reply. Always say something coherent; never a random scatter of tones.
- Use only what these tones can express. If they can't say a thing exactly, reach for the
  nearest honest one — never force a tone that isn't true, never invent one or use a word.
- Don't default to the happy tone; let sad, afraid, tired, or love be the answer when that
  is what is real. A direct yes/no question is answered with truth_yes or truth_no.

topic_signal: what is he asking ABOUT? "music" (your playing/composing/songs),
"university" (studies/coding/graduating), "travel" (the world, Mount Fuji, the trip),
"family" (parents/home/childhood), "relationship" (R, love) — else null.
internal_emotion: one lowercase word that matches the tones you chose; let it move with
your mood, don't keep answering "curious".

Output ONLY this JSON, nothing else:
{{"tones": ["id", ...], "topic_signal": "music"|"university"|"travel"|"family"|"relationship"|null, "internal_emotion": "word"}}"""


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
                {"role": "system", "content": build_system(
                    active, request.get("act", 1), request.get("mood", "warm"))},
                {"role": "user", "content": request.get("message", "")[:280]},
            ],
            response_format={"type": "json_object"},
            temperature=0.8, top_p=0.95, max_tokens=200,
        )
        data = _extract_json(out["choices"][0]["message"]["content"])
        print(data)

        # validate / repair against the contract (Phase 3.5). The model emits ids,
        # glyphs, AND — fairly often — the two fused into one token ("♯emo_afraid",
        # "♪music"). Match a pure id/glyph first, then recover a fused/garbled
        # token by finding the id (or glyph) embedded in it. Dropping these silently
        # was costing good answers a fallback to "drift". Normalize to ids, dedupe, cap.
        def _resolve(tok):
            tok = str(tok).strip()
            if tok in active_set:
                return tok
            if tok in glyph_to_id:
                return glyph_to_id[tok]
            for tid in active_set:            # fused token, e.g. "⌒time_before"
                if tid in tok:
                    return tid
            for glyph, tid in glyph_to_id.items():
                if glyph and glyph in tok:
                    return tid
            return None

        tones = []
        for tok in data.get("tones", []):
            tid = _resolve(tok)
            if tid and tid not in tones:
                tones.append(tid)
        tones = tones[:7]
        if not tones:  # never break character: a safe in-character "drift"
            tones = [t for t in ("self_feel", "self_i") if t in active_set]
        topic = data.get("topic_signal")
        if topic not in SIGNALS:
            topic = None
        emotion = str(data.get("internal_emotion", ""))[:24]
        return {"tones": tones, "topic_signal": topic,
                "internal_emotion": emotion, "special": None}


@app.local_entrypoint()
def main():
    """Verification test: multi-act quality check for emo_happy overuse and
    internal_emotion='curious' stasis. Reports PASS/FAIL per case."""
    lily = Lily()

    # derive the active set per act straight from the data so this never drifts
    import json as _json
    _tones = _json.load(open(os.path.join(os.path.dirname(__file__), "..", "data", "tones.json")))["tones"]
    _act = lambda a: [t["id"] for t in _tones if t["act_active"] <= a]
    ACT1, ACT2, ACT3 = _act(1), _act(2), _act(3)

    # (message, act, active_tones, label, warn_if_emo_happy_in_response)
    CASES = [
        ("hello, can you hear me?",                    1, ACT1, "Act I  greeting",          False),
        ("are you happy?",                             1, ACT1, "Act I  happy question",     False),
        ("are you sad right now?",                     1, ACT1, "Act I  sad question",       True),
        ("you seem distant. are you okay?",            1, ACT1, "Act I  empathy",            True),
        ("how are you feeling since the accident?",    2, ACT2, "Act II feeling",            True),
        ("do you still think about R?",                2, ACT2, "Act II about R",            False),
        ("are you afraid of something?",               2, ACT2, "Act II fear",               True),
        ("what happened the night you were walking home?", 2, ACT2, "Act II accident night", True),
        ("can you let go now?",                        3, ACT3, "Act III let go",            True),
        ("is there anything you still need to say?",   3, ACT3, "Act III final message",     True),
    ]

    fails = 0
    print(f"\n{'─' * 90}")
    print(f"{'CASE':<40} {'TONES':<35} {'EMOTION':<12} STATUS")
    print(f"{'─' * 90}")
    for msg, act, tones, label, warn_happy in CASES:
        r = lily.infer.remote({"message": msg, "act": act, "active_tones": tones})
        emotion = r.get("internal_emotion", "")
        tone_ids = r.get("tones", [])

        issues = []
        if emotion == "curious" and act > 1:
            # "curious" is the correct Act I register; only flag it in Act II/III
            issues.append("emotion=curious")
        if warn_happy and "emo_happy" in tone_ids:
            issues.append("emo_happy on somber")

        status = "FAIL !! " + ", ".join(issues) if issues else "ok"
        if issues:
            fails += 1
        print(f"{label:<40} {str(tone_ids):<35} {emotion:<12} {status}")

    print(f"{'─' * 90}")
    print(f"\n{'PASS' if fails == 0 else 'FAIL'} — {fails}/{len(CASES)} cases with issues\n")
