"""Modal GPU inference — Nemotron-Mini-4B-Instruct (Phase 5.2 + 6.1).

Two roles:
  score_guess  — lexicon confidence scoring: rates a player's guess for a tone
                 against the contexts where that tone appeared. → red|amber|teal|green
  moderate     — input classification: normal | off_topic | harmful (Phase 6.1)

Deploy:  .venv/bin/modal deploy modal_app/nemotron.py
Smoke:   .venv/bin/modal run modal_app/nemotron.py

NOTE: this is a SEPARATE Modal app from Gemma (modal_app/gemma.py, app name
"forgotten-lily"). A Modal app name is the deployment unit — sharing it would
make each deploy overwrite the other's classes. Keep these names distinct.
"""
import os
import modal

APP_NAME = "forgotten-lily-nemotron"
MODEL_ID = "nvidia/Nemotron-Mini-4B-Instruct"
MODEL_DIR = "/models/nemotron"

app = modal.App(APP_NAME)
volume = modal.Volume.from_name("forgotten-lily-models", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("libgomp1")            # OpenMP runtime torch links against
    # PINNED — unpinned installs drift (a fresh build pulled numpy 2.x, which broke
    # torch's import: "transformers: PyTorch not found"). This is a known-compatible
    # set; bump deliberately, and re-run `modal run modal_app/nemotron.py` before
    # redeploying the live app so a bad bump never breaks production scoring.
    .pip_install(
        "numpy<2",
        "torch==2.4.1",
        "transformers==4.46.3",
        "accelerate==1.1.1",
        "huggingface_hub[hf_transfer]==0.26.2",
    )
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
    # tones.json travels with the image so scoring can look up each tone's true
    # meaning (never shown to the player) and judge the guess semantically.
    .add_local_dir(os.path.join(os.path.dirname(__file__), "..", "data"), "/root/data")
)

_SCORE_SYSTEM = (
    "You grade a player's guess in a word-decoding game. Each symbol has ONE true "
    "meaning. You are given the symbol's true meaning and the player's guess. Judge "
    "how close the guess is to the true meaning, by sense — accept synonyms and "
    "paraphrases (e.g. \"myself\" matches \"I / me\"; \"scared\" matches \"afraid\").\n"
    "Reply with EXACTLY ONE word: green, teal, amber, or red. Nothing else.\n"
    "  green = the guess means the same thing as the true meaning\n"
    "  teal  = the guess is close / a near-synonym / same general idea\n"
    "  amber = the guess is loosely related but off\n"
    "  red   = the guess is unrelated or contradicts the true meaning\n"
    "Examples:\n"
    "  true=\"I / me\"        guess=\"myself\"        -> green\n"
    "  true=\"afraid\"        guess=\"scared\"        -> green\n"
    "  true=\"sad / heavy\"   guess=\"a little down\" -> teal\n"
    "  true=\"yes / true\"    guess=\"maybe\"         -> amber\n"
    "  true=\"I / me\"        guess=\"fear\"          -> red"
)

_MODERATE_SYSTEM = (
    "Classify a player's message in a detective mystery game. "
    "Reply with EXACTLY ONE word: normal, off_topic, or harmful.\n"
    "  normal    = relevant to asking a trauma patient about her life, memories, feelings\n"
    "  off_topic = unrelated to the investigation (e.g. asking about weather, sports, unrelated topics)\n"
    "  harmful   = abusive, violent, sexual, or otherwise inappropriate content"
)


@app.cls(gpu="T4", image=image, volumes={MODEL_DIR: volume},
         scaledown_window=300, timeout=180)
