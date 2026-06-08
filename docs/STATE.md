# Game State Machine

Deterministic rules the server enforces per session. Derived from PLAN §4 and §6.3.
The model never decides act transitions — the server does, from these rules.

## Session state object
```json
{
  "session_id": "uuid",
  "turn": 0,
  "act": 1,
  "tones_seen_count": {},    // tone id -> times Lily has emitted it (tones_seen = its keys)
  "lexicon": {},             // tone id -> { guess: str, confidence: "red|amber|teal|green" }
  "notes_unlocked": [],      // note ids, in unlock order
  "empathy": 0,              // rises on caring/personal player questions (see below)
  "finale_played": false
}
```

- **lexicon_size** = count of lexicon entries with a non-empty `guess`.
- A tone is "active" this turn if its `act_active <= act` (see `data/tones.json`).
- **Per-act tone cap** (`ACT_TONE_CAP` in `app/game.py`): Lily's reply is trimmed to
  at most {Act I: 3, Act II: 5, Act III: 7} tones, so early phrases stay short and
  decodable. The prompt also asks for the matching count per act.
- **empathy** rises by 1 on any turn whose message hits a caring cue (`EMPATHY_CUES`)
  or a personal-question cue (`PERSONAL_CUES`) — heuristic in `app/game.py`, upgradable
  to Nemotron (Phase 6). Gates the `empathy` evidence notes.

## Tone activation tiers (PLAN 6.3; Act I widened for learnability)
| Tier | Active from | Tones | Count active |
|---|---|---|---|
| Act I start | act 1 | ◈ ◉ △ ∿ ♭ ♮ ← — ∎ □ | 10 |
| Transition + Act II | act 2 | + ◇ ▽ ⌒ ≈ ▣ ◫ ♯ → | 18 |
| Act III | act 3 | + ◻ ↝ ≋ ↑ ↓ ∅ | 24 |

(In `tones.json`: `act_active` is 1, 2, or 3. `time_now` (∿) and `act_stay` (←) were
promoted from Act II to Act I so Lily has enough vocabulary to be coherent early —
she can ground feeling in the present and express intent ("you / stay / now"). The
total still reaches 18 by Act II and 24 by Act III, so the later gates are unchanged.)

## Act transitions
Evaluated after each turn. Forward-only; never regress.

**Act I → Act II** when BOTH:
- `lexicon_size >= 5` (at least 5 lexicon entries — PLAN 4.2), AND
- at least `max(5, len(ACT1_TONES) - 3)` Act-I tones have been seen ≥ 2× (currently
  7 of 10). Relaxed from "every Act-I tone twice" so widening Act I vocabulary doesn't
  stall progression; a couple of rarely-used tones are tolerated.

**Act II → Act III** when BOTH:
- `len(tones_seen) >= 18` (18 of 24 tones seen — PLAN 4.3), AND
- note `N07` (hospital intake form) is unlocked.

**Finale** — within Act III, when `len(tones_seen) == 24` AND `N10` unlocked:
the server may trigger the ending sequence (`special: "finale"`), set
`finale_played = true`. After that, normal input is closed; the ending plays out
(PLAN 4.5).

## Note unlocks (see data/notes.json) — 15 notes
Re-evaluated every turn (`act >= note.act` always required):
- **threshold notes** unlock when `lexicon_size >= unlock_value`.
- **topic notes** unlock when the turn's `topic_signal == note.unlock_value`. Signals:
  `music`, `university`, `relationship`, `hospital_staff`, `family`. The `family` signal
  also has a server-side keyword fallback (`FAMILY_CUES`) when the model misses it.
- **empathy notes** unlock when `empathy >= unlock_value` — the vulnerable backstory
  (friend's statement, mother's voicemail, counseling slip, unsent letter), gated
  behind the detective showing care. Thresholds: N15=2, N12=3, N13=4, N14=5.
- `N10` requires all 24 tones *seen* (`len(tones_seen) == 24`, per PLAN 7.3) — special-cased.

Each note also carries `found` (investigation provenance, shown on the card), an
optional `hint` (`{tone_id, text}` surfaced in the lexicon once that tone is heard —
evidence helps decode the language), and `summary`/`order` (the "Her Story" tab
assembles found summaries into a narrative, sequenced by `order`).

## Atmosphere coupling (Phase 7)
Act drives the UI color temperature (Tailwind CSS vars on `body[data-act]`):
- Act I — warm cream / amber. Act II — gray-amber. Act III — near-monochrome cold.

Note: ambient background music was **removed** by design — only the tones make sound.
The PLAN 6.5 "music EQ shift per act" no longer applies; color temperature is the
remaining act-coupled atmosphere (Phase 7.2).
