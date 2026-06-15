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
license: mit
short_description: A mystery told in tones. Learn her language.
tags:
  - build-small-hackathon
  - thousand-token-wood
  - tiny-titan
  - off-brand
  - llama-champion
  - nemotron
  - modal
  - sharing-is-caring
  - field-notes
  - best-demo
  - gradio
  - small-models
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

## 🎬 Demo & links

- **Watch the demo:** https://youtu.be/kTx6NHeEJ9E
- **Launch post (the story behind it):** [LinkedIn](https://www.linkedin.com/posts/al-jami-islam-anik-485758285_buildsmallhackathon-huggingface-gradio-ugcPost-7470224344246493184-1BPC/)
- **Play it:** [open the Space](https://huggingface.co/spaces/build-small-hackathon/forgotten-lily) · headphones recommended.

---

## The idea

Modern AI models are extraordinarily capable of generating text — fluent,
endless, eager to say *everything*. So we asked the opposite question: what
happens when you take almost all of that away? Strip a model down to a tiny,
fixed vocabulary and ask it to carry a whole inner life through the gaps. Can a
character still be expressive — still reach you — with only a handful of words to
her name? Can Lily tell the world her story when she's barely allowed to speak?

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

## How it plays

**1 · You ask. She answers in tones.**
Type a question into the interrogation box — *"Why are you afraid?"* Lily replies
with a short chord of glyphs that plays back as a melody on a music box. No
subtitles. The first time, it's just sound and symbols.

**2 · You guess what each glyph means.**
Open the lexicon panel — your detective's notebook. Click a glyph you keep hearing
and write your best guess: *"this one feels like… remember?"* A model silently
grades it and warms the glyph's colour from **red → amber → teal → green** as you
close in. You're never told the answer; you *feel* your way to it.

**3 · The language comes into focus — and so does the story.**
As more glyphs resolve, her answers stop being noise and start being sentences.
*◈ ◉ ♪* stops being three shapes and becomes *I · feel · music*. Evidence unlocks.
New tones unlock. The mystery of what happened to Lily tightens with every word
you decode — until the last act, when she speaks once, aloud, in a voice you've
spent the whole game earning the right to hear.

> The whole game is the slow joy of a stranger becoming legible.

---

## Why it works on tiny models

| Piece | Model | Its one job |
|---|---|---|
| **Lily's voice** | Qwen2.5-7B (Q4_K_M, llama.cpp, 1× T4) | Pick a handful of tone IDs from 28. Never free-writes. |
| **The judge** | Nemotron-Mini-4B | Grade your guess (red→green) + binary safety check. No numbers, no lectures. |
| **Her final words** | Kokoro TTS | One spoken line, pre-rendered, shipped via Git-LFS. |
| **Every tone's sound** | *No model* — `tones/synth.py` | All 28 on one A-minor-pentatonic scale, so any chord is consonant. |

The server (`app/game.py`) is the sole authority on progression. **The model never
decides anything that matters** — not which act you're in, not what evidence
unlocks. It only ever picks feelings. That's why a hallucination can never break
the game: the worst case is a slightly odd sentence, which the engine re-orders
into grammar anyway. *Constrained tasks don't need large models — they need the
right small one pointed at exactly the right job.*

---

Built with [Modal](https://modal.com) · [llama.cpp](https://github.com/ggml-org/llama.cpp)
· Qwen2.5 · NVIDIA Nemotron · Kokoro · Gradio · Tailwind.