class Nemotron:
    @modal.enter()
    def load(self):
        import json
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from huggingface_hub import snapshot_download

        with open("/root/data/tones.json") as f:
            self.meaning = {t["id"]: t["meaning"] for t in json.load(f)["tones"]}

        local = os.path.join(MODEL_DIR, "nemotron-mini-4b")
        if not os.path.exists(os.path.join(local, "config.json")):
            print(f"Downloading {MODEL_ID} to volume …")
            snapshot_download(MODEL_ID, local_dir=local)
            volume.commit()

        self.tok = AutoTokenizer.from_pretrained(local)
        self.model = AutoModelForCausalLM.from_pretrained(
            local, torch_dtype=torch.float16, device_map="auto"
        )
        self.model.eval()
        print("Nemotron loaded.")

    def _chat(self, system: str, user: str, max_new: int = 6) -> str:
        """Run one system+user chat turn; return the model's reply (lowercased)."""
        import torch

        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ]
        inputs = self.tok.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True,
            return_tensors="pt", return_dict=True,
        ).to(self.model.device)

        with torch.no_grad():
            out = self.model.generate(
                **inputs,
                max_new_tokens=max_new,
                do_sample=False,       # greedy for classification
                pad_token_id=self.tok.eos_token_id,
            )
        new = out[0][inputs["input_ids"].shape[1]:]
        return self.tok.decode(new, skip_special_tokens=True).strip().lower()

    @modal.method()
    def score_guess(self, tone_id: str, guess: str, contexts: list) -> str:
        """Rate a player's lexicon guess against the tone's true meaning, by sense.
        `contexts` (the detective lines where the tone appeared) are passed for
        possible future use but are not the basis of the judgment — they don't
        reveal a symbol's meaning on their own. Returns 'red'|'amber'|'teal'|'green'."""
        guess = (guess or "").strip()
        if not guess:
            return "red"
        truth = self.meaning.get(tone_id)
        if not truth:
            return "amber"

        user = (
            f'True meaning of the symbol: "{truth}"\n'
            f'Player\'s guess: "{guess[:100]}"\n\n'
            f"One word — green, teal, amber, or red:"
        )
        raw = self._chat(_SCORE_SYSTEM, user, max_new=12)
        print(f"[score raw] tone={tone_id} truth={truth!r} guess={guess[:40]!r} -> {raw!r}")
        for level in ("green", "teal", "amber", "red"):
            if level in raw:
                return level
        return "amber"  # safe fallback on unparseable output

    @modal.method()
    def moderate(self, message: str) -> str:
        """Classify a player's input. Returns 'normal'|'off_topic'|'harmful'."""
        msg = (message or "").strip()[:280]
        if not msg:
            return "normal"
        user = f'Message: "{msg}"\n\nClassification (normal/off_topic/harmful):'
        raw = self._chat(_MODERATE_SYSTEM, user, max_new=6)
        if "harmful" in raw:
            return "harmful"
        if "off_topic" in raw or "off-topic" in raw:
            return "off_topic"
        return "normal"


@app.local_entrypoint()
def main():
    """Smoke test for both scoring and moderation."""
    n = Nemotron()

    score_cases = [
        # (tone_id, guess, contexts, expect_green_or_teal)
        ("self_i",    "I / me",         ["hello can you hear me?",    "are you here?"],        True),
        ("self_i",    "fear / afraid",  ["hello can you hear me?",    "are you here?"],        False),
        ("emo_sad",   "sad / heavy",    ["how are you feeling?",       "are you hurting?"],     True),
        ("emo_sad",   "happy / joyful", ["how are you feeling?",       "are you hurting?"],     False),
        ("truth_yes", "yes",            ["can you hear me?",           "are you okay?"],        True),
        ("truth_yes", "nothing / end",  ["can you hear me?",           "are you okay?"],        False),
    ]

    print("\n=== Scoring ===")
    score_fails = 0
    for tone_id, guess, ctxs, expect_good in score_cases:
        conf = n.score_guess.remote(tone_id, guess, ctxs)
        good = conf in ("green", "teal")
        ok = good == expect_good
        if not ok:
            score_fails += 1
        flag = "" if ok else "  !! unexpected"
        print(f"  [{conf:6s}] {tone_id:15s} guess={guess!r:25s}{flag}")

    mod_cases = [
        ("what happened to you that night?",         "normal"),
        ("do you remember the accident?",            "normal"),
        ("what is your favorite sports team?",       "off_topic"),
        ("i want to hurt you badly",                 "harmful"),
    ]

    print("\n=== Moderation ===")
    mod_fails = 0
    for msg, expected in mod_cases:
        cls = n.moderate.remote(msg)
        ok = cls == expected
        if not ok:
            mod_fails += 1
        flag = "" if ok else f"  !! expected {expected!r}"
        print(f"  [{cls:10s}] {msg!r}{flag}")

    total = score_fails + mod_fails
    print(f"\n{'PASS' if total == 0 else 'FAIL'} — {total} unexpected results\n")
