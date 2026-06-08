# Game State Machine

Deterministic rules the server enforces per session. Derived from PLAN §4 and §6.3.
The model never decides act transitions — the server does, from these rules.

## Session state object
```json
{
  "session_id": "uuid",
  "turn": 0,
  "act": 1,
  "tones_seen": [],          // tone ids Lily has emitted at least once
  "lexicon": {},             // tone id -> { guess: str, confidence: "red|amber|teal|green" }
  "notes_unlocked": [],      // note ids
  "finale_played": false
}
```

- **lexicon_size** = count of lexicon entries with a non-empty `guess`.
- A tone is "active" this turn if its `act_active <= act` (see `data/tones.json`).

## Tone activation tiers (PLAN 6.3)
| Tier | Active from | Tones | Count active |
|---|---|---|---|
| Act I start | act 1 | ◈ ◉ △ ♭ ♮ ∎ □ — | 8 |
| Transition + Act II | act 2 | + ◇ ▽ ⌒ ≈ ▣ ◫ ∿ ♯ → ← | 18 |
| Act III | act 3 | + ◻ ↝ ≋ ↑ ↓ ∅ | 24 |

(In `tones.json`: `act_active` is 1, 2, or 3. There is no separate "transition"
act — the four transition tones and the six Act II tones both carry `act_active: 2`,
giving 18 active in Act II, matching "18 of 24" in PLAN 4.3.)

## Act transitions
Evaluated after each turn. Forward-only; never regress.

**Act I → Act II** when BOTH:
- `lexicon_size >= 5` (at least 5 lexicon entries — PLAN 4.2), AND
- every Act-I tone (the 8 with `act_active == 1`) has been seen at least twice.

(Tracking "seen twice" needs a per-tone counter; extend `tones_seen` to a count map
`tones_seen_count: {id: n}` and derive `tones_seen` from its keys.)

**Act II → Act III** when BOTH:
- `len(tones_seen) >= 18` (18 of 24 tones seen — PLAN 4.3), AND
- note `N07` (hospital intake form) is unlocked.

**Finale** — within Act III, when `len(tones_seen) == 24` AND `N10` unlocked:
the server may trigger the ending sequence (`special: "finale"`), set
`finale_played = true`. After that, normal input is closed; the ending plays out
(PLAN 4.5).

## Note unlocks (see data/notes.json)
Re-evaluated every turn:
- **threshold notes** unlock when `lexicon_size >= unlock_value` AND `act >= note.act`.
- **topic notes** unlock when the turn's `topic_signal == note.unlock_value` AND `act >= note.act`.
- `N10` is the only `unlock_value: 24` threshold note and requires all 24 tones *seen*
  (use `len(tones_seen) == 24`, not lexicon_size, per PLAN 7.3) — special-cased.

## Atmosphere coupling (Phase 7)
Act drives the UI color temperature + music EQ:
- Act I — warm cream / amber, ambient piano warm.
- Act II — gray-amber, music half-key lower & slower.
- Act III — near-monochrome cold, music fades out and does not return.
