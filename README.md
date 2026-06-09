---
title: Forgotten Lily
emoji: 🥀
colorFrom: gray
colorTo: indigo
sdk: gradio
sdk_version: 5.49.1
python_version: "3.12"
app_file: app.py
pinned: false
short_description: A mystery told in tones. Learn her language.
---

# Forgotten Lily

*A narrative mystery you play by learning a language that has never been spoken.*

You are a detective. Across the table is Lily Anne, nineteen. She can no longer
speak in words — only in **tones**, small sounds that each carry one fragment of
meaning. You ask her questions. She answers in chords of glyphs. Slowly, by
listening and guessing, you build a dictionary of her language — and as the words
resolve, so does what happened to her.

> Built for the Hugging Face **Build Small** hackathon — *Thousand Token Wood*.
> Every model in it is tiny, runs on a single T4, and is asked to do one narrow
> thing extremely well.

---

## The idea

Most "talk to an AI character" games fail the same way: the model says too much,
too fluently, and the magic evaporates. We wanted the opposite — a character whose
every utterance is *scarce*, and where the player does the meaning-making.

So Lily has no words. She has **28 tones** — `I`, `you`, `music`, `family`,
`remember`, `afraid`, `before`, `nothing`, `friend`, `lonely`… — and nothing else.
When you ask "do you like music?", she might answer `◈ ◉ ♪` — *I · feel · music* —
and it's on you to hear that as "yes, it's everything to me." The lexicon panel is
your notebook: you write down what you think each glyph means, and a model quietly
grades how close you are. The game is the slow joy of a language coming into focus.

The story underneath is about **unfinished life**, not death: a girl who wanted to
become a composer, to see the world, to stand at Mount Fuji at sunrise with both
her divorced parents — once, after she graduated. You don't learn she died until
the very end. Everything she says is in the present tense, because to her it still is.

---

## What's small, and what it does

The whole point of the entry is that **constrained tasks don't need large models** —
they need the right small one pointed at exactly the right job.

- **Lily's voice — Qwen2.5-7B-Instruct** (GGUF Q4_K_M, llama.cpp, one T4).
  She never free-writes. Given your line and the tones unlocked this act, she
  returns a tiny JSON object choosing a handful of tone IDs and a topic signal.
  That's it. A 7B model is plenty when the entire output space is 28 words.
- **The judge — Nemotron-Mini-4B** (its own Modal app). Two narrow jobs: score
  your guess against a tone's *true* meaning (which you're never shown) →
  red/amber/teal/green, and a binary safety check on your input. No numbers, no
  lectures — just a colour warming up as you get closer.
- **The voice you can't synthesize — Kokoro TTS.** Her single spoken line at the
  end is pre-rendered once and committed via Git-LFS, because it can't exist until
  the end exists.
- **No neural audio at all for the tones.** Every glyph's sound is *designed*,
  procedurally, in `tones/synth.py`: all 28 sit on one shared A-minor-pentatonic
  scale, so any combination she chooses is consonant — a reply plays back as a
  little melody on a music box, not a row of beeps. Determinism where determinism
  belongs.

The server (`app/game.py`) is the sole authority on progression. **The model never
decides anything that matters** — not which act you're in, not what evidence
unlocks. It only ever picks feelings. That separation is why a hallucination can
never break the game; the worst case is a slightly odd sentence, which the engine
re-orders into grammar anyway.

---

## Things we learned building it

- **Coherence beats correctness.** The first vocabulary had connective tones —
  `and`, `to`, `but` — so Lily could form "real" sentences. They produced garbage
  like *"I and"*. We deleted every connective and let the engine sort her chosen
  tones into a fixed grammar instead. Now she can't say "I and music"; she says
  *I · music*, and the player fills the gap. An answer that's slightly tangential
  but *meaningful* beats one that's literally correct but reads as noise.
- **Design vocabulary by need, not symmetry.** The tones started as a tidy 6×4
  grid. It looked balanced and said the wrong things. We tore it up and rebuilt
  from "what does *this character* actually need to say?" — which is lopsided on
  purpose: lots of feelings, few connectives, words like `study` and `lonely` that
  exist only because they're true of her. Then we split "people" from "things" so a
  player decoding a glyph gets a sharper hint.
- **A bigger model helps *selection*, not grammar.** Once ordering was the engine's
  job, upgrading the model (Gemma E4B → Qwen2.5-7B) stopped mattering for sentence
  structure and started mattering for *taste* — choosing tones that mean something
  true, and resisting the urge to default to "happy".
- **Errors must stay in character.** There is no error message anywhere a player
  can reach. A malformed model reply, a moderation hiccup, a model that emits a
  stray emoji — all of it resolves to Lily going quiet, or to a safe felt response.
  The fiction never cracks.

---

## Play it

```
USE_MOCK=1 python app.py     # offline: a rule-based mock stands in for the model, no GPU
USE_MOCK=0 python app.py     # live: real models on Modal
# → http://localhost:7860
```

On the Space, `USE_MOCK=0` with Modal + HF secrets. Tone WAVs are build output
(gitignored) — `app.py` regenerates all 28 on startup, so a fresh clone has audio.

```
# deploy / smoke the inference models (two separate Modal apps — distinct names,
# or each deploy clobbers the other):
modal deploy modal_app/gemma.py      &&  modal run modal_app/gemma.py
modal deploy modal_app/nemotron.py   &&  modal run modal_app/nemotron.py
```

## Project map

```
app/        FastAPI backend + custom HTML/Tailwind/JS frontend, mounted as Gradio
  game.py     the engine — state, act gates, note unlocks, grammar ordering
  static/     index.html, generated tones/*.wav, audio/
modal_app/  Modal GPU inference — gemma.py (Lily: Qwen2.5-7B), nemotron.py (judge)
tones/      synth.py — procedural tone synthesis (scipy/numpy) → app/static/tones/
data/       tones.json (the 28-tone language), notes.json (evidence) — single sources of truth
docs/       CONTRACT.md (model I/O), STATE.md (act/unlock rules)
documents/  PLAN.md — the full design doc · todo.md — the roadmap
```

Built with [Modal](https://modal.com) · [llama.cpp](https://github.com/ggml-org/llama.cpp)
· Qwen2.5 · NVIDIA Nemotron · Kokoro · Gradio · Tailwind.
