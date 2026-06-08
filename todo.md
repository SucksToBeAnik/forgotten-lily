# Forgotten Lily — Implementation TODO

Working roadmap derived from `documents/PLAN.md`. Reorganized for de-risking and a
fast vertical slice. Check items off as we go. Each item has a **DoD** (definition of done).

**Guiding principles**
- Build the **JSON contract** between Gemma and the frontend first; everything keys off it.
- Build a **mock inference layer** so the UI is fully developable with zero GPU cost.
- Land an **end-to-end vertical slice** (type → tones → chips + audio) before polishing any layer.
- Prize models (MiniCPM, Nemotron) are **additive layers**, never blockers for the core loop.
- The game must **never break character** — error states are diegetic (Lily goes quiet).

---

## Phase 0 — Project Scaffolding & Contracts
- [x] **0.1** Repo layout: `app/` (gr.Server + frontend), `modal/` (inference fns), `tones/` (synth + generated WAVs), `notes/` (note content + assets), `data/` (lexicon/tone defs), `docs/`.
  - DoD: directories exist, README stub, `.gitignore` (ignore `*.wav` build output, model weights, `__pycache__`).
- [x] **0.2** Define **tone vocabulary as data** — `data/tones.json`: 24 entries `{id, glyph, category, meaning, act_active, audio_profile}`.
  - DoD: all 24 tones from PLAN §6.2 encoded with their act-activation tier (§6.3).
- [x] **0.3** Define the **Gemma response JSON contract** — `docs/CONTRACT.md`. Lily's reply = `{tones: [glyph...], topic_signal: <note_key|null>, internal_emotion: <tag>}`. Player turn request = `{message, turn, act, active_tones, lexicon_state}`.
  - DoD: documented request/response schemas + 3 worked examples (Act I greeting, off-topic, Act III finale).
- [x] **0.4** Define **note inventory as data** — `data/notes.json`: 10 notes `{id, title, unlock_type, unlock_value, asset, body, act}` (PLAN §7.3).
  - DoD: all N01–N10 encoded with unlock rules (threshold vs topic).
- [x] **0.5** Define **act/state machine** — `docs/STATE.md`: act transitions, tone-unlock tiers, note thresholds, lexicon-size gates.
  - DoD: deterministic rules for Act I→II→III transitions written down (PLAN §4.2–4.4).

## Phase 1 — Tone Synthesis (offline, no GPU)
- [x] **1.1** `tones/synth.py` — procedural generator (scipy/numpy) producing one WAV per tone, driven by `tones.json` audio profiles (PLAN §6.4).
  - DoD: running it emits 24 WAVs into `app/static/tones/`.
- [x] **1.2** Tune per-category character: Self=warm hums, Other=cooler/directional, Time=enveloped pulses, Emotion=minor/bright intervals, Action=short percussive, Truth=near-silence pause + sub-bass end.
  - DoD: listen pass — categories are audibly distinct; pause ≈ silence; end ≈ sub-frequency.
- [x] **1.3** Loudness-normalize + short fades to avoid clicks; consistent sample rate.
  - DoD: no clipping/pops; tones sit at even perceived volume.

## Phase 2 — Mock Inference + Vertical Slice (THE milestone)
- [x] **2.1** `app/mock_inference.py` — returns valid contract JSON deterministically from canned/rule-based logic (keyword → topic_signal, act → active_tones).
  - DoD: drop-in module matching the real inference signature.
- [x] **2.2** `gr.Server` app skeleton serving static `index.html` + API routes (`/turn`, `/state`, `/lexicon`). Wire to mock.
  - DoD: `curl`/fetch to `/turn` returns contract JSON; page loads.
- [x] **2.3** Minimal conversation panel: input (280-char counter), send, render Lily's reply as **tone chips**, sequential **audio playback** (one tone at a time).
  - DoD: type a message → chips appear → tones play in order. **End-to-end loop works on mocks.**
- [x] **2.4** Session state (server-side keyed by session id): turn count, act, tones-seen, lexicon, notes-unlocked.
  - DoD: refresh-safe state; act advances per STATE rules.

## Phase 3 — Modal Inference (replace the mock)
- [ ] **3.1** Modal account/CLI auth; persistent **Volume** for weights.
  - DoD: `modal token` set; empty volume created.
- [ ] **3.2** **Gemma 4 12B** GGUF Q4_K_M via `llama-cpp-python` on A10G; download-to-volume on first run.
  - DoD: warm function returns text for a prompt.
- [ ] **3.3** Author + iterate **Lily system prompt** — enforces tone-only output, respects `active_tones`, emits the JSON contract, stays in character.
  - DoD: 10/10 test prompts return schema-valid JSON using only active tones.
- [ ] **3.4** Swap mock → Modal in gr.Server (keep mock behind a flag for offline dev).
  - DoD: vertical slice runs on real Gemma; `USE_MOCK=1` still works.
