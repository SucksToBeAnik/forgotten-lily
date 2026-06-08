"""Core game engine for Forgotten Lily — the authority for state, act
transitions, and note unlocks (see docs/STATE.md). Pure Python, no web/inference
deps so it can be unit-tested in isolation. The server enriches inference
responses through here; the model never decides progression.
"""
import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TONES = json.loads((ROOT / "data" / "tones.json").read_text())
NOTES = json.loads((ROOT / "data" / "notes.json").read_text())

TONE_BY_ID = {t["id"]: t for t in TONES["tones"]}
NOTE_BY_ID = {n["id"]: n for n in NOTES["notes"]}
ACT1_TONES = [t["id"] for t in TONES["tones"] if t["act_active"] == 1]

# Per-act ceiling on how many tones Lily emits per turn. Short, literal phrases
# early make the language learnable; expressive expansion is earned in later acts.
ACT_TONE_CAP = {1: 3, 2: 5, 3: 7}


def new_session():
    return {
        "session_id": str(uuid.uuid4()),
        "turn": 0,
        "act": 1,
        "tones_seen_count": {},   # tone id -> times Lily has emitted it
        "tone_contexts": {},      # tone id -> [player messages where it appeared, max 8]
        "lexicon": {},            # tone id -> {guess, confidence}
        "notes_unlocked": [],     # note ids, in unlock order
        "empathy": 0,             # rises when the detective asks caring/personal questions
        "finale_played": False,
    }


# --- empathy / personal-question detection (heuristic; upgradable to Nemotron) ---
# Caring statements and gentle, personal questions. When the detective shows this
# kind of care, the vulnerable backstory evidence (unlock_type "empathy") opens up.
EMPATHY_CUES = (
    "are you okay", "you okay", "it's okay", "its okay", "not your fault",
    "wasn't your fault", "wasnt your fault", "i'm here", "im here", "i am here",
    "take your time", "you're safe", "youre safe", "you are safe", "i care",
    "i'm sorry", "im sorry", "you matter", "you're not alone", "you are not alone",
    "not alone", "i understand", "i want to help", "let me help", "you can trust",
    "i'm with you", "im with you", "here for you", "i won't leave", "i wont leave",
)
PERSONAL_CUES = (
    "your parents", "your mother", "your mom", "your mum", "your father", "your dad",
    "your family", "your home", "childhood", "grow up", "grew up", "your dream",
    "your dreams", "who were you", "who are you", "tell me about yourself",
    "tell me about you", "your friend", "what do you love", "what makes you happy",
    "what scares you", "what do you fear", "when you were young", "your past",
)
FAMILY_CUES = (
    "parent", "mother", "mom", "mum", "father", "dad", "family", "childhood",
    "grew up", "grow up", "sister", "brother", "divorce", "home",
)


def _has_cue(message, cues):
    m = (message or "").lower()
    return any(c in m for c in cues)


# --- derived helpers ---------------------------------------------------------

def active_tone_ids(act):
    return [t["id"] for t in TONES["tones"] if t["act_active"] <= act]


def tones_seen(state):
    return list(state["tones_seen_count"].keys())


def lexicon_size(state):
    return sum(1 for v in state["lexicon"].values() if v.get("guess", "").strip())


def tone_payload(tone_id):
    """Frontend-facing tone object: glyph, meaning, audio path."""
    t = TONE_BY_ID[tone_id]
    return {
        "id": tone_id,
        "glyph": t["glyph"],
        "category": t["category"],
        "meaning": t["meaning"],
        "audio": f"/static/tones/{tone_id}.wav",
    }


# --- progression -------------------------------------------------------------

def _maybe_advance_act(state):
    """Forward-only act transitions (STATE.md). Returns True if act changed."""
    act = state["act"]
    seen = state["tones_seen_count"]
    if act == 1:
        # tolerate a couple of rarely-used tones so adding Act I vocabulary
        # doesn't stall progression (was: every Act I tone seen twice).
        seen_twice = sum(1 for tid in ACT1_TONES if seen.get(tid, 0) >= 2)
        if lexicon_size(state) >= 5 and seen_twice >= max(5, len(ACT1_TONES) - 3):
            state["act"] = 2
            return True
    elif act == 2:
        if len(seen) >= 18 and "N07" in state["notes_unlocked"]:
            state["act"] = 3
            return True
    return False


def _unlock_notes(state, topic_signal):
    """Re-evaluate every turn. Returns newly unlocked note objects."""
    newly = []
    lex = lexicon_size(state)
    seen_total = len(state["tones_seen_count"])
    for note in NOTES["notes"]:
        if note["id"] in state["notes_unlocked"]:
            continue
        if state["act"] < note["act"]:
            continue
        hit = False
        if note["id"] == "N10":  # special: all 24 tones SEEN (PLAN 7.3)
            hit = seen_total >= 24
        elif note["unlock_type"] == "threshold":
            hit = lex >= note["unlock_value"]
        elif note["unlock_type"] == "topic":
            hit = topic_signal == note["unlock_value"]
        elif note["unlock_type"] == "empathy":
            hit = state["empathy"] >= note["unlock_value"]
        if hit:
            state["notes_unlocked"].append(note["id"])
            newly.append(_note_payload(note))
    return newly


def _note_payload(note):
    return {
        "id": note["id"],
        "title": note["title"],
        "body": note["body"],
        "asset": note["asset"],
        "design": note["design"],
        "found": note.get("found", ""),   # how the investigation surfaced it
        "hint": note.get("hint"),         # {tone_id, text} — nudges a tone's meaning
        "centered": note["id"] == "N10",  # placed flat in the center, not pinned
    }


# --- turn application --------------------------------------------------------

