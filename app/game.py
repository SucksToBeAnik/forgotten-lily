"""Core game engine for Forgotten Lily — the authority for state, act
transitions, and note unlocks (see docs/STATE.md). Pure Python, no web/inference
deps so it can be unit-tested in isolation. The server enriches inference
responses through here; the model never decides progression.
"""
import json
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TONES = json.loads((ROOT / "data" / "tones.json").read_text())
NOTES = json.loads((ROOT / "data" / "notes.json").read_text())

TONE_BY_ID = {t["id"]: t for t in TONES["tones"]}
NOTE_BY_ID = {n["id"]: n for n in NOTES["notes"]}
TOTAL_TONES = len(TONES["tones"])
ACT1_TONES = [t["id"] for t in TONES["tones"] if t["act_active"] == 1]
# Act-1 tones drive the act-advance gate. (There are no longer any Link/connective
# tones to exclude — the language is all content words now; PLAN 6.1 redesign.)
ACT1_CONTENT = [t["id"] for t in TONES["tones"] if t["act_active"] == 1]

# Per-act ceiling on how many tones Lily emits per turn. Short, literal phrases
# early make the language learnable; expressive expansion is earned in later acts.
ACT_TONE_CAP = {1: 4, 2: 5, 3: 7}

# Lily's grammar, as a canonical reading order. Gemma chooses WHICH tones she says;
# the engine sorts them into this order so chips read as a coherent phrase ("I feel
# sad") instead of a bag of words ("sad feel I"). With the Link connectives removed,
# this ordering is unambiguous, so we apply it to EVERY reply (see _order_tones /
# apply_turn). Lower = earlier; unknown ids sort last; the finale ships its own order.
GRAMMAR_ORDER = {
    "truth_yes": 0, "truth_no": 0,                                          # answer first
    "self_i": 1,                                                            # subject
    "self_feel": 2, "self_remember": 2, "self_forget": 2,                   # inner verbs
    "emo_love": 3, "emo_happy": 3, "emo_sad": 3, "emo_afraid": 3, "emo_tired": 3,  # emotion
    "act_want": 4, "act_go": 4, "act_stay": 4, "act_fall": 4,               # action
    "other_you": 5, "other_him": 5, "other_us": 5, "other_world": 5,        # people
    "family": 5, "music": 5,                                                # & things
    "time_now": 6, "time_before": 6, "time_after": 6,                       # time
    "truth_nothing": 8,                                                     # the end
}


def _order_tones(tone_ids):
    """Sort Lily's chosen tones into her grammar (stable). Unknown ids sort last.
    Applied to every non-finale reply now that there are no connectives to place."""
    return sorted(tone_ids, key=lambda t: GRAMMAR_ORDER.get(t, 50))


# Lily's mood persists across turns instead of being re-rolled each reply (which
# made her flip warm→heavy→warm and feel disconnected). It is anchored to a per-act
# baseline (PLAN act registers: hope → unease → release) and carried forward each
# turn — derived from the emotion tone she actually voiced (more reliable than the
# model's internal_emotion field), or held steady when she voices none. The mood is
# fed back into the model so it colors WITHIN the current feeling. It will also drive
# the melodic key/mode once the musician pivot lands. See [[design-pivot-musician]].
ACT_BASELINE_MOOD = {1: "warm", 2: "wistful", 3: "releasing"}
EMOTION_TONE_MOOD = {
    "emo_happy": "light", "emo_sad": "heavy",
    "emo_afraid": "afraid", "emo_love": "tender", "emo_tired": "weary",
}


