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
  static/   index.html, tones/ (generated WAVs), notes/ (assets), audio/ (ambient)
modal/      Modal serverless GPU inference functions (Gemma, Nemotron, MiniCPM)
tones/      Procedural tone synthesis (scipy/numpy) -> app/static/tones/*.wav
notes/      Note source content + asset generation
data/       tones.json (vocabulary), notes.json (evidence) — single sources of truth
docs/       CONTRACT.md (inference I/O), STATE.md (act/unlock rules)
documents/  PLAN.md — the full design doc
todo.md     Implementation roadmap
```

## Build status
See `todo.md`. Phase 0 (contracts + data) done; building tone synth + mock vertical slice.

## Local dev
```
python tones/synth.py          # generate the 24 tone WAVs (app/static/tones/)
python tones/ambient.py        # generate the ambient piano bed (app/static/audio/)
USE_MOCK=1 python app.py       # run the game (Gradio-mounted) on mock inference, no GPU
# -> game UI at http://localhost:7860/   ·   Gradio engine at /engine
```
Generated audio is gitignored; run the two scripts after cloning.