JOURNAL = {
    "silent": "She doesn't respond to that.",
    "drift": "She seems to have drifted somewhere.",
}


def apply_turn(state, inference_response, message=""):
    """Fold a contract response (docs/CONTRACT.md) into session state and build
    the enriched frontend payload. Tones outside the active set are dropped here
    as a final guard even though inference is asked to respect active_tones.
    `message` is the player's line, used for empathy/personal-topic detection."""
    state["turn"] += 1
    active = set(active_tone_ids(state["act"]))

    # empathy rises on caring or personal questions; gates the backstory evidence
    if _has_cue(message, EMPATHY_CUES) or _has_cue(message, PERSONAL_CUES):
        state["empathy"] += 1

    cap = ACT_TONE_CAP.get(state["act"], 7)
    tones = [tid for tid in inference_response.get("tones", []) if tid in active][:cap]
    if not tones:  # never break character; a safe in-character "drift"
        tones = [tid for tid in ("self_remember", "truth_pause") if tid in active] or [ACT1_TONES[0]]

    tone_ctxs = state.setdefault("tone_contexts", {})
    for tid in tones:
        state["tones_seen_count"][tid] = state["tones_seen_count"].get(tid, 0) + 1
        if message:
            ctxs = tone_ctxs.setdefault(tid, [])
            if len(ctxs) < 8:
                ctxs.append(message[:280])

    topic = inference_response.get("topic_signal")
    if topic not in NOTES["topic_signals"]:
        topic = None
    if topic is None and _has_cue(message, FAMILY_CUES):  # server-side family fallback
        topic = "family"

    newly = _unlock_notes(state, topic)
    act_changed = _maybe_advance_act(state)
    # a transition may itself open threshold notes gated behind the new act
    if act_changed:
        newly += _unlock_notes(state, None)

    special = inference_response.get("special")
    return {
        "tones": [tone_payload(t) for t in tones],
        "journal_line": JOURNAL.get(special),
        "internal_emotion": inference_response.get("internal_emotion", ""),
        "special": special,
        "topic_signal": topic,
        "act": state["act"],
        "act_changed": act_changed,
        "notes_unlocked": newly,
        "turn": state["turn"],
        "tones_seen": len(state["tones_seen_count"]),
        "lexicon_size": lexicon_size(state),
        "finale": special == "finale",
    }


# --- lexicon scoring (mock; real Nemotron lands in Phase 5) ------------------

def score_guess(tone_id, guess):
    """Placeholder semantic scorer -> red|amber|teal|green. Token overlap between
    the guess and the tone's true meaning. Replaced by Nemotron in Phase 5.2."""
    guess = (guess or "").lower().strip()
    if not guess:
        return "red"
    truth = TONE_BY_ID[tone_id]["meaning"].lower()
    stop = {"the", "a", "an", "of", "to", "is"}
    truth_tokens = {w for w in truth.replace("/", " ").split() if len(w) >= 2 and w not in stop}
    guess_tokens = {w for w in guess.replace("/", " ").split() if len(w) >= 2 and w not in stop}
    if not truth_tokens:
        return "amber"
    overlap = len(truth_tokens & guess_tokens) / len(truth_tokens)
    # synonym nudge so the slice feels alive without a real model
    if overlap == 0 and any(g in truth or truth_word in guess
                            for g in guess_tokens for truth_word in truth_tokens):
        overlap = 0.5
    if overlap >= 0.99:
        return "green"
    if overlap >= 0.5:
        return "teal"
    if overlap > 0:
        return "amber"
    return "red"


def set_guess(state, tone_id, guess):
    if tone_id not in TONE_BY_ID:
        return None
    conf = score_guess(tone_id, guess)
    state["lexicon"][tone_id] = {"guess": guess, "confidence": conf}
    return {"tone_id": tone_id, "guess": guess, "confidence": conf}


def _hints_from_found_notes(state):
    """tone_id -> hint text, gathered from every evidence note already unlocked.
    This is how evidence helps the player decode the lexicon."""
    hints = {}
    for nid in state["notes_unlocked"]:
        h = NOTE_BY_ID.get(nid, {}).get("hint")
        if h and h["tone_id"] not in hints:
            hints[h["tone_id"]] = h["text"]
    return hints


def lexicon_view(state):
    """Full lexicon for the drawer: every tone the player has SEEN, plus counts
    of locked/remaining. Unseen tones are returned as locked placeholders. Seen
    tones carry any hint unlocked by found evidence."""
    seen = state["tones_seen_count"]
    hints = _hints_from_found_notes(state)
    entries = []
    for t in TONES["tones"]:
        tid = t["id"]
        if tid in seen:
            lx = state["lexicon"].get(tid, {})
            entries.append({
                "id": tid, "glyph": t["glyph"], "category": t["category"],
                "seen": seen[tid], "locked": False, "hint": hints.get(tid),
                "guess": lx.get("guess", ""), "confidence": lx.get("confidence", "red"),
            })
        else:
            entries.append({"id": tid, "glyph": "?", "category": t["category"],
                            "seen": 0, "locked": True, "guess": "", "confidence": None})
    return {
        "entries": entries,
        "total": len(TONES["tones"]),
        "discovered": len(seen),
        "act": state["act"],
    }


def story_view(state):
    """The 'Her Story' tab: a narrative assembled from the summary fragments of
    every evidence note found so far, sequenced by each note's `order`."""
    found = set(state["notes_unlocked"])
    frags = [
        {"id": n["id"], "title": n["title"],
         "summary": n.get("summary", ""), "order": n.get("order", 999)}
        for n in NOTES["notes"] if n["id"] in found and n.get("summary")
    ]
    frags.sort(key=lambda f: f["order"])
    return {"fragments": frags, "found": len(found), "total": len(NOTES["notes"])}