- [ ] **3.5** Robustness: JSON repair/validation, retry, fallback to a safe in-character tone (`◇ —`) on malformed output.
  - DoD: malformed model output never crashes a turn.

## Phase 4 — Notes / Evidence Board
- [ ] **4.1** Write all 10 note bodies + source/design the visual assets (text thread, sketchbook, forms, photo) per PLAN §7.3.
  - DoD: each note renders with intended "read twice" content.
- [ ] **4.2** Evidence board UI (Tailwind): kraft cards, seeded rotation, red pushpin, DM Mono, pin-drop animation.
  - DoD: notes appear as designed; rotation stable across reloads.
- [ ] **4.3** Unlock engine: threshold (lexicon size) + topic (Gemma `topic_signal`) → reveal note. N10 placed flat/center, unpinned.
  - DoD: asking about art unlocks N02; 6-tone threshold unlocks N03; finale reveals N10.

## Phase 5 — Lexicon + Nemotron Scoring
- [ ] **5.1** Lexicon drawer (slides up): glyph, guess text field, color confidence bar; locked tones as grayed `?`.
  - DoD: drawer opens, guesses persist, unseen tones hidden as count.
- [ ] **5.2** **Nemotron-Mini 4B** on Modal (T4) — semantic scoring of guess vs the tone's observed contexts → {red/amber/teal/green}.
  - DoD: a correct guess trends green across turns; wrong stays red. **No numbers shown.**
- [ ] **5.3** Retroactive chip updates: past message chips reflect current lexicon/confidence.
  - DoD: changing a guess updates hovers on old chips.

## Phase 6 — Moderation + Input Edge Cases
- [ ] **6.1** Nemotron dual-role: harmful input → Lily plays `∅`, journal line *"She doesn't respond to that."* (PLAN §8.2).
  - DoD: harmful input never errors, never breaks fiction.
- [ ] **6.2** Off-topic input → `◇ —`, journal *"She seems to have drifted somewhere."* (§8.3).
  - DoD: irrelevant input handled diegetically.

## Phase 7 — Atmosphere + Ending
- [x] **7.1** Background ambient piano (CC0) via Web Audio API; **duck to silence during tones**, fade back (PLAN §6.5).
  - DoD: world goes quiet whenever Lily speaks.
- [ ] **7.2** Act-based color-temperature transitions via Tailwind CSS vars (warm → gray-amber → cold mono). Music EQ shift per act; gone by Act III.
  - DoD: visible/audible drift across acts.
- [ ] **7.3** Ending sequence: final 7-tone sequence (1.5s apart) → 5s fade to white → **Kokoro TTS** line *"I just wanted someone to know it wasn't his fault."* → 8s silence → memorial screen (name, dates, player's full lexicon). No score/replay.
  - DoD: full ending plays start to finish as scripted (PLAN §4.5).

## Phase 8 — Prize Extras
- [ ] **8.1** **MiniCPM-o 4.5** optional audio input (mic button) on a cold-start Modal endpoint → transcribe/interpret to a player turn (OpenBMB badge).
  - DoD: mic input produces a normal game turn; absence doesn't block text play.
- [ ] **8.2** **Trace logging** to HF dataset — metadata only, never message content (turn, act, tones, moderation class, note unlocked, lexicon size) (PLAN §10.7, Sharing is Caring).
  - DoD: rows append per turn; verified no PII/message text.

## Phase 9 — Submission
- [ ] **9.1** Space README as **Field Notes** narrative writeup (PLAN §10.6).
- [ ] **9.2** `modal deploy` all endpoints; HF Space (Gradio SDK, CPU Basic) with secrets `MODAL_TOKEN_ID/SECRET`, `HF_TOKEN`.
- [ ] **9.3** Full playthrough test (Act I→III, all notes, ending); mobile responsiveness pass.
- [ ] **9.4** Record demo video; set Space public.
  - DoD: live public Space + video + README submitted; badges claimed.

---

### Prize → Task traceability
| Prize/Badge | Covered by |
|---|---|
| Main (Thousand Token Wood) | Whole game |
| NVIDIA (Nemotron) | 5.2, 6.1 |
| OpenBMB (MiniCPM) | 8.1 |
| llama.cpp | 3.2 |
| Off-brand UI | 2.2, 4.2, 5.1, 7.x |
| Off the Grid (local only) | 3.x, 5.2, 8.1 (all Modal) |
| Modal credits | 3.x |
| Sharing is Caring | 8.2 |
| Field Notes | 9.1 |

### Critical path
0.2/0.3 (contracts) → 1.x (tones) → 2.x (mock + vertical slice) → 3.x (real Gemma) → everything else parallelizable.

### Open questions / risks
- Gemma 4 12B Q4_K_M JSON reliability under llama.cpp — mitigate with strict prompt + repair (3.5).
- A10G cold-start latency vs "warm afternoon" pacing — consider keep-warm during judging.
- Kokoro TTS voice fit for a 19-year-old — audition early in Phase 7.
- CC0 ambient loop sourcing/licensing — confirm before 7.1.
