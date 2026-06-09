---
title: Forgotten Lily
emoji: 🥀
colorFrom: gray
colorTo: indigo
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
short_description: A mystery told in tones. Learn her language. Find out what happened.
---

# Forgotten Lily

A narrative mystery game disguised as a conversation. You are a detective. Across
the table is a girl who can no longer speak in words — only in tones. Learn her
language. Find out what happened to her.

> Built for the HuggingFace **Build Small** hackathon — *Thousand Token Wood*.

This README will become the **Field Notes** writeup before submission. For now it
is a developer map.

## Project layout
```
app/        gr.Server backend + custom HTML/Tailwind/JS frontend
  static/   index.html, tones/ (generated WAVs), notes/ (assets)
modal_app/  Modal serverless GPU inference (Gemma 4 E4B; Nemotron, MiniCPM later)
tones/      Procedural tone synthesis (scipy/numpy) -> app/static/tones/*.wav
notes/      Note source content + asset generation
data/       tones.json (vocabulary), notes.json (evidence) — single sources of truth
docs/       CONTRACT.md (inference I/O), STATE.md (act/unlock rules)
documents/  PLAN.md — the full design doc
todo.md     Implementation roadmap
```

## Build status
See `todo.md`. Phases 0–5 done: contracts/data, tone synth, mock vertical slice, live
**Gemma 4 E4B** on Modal (the conversation), evidence/notes + empathy, lexicon drawer,
and **Nemotron-Mini-4B** semantic guess-scoring (Phase 5.2). Next: input moderation
(Phase 6), then the ending sequence (7.3).

Two Modal apps, deployed separately (distinct app names — sharing one makes deploys
clobber each other): `forgotten-lily` (Gemma, class `Lily`) and
`forgotten-lily-nemotron` (Nemotron, class `Nemotron`).

## Local dev
```
python tones/synth.py          # generate the 24 tone WAVs (app/static/tones/)
USE_MOCK=1 python app.py       # run the game (Gradio-mounted) on mock inference, no GPU
USE_MOCK=0 python app.py       # run on live Modal models (needs `modal token new`)
# -> game UI at http://localhost:7860/   ·   Gradio engine at /engine

# deploy / smoke the inference models:
modal deploy modal_app/gemma.py       &&  modal run modal_app/gemma.py
modal deploy modal_app/nemotron.py    &&  modal run modal_app/nemotron.py
```
Generated tone audio is gitignored; run `tones/synth.py` after cloning. (Ambient music
was removed by design — only the tones make sound; `tones/ambient.py` is now unused.)