def new_session():
    return {
        "session_id": str(uuid.uuid4()),
        "turn": 0,
        "act": 1,
        "tones_seen_count": {},   # tone id -> times Lily has emitted it
        "tone_contexts": {},      # tone id -> [player messages where it appeared, max 8]
        "lexicon": {},            # tone id -> {guess, confidence}
        "notes_unlocked": [],     # note ids, in unlock order
        "empathy": 0,             # meter 0..EMPATHY_METER_MAX; each fill reveals a memory, then resets
        "empathy_counted": [],    # fingerprints of caring questions already counted (anti-farm)
        "mood": ACT_BASELINE_MOOD[1],  # persistent emotional state, carried across turns
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
TRAVEL_CUES = (
    "travel", "trip", "journey", "world", "fuji", "mountain", "japan", "abroad",
    "passport", "escape", "go somewhere", "leave", "away", "see the world",
    "places", "dream", "wander", "explore", "graduate", "after you graduate",
)


def _has_cue(message, cues):
    m = (message or "").lower()
    return any(c in m for c in cues)


# --- empathy meter -----------------------------------------------------------
# Caring/personal questions fill a meter; each FULL meter surfaces one of her more
# private memories, then resets. The empathy notes are revealed in the order their
# author intended (their old unlock_value doubled as a sequence), act-gated so the
# act-3 one can't appear early. These memories are off the critical path to the
# ending, so the meter can be a meatier optional thread.
EMPATHY_METER_MAX = 3
EMPATHY_NOTES = sorted(
    (n for n in NOTES["notes"] if n["unlock_type"] == "empathy"),
    key=lambda n: n["unlock_value"],
)
# Kept small on purpose: only truly contentless glue. Stripping too much (e.g.
# "okay") would collapse a real caring question like "are you okay?" to nothing.
_STOP_WORDS = {"a", "an", "the", "is", "are", "do", "did", "to", "of", "you",
               "your", "i", "it", "that", "this"}


def _empathy_fingerprint(message):
    """A stable signature for a caring question so repeats/rewordings of the SAME
    question don't farm the meter. Significant words, lowercased, deduped, sorted —
    so 'are you okay' and 'you okay?' collapse to one fingerprint. Falls back to the
    full word set if stripping leaves nothing, so a question never becomes empty."""
    words = re.sub(r"[^a-z0-9 ]", " ", (message or "").lower()).split()
    sig = sorted({w for w in words if w not in _STOP_WORDS})
    return " ".join(sig or sorted(set(words)))


# --- derived helpers ---------------------------------------------------------

def active_tone_ids(act):
    return [t["id"] for t in TONES["tones"] if t["act_active"] <= act]


def _coverage_order(act):
    """The order in which we reveal any active tones the player hasn't heard yet:
    gentler/common tones first, the final-feeling ∅ (truth_nothing) held for last so
    'nothing / the end' is the last word she teaches — right before the ending."""
    ids = active_tone_ids(act)
    ids.sort(key=lambda t: (TONE_BY_ID[t]["act_active"],
                            t == "truth_nothing",
                            GRAMMAR_ORDER.get(t, 50)))
    return ids


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
    turn = state["turn"]
    if act == 1:
        # coverage guarantees each Act I content tone is heard at least once; tolerate
        # one straggler. Advance when the player has decoded a few (the intended gate),
        # OR — as a safety net so no one stalls — after enough turns regardless.
        heard = sum(1 for tid in ACT1_CONTENT if seen.get(tid, 0) >= 1)
        enough_vocab = heard >= len(ACT1_CONTENT) - 1
        if enough_vocab and (lexicon_size(state) >= 5 or turn >= 14):
            state["act"] = 2
            return True
    elif act == 2:
        # coverage drives `seen` toward the full Act II set (21 tones). Advance on the
        # intended gate (wide vocabulary + the travel-fund note), OR via the turn valve.
        wide = len(seen) >= 18
        if wide and ("N07" in state["notes_unlocked"] or turn >= 28):
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
        if note["unlock_type"] == "empathy":
            continue  # empathy memories are surfaced by the meter, not here
        hit = False
        if note["id"] == "N10":  # special: every tone SEEN (PLAN 7.3)
            hit = seen_total >= TOTAL_TONES
        elif note["unlock_type"] == "threshold":
            hit = lex >= note["unlock_value"]
        elif note["unlock_type"] == "topic":
            hit = topic_signal == note["unlock_value"]
        if hit:
            state["notes_unlocked"].append(note["id"])
            newly.append(_note_payload(note))
    return newly


def _unlock_empathy_notes(state):
    """Spend full meters: while the meter is full AND an empathy memory is eligible
    (its act has been reached and it isn't already found), surface the next one and
    drain a meter's worth. Runs every turn, so a meter left full in Act II releases
    its act-III memory the moment the act advances."""
    newly = []
    while state["empathy"] >= EMPATHY_METER_MAX:
        nxt = next((n for n in EMPATHY_NOTES
                    if n["id"] not in state["notes_unlocked"] and state["act"] >= n["act"]),
                   None)
        if nxt is None:
            break
        state["notes_unlocked"].append(nxt["id"])
        newly.append(_note_payload(nxt))
        state["empathy"] -= EMPATHY_METER_MAX  # reset for the next memory
    return newly


def _note_payload(note):
    return {
        "id": note["id"],
        "title": note["title"],
        "body": note["body"],
        "asset": note["asset"],
        "design": note["design"],
        "found": note.get("found", ""),   # how the investigation surfaced it
        "prompts": note.get("prompts", []),  # helping questions: nudge the player's next move
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

    # empathy meter fills on caring/personal questions — but only on a question she
    # hasn't already been asked (so the same question can't be repeated to farm it).
    if _has_cue(message, EMPATHY_CUES) or _has_cue(message, PERSONAL_CUES):
        fp = _empathy_fingerprint(message)
        counted = state.setdefault("empathy_counted", [])
        if fp and fp not in counted:
            counted.append(fp)
            state["empathy"] = min(state["empathy"] + 1, EMPATHY_METER_MAX)

    cap = ACT_TONE_CAP.get(state["act"], 7)
    raw = inference_response.get("tones", [])
    if inference_response.get("special") == "finale":
        # the finale is a hand-authored sequence (PLAN 4.4): play it in full — uncapped,
        # in the authored order, and never trimmed by act-gating or grammar reordering.
        tones = list(raw)
    else:
        tones = [tid for tid in raw if tid in active][:cap]
        if not tones:  # never break character; a safe in-character "drift"
            tones = [tid for tid in ("self_feel", "self_i") if tid in active] or [ACT1_TONES[0]]
        # render in Lily's grammar so the phrase reads as a coherent clause
        tones = _order_tones(tones)

        # GUARANTEED COVERAGE — the reachability backbone. Progression gates key off
        # tones SEEN (Act II→III needs ≥18; the ending's N10 needs all of them), but the
        # model alone may never emit some tones. So if this turn revealed nothing new
        # and unseen active tones remain, she surfaces one — gradually teaching her
        # whole vocabulary. This makes the ending reachable no matter what the model says.
        seen = state["tones_seen_count"]
        if not any(t not in seen for t in tones):
            unseen = [t for t in _coverage_order(state["act"]) if t not in seen and t not in tones]
            if unseen:
                tones = _order_tones(tones + [unseen[0]])  # weave the teach-reveal into the phrase

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
    if topic is None and _has_cue(message, TRAVEL_CUES):  # server-side travel fallback
        topic = "travel"

    newly = _unlock_notes(state, topic)
    newly += _unlock_empathy_notes(state)  # spend any full meter (respects the current act)
    act_changed = _maybe_advance_act(state)
    # a transition may itself open threshold notes gated behind the new act, and may
    # release an empathy memory that was waiting on the act
    if act_changed:
        newly += _unlock_notes(state, None)
        newly += _unlock_empathy_notes(state)

    # carry Lily's mood forward: take the emotion she actually voiced this turn;
    # otherwise hold steady (continuity), snapping to the new baseline on a transition.
    voiced = next((EMOTION_TONE_MOOD[t] for t in tones if t in EMOTION_TONE_MOOD), None)
    if voiced:
        state["mood"] = voiced
    elif act_changed:
        state["mood"] = ACT_BASELINE_MOOD[state["act"]]

    special = inference_response.get("special")
    return {
        "tones": [tone_payload(t) for t in tones],
        "journal_line": JOURNAL.get(special),
        "internal_emotion": inference_response.get("internal_emotion", ""),
        "mood": state["mood"],
        "special": special,
        "topic_signal": topic,
        "act": state["act"],
        "act_changed": act_changed,
        "notes_unlocked": newly,
        "empathy": state["empathy"],          # current meter fill (0..max)
        "empathy_max": EMPATHY_METER_MAX,
        "turn": state["turn"],
        "tones_seen": len(state["tones_seen_count"]),
        "total_tones": TOTAL_TONES,
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


def lexicon_view(state):
    """Full lexicon for the drawer: every tone the player has SEEN, plus counts
    of locked/remaining. Unseen tones are returned as locked placeholders."""
    seen = state["tones_seen_count"]
    entries = []
    for t in TONES["tones"]:
        tid = t["id"]
        if tid in seen:
            lx = state["lexicon"].get(tid, {})
            entries.append({
                "id": tid, "glyph": t["glyph"], "category": t["category"],
                "seen": seen[tid], "locked": False,
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


def artifacts_view(state):
    """The 'Her Things' tab: the personal objects behind each piece of evidence,
    each with a line on what it means to her. Populates as notes are found, in the
    order they surfaced (state['notes_unlocked'] is append-ordered)."""
    items = []
    for nid in state["notes_unlocked"]:
        note = NOTE_BY_ID.get(nid, {})
        art = note.get("artifact")
        if art:
            items.append({
                "id": nid,
                "name": art.get("name", note.get("title", "")),
                "icon": art.get("icon", "✦"),
                "relation": art.get("relation", ""),
            })
    total = sum(1 for n in NOTES["notes"] if n.get("artifact"))
    return {"items": items, "found": len(items), "total": total}
