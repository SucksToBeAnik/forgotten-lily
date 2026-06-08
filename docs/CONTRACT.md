# Inference Contract — Gemma ↔ Frontend

The single source of truth for the data crossing between the game server and the
inference layer. Both `app/mock_inference.py` and the real Modal/Gemma function
MUST honor this exactly. Everything downstream (chips, audio, notes, lexicon) keys
off these shapes.

---

## Turn request — server → inference

```json
{
  "session_id": "uuid",
  "message": "what do you remember about him?",
  "turn": 14,
  "act": 2,
  "mood": "wistful",
  "active_tones": ["self_i", "self_feel", "other_you", "emo_happy", "emo_sad",
                   "truth_yes", "truth_no", "truth_pause", "self_remember",
                   "other_him", "time_before", "emo_love"],
  "lexicon_state": {
    "self_i": "me",
    "other_him": "the boy",
    "emo_sad": "hurt"
  }
}
```

- `active_tones` — tone `id`s usable this act (from `data/tones.json` `act_active <= act`).
  Lily MUST NOT emit a tone outside this list.
- `lexicon_state` — the player's current guesses (id → guess text). Passed for
  context/telemetry; Lily does not "know" these.
- `mood` — Lily's carried emotional state (`warm|wistful|releasing` baseline per act,
  or `light|heavy|afraid|tender` from the emotion she last voiced). The model stays
  within it so her feeling persists across turns instead of flip-flopping. The server
  owns mood (in `game.apply_turn`); the response's `mood` field echoes the updated value.

## Turn response — inference → server

```json
{
  "tones": ["self_i", "self_remember", "other_him", "emo_sad"],
  "topic_signal": "relationship",
  "internal_emotion": "grief",
  "special": null
}
```

| Field | Type | Notes |
|---|---|---|
| `tones` | `string[]` | Tone `id`s, in playback order. All must be in `active_tones`. Asked to use {Act I: 1–3, Act II: 1–5, Act III: 1–6} per the act register; the server hard-trims to `ACT_TONE_CAP` (3/5/7) regardless. |
| `topic_signal` | `string \| null` | One of `data/notes.json` `topic_signals` (`music`, `university`, `relationship`, `hospital_staff`, `family`) or `null`. Drives topic note unlocks. |
| `internal_emotion` | `string` | Free tag for telemetry + atmosphere (e.g. `hope`, `unease`, `grief`). Never shown raw. |
| `special` | `string \| null` | Reserved control signal. `null` normally. Values: `"silent"` (harmful input → play `truth_nothing` only), `"drift"` (off-topic → `self_remember`+`truth_pause`), `"finale"` (Act III ending sequence). |

The server is the authority on glyph rendering: it maps each tone `id` →
`{glyph, meaning, audio file}` via `tones.json`. The model only ever speaks in `id`s.

**Empathy is NOT part of this contract.** The "rapport" that gates the backstory
evidence is detected server-side from the player's message (caring / personal-question
keywords in `app/game.py`), not by the model. Likewise the `family` topic has a
server-side keyword fallback, so it fires even when Gemma returns `null`.
`internal_emotion` should match the tones chosen (the model is told not to park on
"curious"), but the server does not depend on it for progression.

---

## Worked examples

### 1. Act I — greeting (`act: 1`)
Player: *"hello? can you hear me?"*
```json
{ "tones": ["self_i", "self_feel", "other_you"], "topic_signal": null,
  "internal_emotion": "reaching", "special": null }
```
Reads as: *I / feel / you* — she senses someone is there.

### 2. Off-topic input (any act)
Player: *"what's the weather like today lol"*
```json
{ "tones": ["self_remember", "truth_pause"], "topic_signal": null,
  "internal_emotion": "withdrawn", "special": "drift" }
```
Server appends journal line: *"She seems to have drifted somewhere."* (PLAN 8.3)

### 3. Harmful input (any act)
```json
{ "tones": ["truth_nothing"], "topic_signal": null,
  "internal_emotion": "absent", "special": "silent" }
```
Server appends journal line: *"She doesn't respond to that."* (PLAN 8.2)
Note: harmful classification is decided by Nemotron moderation upstream; the
server may set `special: "silent"` itself and skip Gemma entirely.

### 4. Act III — the finale (`act: 3`, triggered by server, not free input)
```json
{ "tones": ["self_i", "act_fall", "self_remember", "other_you",
            "emo_happy", "other_him", "truth_no", "truth_nothing"],
  "topic_signal": null, "internal_emotion": "release", "special": "finale" }
```
Reads as: *I / let go / remember — you / happy / him / not / the end* (PLAN 4.4)

---

## Lexicon scoring (Nemotron, Phase 5.2)

A second model — `nvidia/Nemotron-Mini-4B-Instruct`, deployed as its own Modal app
`forgotten-lily-nemotron` (class `Nemotron`, T4) — silently rates the player's guess
for a tone. It is the "silent semantic scorer" (PLAN §2); the player only ever sees a
color, never a number.

**Request** (`POST /api/guess` → `nemotron_inference.score_guess`):
```json
{ "tone_id": "self_i", "guess": "me, myself", "contexts": ["are you there?"] }
```
- `contexts` — the detective lines where this tone was heard (`state.tone_contexts`,
  max 8). Passed for future use; **not** the basis of the judgment.

**Response:** exactly one of `"green" | "teal" | "amber" | "red"`.

**How it scores:** the guess is compared **by sense** against the tone's *true meaning*
(from `data/tones.json`, never shown to the player) — synonyms and paraphrases count
("myself" → `self_i` is green; "scared" → `emo_afraid` is green). This is the value
over the offline token-overlap mock in `game.score_guess`, which misses synonyms.
- `green` = same meaning · `teal` = near-synonym / same idea · `amber` = loosely
  related but off · `red` = unrelated or contradictory · empty guess → `red`.

Scoring is gated by `USE_MOCK`: `USE_MOCK=1` (default) uses the offline mock so the
game runs with zero GPU cost; `USE_MOCK=0` routes guesses to Nemotron. A correct guess
trends `green` across turns, a wrong one stays `red`.

Nemotron also exposes `moderate(message) -> "normal"|"off_topic"|"harmful"` for the
input-moderation path (Phase 6.1/6.2, not yet wired into `/api/turn`).

---

## Robustness (impl note for Phase 3.5)
Real Gemma output is repaired before it reaches the frontend:
1. Parse JSON; on failure, extract first `{...}` block.
2. Drop any tone not in `active_tones`; cap at 7.
3. If `tones` ends up empty, fall back to `["self_remember", "truth_pause"]` (a safe, in-character "drift").
4. Coerce `topic_signal` to `null` if not a known signal.

A malformed model response must NEVER crash a turn or break character.
