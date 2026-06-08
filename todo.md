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

## Current status (session handoff — updated end of "core-loop fun" pass)

**Done:** Phases 0–3 (contracts/data, synth, engine+mock+Gradio+Tailwind UI, real
Gemma 4 E4B on Modal). Phase 4 (evidence) and Phase 5.1 (lexicon drawer) now largely
done. A big gameplay-feel + content pass landed this session (see below).

**This session's changes (all live):**
- **Learnability:** category scaffold on chips + lexicon (Self/Other/Time/Emotion/
  Action/Truth, colored); per-act tone cap (`ACT_TONE_CAP` 3/5/7) so Act I stays short
  & decodable; prompt rewritten for direct answers (yes/no → truth tones, lead with the
  honest emotion, `internal_emotion` must match tones / stop saying "curious").
- **Vocabulary:** promoted `time_now` (∿) and `act_stay` (←) into Act I (8→10 tones);
  relaxed the Act I→II gate accordingly.
- **Evidence ⇄ lexicon:** each note has a `hint {tone_id,text}` that surfaces in the
  lexicon once that tone is heard — evidence now *helps decode* the language.
- **Empathy system:** caring/personal questions raise `state.empathy` (keyword
  heuristic in game.py) → unlocks `empathy` backstory notes. 5 NEW notes (N11–N15:
  two homes/divorce, mother's voicemail, counseling slip, unsent letter, friend M).
  Every note now has `found` provenance + a `summary`/`order`.
- **Her Story tab:** second tab beside Evidence; assembles found-note summaries into a
  narrative (`/api/story`, `game.story_view`).
- **UX:** ambient music REMOVED (tones only); intro brief pinned to evidence board;
  lexicon is now a LEFT sidebar (conversation stays scrollable); Enter/↵ affordance to
  save a guess; discovery feel (NEW chip flash + toast, note glow/badge + toast);
  evidence-type icons; decoded-glyph corner-dot highlight; thinking dots while
  generating; tooltip left-anchored (no clipping). Local `[modal ←]` response logging
  in app/modal_inference.py.

**Model:** Gemma 4 **E4B** (GGUF Q4_K_M) via llama-cpp-python on a Modal **T4** (not
PLAN's 12B; trivial to upgrade). Workspace `anik-islam1494`, app `forgotten-lily`
(class `Lily`). The `family` topic_signal was added → **redeploy done** this session.

**Run it:**
```
python tones/synth.py        # regenerate tone WAVs (gitignored); ambient.py now unused
USE_MOCK=1 python app.py     # offline, rule-based mock, no GPU
USE_MOCK=0 python app.py     # live Gemma on Modal (needs `modal token new` done)
# game at http://localhost:7860/   ·   redeploy model: modal deploy modal_app/gemma.py
# watch raw model JSON: modal app logs forgotten-lily
```
Modal gotcha (solved, see modal_app/gemma.py): PREBUILT llama-cpp-python CUDA wheel +
CUDA runtime image + `libgomp1`; do NOT compile from source, do NOT set chat_format.

**Verify-by-playing TODO (highest value next):**
- Confirm the P2 prompt fix actually cured `emo_happy`/`curious` overuse on the LIVE
  model across Acts II/III (only smoke-tested; needs a real playthrough).
- Tune empathy pacing (N15=2 … N14=5) and hint wording — enough nudge, no spoiler.

**Recommended next feature:** Phase 6.1/6.2 (Nemotron `moderate` already deployed &
smoke-passing — wire `/api/turn` to classify input → harmful plays `∅`, off-topic plays
`◇ —`, diegetic journal lines). Then ending (7.3).

**Nemotron note:** Phase 5.2 done this session. Lives in its own Modal app
`forgotten-lily-nemotron` (class `Nemotron`, T4) with `score_guess` + `moderate`. Deploy
with `.venv/bin/modal deploy modal_app/nemotron.py`; smoke `.venv/bin/modal run …`. Keep
its app name distinct from Gemma's `forgotten-lily` or deploys clobber each other.

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
- [x] **3.1** Modal account/CLI auth; persistent **Volume** for weights.
  - DoD: `modal token` set; empty volume created.
- [x] **3.2** **Gemma 4 12B** GGUF Q4_K_M via `llama-cpp-python` on A10G; download-to-volume on first run.
  - DoD: warm function returns text for a prompt.
- [x] **3.3** Author + iterate **Lily system prompt** — enforces tone-only output, respects `active_tones`, emits the JSON contract, stays in character.
  - DoD: 10/10 test prompts return schema-valid JSON using only active tones.
- [x] **3.4** Swap mock → Modal in gr.Server (keep mock behind a flag for offline dev).
  - DoD: vertical slice runs on real Gemma; `USE_MOCK=1` still works.
- [x] **3.5** Robustness: JSON repair/validation, retry, fallback to a safe in-character tone (`◇ —`) on malformed output.
  - DoD: malformed model output never crashes a turn.

## Phase 4 — Notes / Evidence Board
- [x] **4.1** Write all note bodies (now **15**: original 10 + N11–N15 backstory — divorce,
  voicemail, counseling, unsent letter, friend). Each has `found` provenance, `hint`,
  `summary`/`order`. **Visual asset images NOT made** — cards are text-only (see backlog).
  - DoD: each note renders with intended "read twice" content. ✓ (text)
- [x] **4.2** Evidence board UI (Tailwind): kraft cards, seeded rotation, red pushpin, pin-drop
  animation, per-type icons, NEW badge/glow, provenance + hint lines, Evidence/Her-Story tabs.
  - DoD: notes appear as designed; rotation stable across reloads. ✓
- [x] **4.3** Unlock engine: threshold + topic + **empathy** → reveal note. N10 flat/center, unpinned.
  - DoD: art→N02; threshold→N03; family→N11; empathy→N15/N12; finale reveals N10. ✓
  - Note: `topic_signal` now includes `family` (+ server-side `FAMILY_CUES` fallback).

## Phase 5 — Lexicon + Nemotron Scoring
- [x] **5.1** Lexicon drawer (now a **left sidebar**): glyph, category tag, "heard N×",
  guess field + ↵/Enter save, color confidence bar, evidence `hint` line; locked tones as `?`.
  - DoD: drawer opens, guesses persist, conversation stays scrollable while open. ✓
- [x] **5.2** **Nemotron-Mini 4B** on Modal (T4) — semantic scoring of a guess vs the
  tone's **true meaning** (from `tones.json`, never shown) → {red/amber/teal/green}.
  Server `/api/guess` routes here when `USE_MOCK=0`; mock token-overlap stays for offline.
  - DoD: correct→green, wrong→red, synonyms→green (e.g. "myself"→self_i, "scared"→afraid);
    color only, no numbers. ✓ smoke test PASS (0 unexpected) + live client-wrapper check.
  - **Deploy gotcha (fixed):** Nemotron now lives in its OWN Modal app
    `forgotten-lily-nemotron` — it previously shared `forgotten-lily` with Gemma, so each
    `modal deploy` clobbered the other's class. Both apps now coexist; redeploy each from
    its own file. Also: `apply_chat_template` needs `return_dict=True` + `generate(**inputs)`
    on this transformers version (a bare tensor crashes). Scoring keys off the true meaning,
    NOT the detective's questions (questions don't reveal a symbol's meaning → all-amber).
- [x] **5.3** Retroactive chip updates: saving a guess updates all past chips (`refreshChips`),
  reveals the guess on hover, and marks decoded chips with a corner dot. ✓
  - (Confidence still from the token-overlap mock until 5.2 lands.)

## Phase 6 — Moderation + Input Edge Cases
- [ ] **6.1** Nemotron dual-role: harmful input → Lily plays `∅`, journal line *"She doesn't respond to that."* (PLAN §8.2).
  - DoD: harmful input never errors, never breaks fiction.
- [ ] **6.2** Off-topic input → `◇ —`, journal *"She seems to have drifted somewhere."* (§8.3).
  - DoD: irrelevant input handled diegetically.

## Phase 7 — Atmosphere + Ending
- [x] ~~**7.1** Background ambient piano + duck during tones~~ — **REMOVED by design**
  (felt wrong; only the tones make sound now). `tones/ambient.py` is now unused.
- [ ] **7.2** Act-based color-temperature transitions via Tailwind CSS vars (warm → gray-amber →
  cold mono). (Music EQ per act dropped — no ambient music anymore.)
  - DoD: visible color drift across acts. (Palette vars exist on `body[data-act]`; verify the
    transition reads clearly Act I→II→III.)
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

## Backlog — polish & verify (from the core-loop / content pass)
Things deliberately deferred or worth a second look later:
- [ ] **Live prompt verification** — confirm on real Gemma that the P2 fix cured the
  `emo_happy`/`internal_emotion="curious"` overuse across Acts II/III (only smoke-tested).
- [ ] **Empathy tuning** — playtest thresholds (N15=2 … N14=5) and the empathy/personal
  keyword lists; make sure caring players actually reach the deeper notes, non-caring don't.
- [ ] **Hint balance** — the lexicon `hint` text should nudge, not give away; review wording.
- [ ] **Note visual assets** — cards are text-only. PLAN §7.3 wanted designed artifacts
  (text-thread screenshot, sketchbook, forms, photo). Decide: keep text (clean, shippable)
  or generate/source images and render them. Icons currently stand in for type.
- [ ] **N10 / total-tones gate** — N10 needs all 24 tones *seen*; with the Act I widening,
  reconfirm a full playthrough actually surfaces all 24 before the finale can fire.
- [ ] **Story tab ordering** — narrative is sequenced by note `order`; reread the assembled
  text once all 15 are found to ensure it flows as one coherent arc.
- [ ] **Empathy → Nemotron** — replace the keyword heuristic with the Nemotron classifier
  when Phase 6 lands (richer, fewer false negatives).
- [ ] **Mobile / narrow layout** — the left lexicon sidebar + 2-col grid + tabs need a
  responsive pass (Phase 9.3).

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
