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
| `tones` | `string[]` | Tone `id`s, in playback order. 1–7 tones. All must be in `active_tones`. |
| `topic_signal` | `string \| null` | One of `data/notes.json` `topic_signals` (`art`, `university`, `relationship`, `hospital_staff`) or `null`. Drives topic note unlocks. |
| `internal_emotion` | `string` | Free tag for telemetry + atmosphere (e.g. `hope`, `unease`, `grief`). Never shown raw. |
| `special` | `string \| null` | Reserved control signal. `null` normally. Values: `"silent"` (harmful input → play `truth_nothing` only), `"drift"` (off-topic → `self_remember`+`truth_pause`), `"finale"` (Act III ending sequence). |

The server is the authority on glyph rendering: it maps each tone `id` →
`{glyph, meaning, audio file}` via `tones.json`. The model only ever speaks in `id`s.

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

## Robustness (impl note for Phase 3.5)
Real Gemma output is repaired before it reaches the frontend:
1. Parse JSON; on failure, extract first `{...}` block.
2. Drop any tone not in `active_tones`; cap at 7.
3. If `tones` ends up empty, fall back to `["self_remember", "truth_pause"]` (a safe, in-character "drift").
4. Coerce `topic_signal` to `null` if not a known signal.

A malformed model response must NEVER crash a turn or break character.
