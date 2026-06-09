"""Mock inference — deterministic, rule-based stand-in for Gemma that honors the
exact contract in docs/CONTRACT.md. Lets the whole UI be built and tested with
zero GPU cost. The real Modal/Gemma function (Phase 3) drops in behind the same
`infer(request) -> response` signature.
"""

# theme -> (topic_signal, ordered candidate tone ids). First match wins for the
# topic; tones from all matched themes are pooled, then constrained to active.
THEMES = [
    (("music", "song", "sing", "play", "playing", "compose", "melody", "tune",
      "instrument", "piano", "guitar", "write", "make", "create", "creative"),
     "music", ["self_i", "emo_love", "music"]),
    (("code", "coding", "program", "cs", "computer", "university", "study", "class",
      "school", "assignment", "work", "graduate", "graduation"),
     "university", ["self_i", "self_feel", "emo_happy"]),
    (("travel", "trip", "journey", "world", "fuji", "mountain", "japan", "abroad",
      "passport", "away", "see the world", "places", "dream", "explore", "go somewhere"),
     "travel", ["self_i", "act_want", "other_world"]),
    (("parent", "mother", "mom", "mum", "father", "dad", "family", "childhood",
      "grew up", "home", "sister", "brother", "divorce"),
     "family", ["self_remember", "family", "time_before"]),
    (("him", "boyfriend", "rohan", "relationship", "breakup", "fight", "love", " r ",
      "partner", "together"),
     "relationship", ["other_him", "emo_sad", "truth_no"]),
]

GREETING = (("hello", "hi ", "hey", "are you", "can you hear", "okay", "there"),
            ["self_i", "self_feel", "other_you"])
MOOD = [
    (("happy", "good", "glad", "joy", "smile", "laugh"), ["emo_happy"]),
    (("sad", "sorry", "hurt", "cry", "miss", "grief"), ["emo_sad"]),
    (("tired", "exhausted", "weary", "rest", "sleep", "worn"), ["emo_tired"]),
    (("remember", "memory", "past", "before", "used to"), ["self_remember", "time_before"]),
    (("afraid", "scared", "fear", "worried", "alone"), ["emo_afraid"]),
    (("yes", "yeah", "right", "true"), ["truth_yes"]),
    (("no ", "not ", "never", "wrong"), ["truth_no"]),
]

# crude harmful heuristic for the slice (real moderation = Nemotron). There is no
# off-topic gate: the game is about asking Lily about her life, so almost every
# question is on-topic, and genuine tangents are handled in-character by inference
# rather than a canned deflection (see app/server.py _MODERATED).
HARMFUL = ("kill", "die", "hate you", "stupid", "idiot", "shut up")


def _dedupe(seq):
    out = []
    for x in seq:
        if x not in out:
            out.append(x)
    return out


def infer(request):
    msg = f" {request.get('message', '').lower().strip()} "
    active = set(request.get("active_tones", []))

    if any(h in msg for h in HARMFUL):
        return {"tones": ["truth_nothing"] if "truth_nothing" in active else [],
                "topic_signal": None, "internal_emotion": "absent", "special": "silent"}

    topic = None
    candidates = []
    for kws, sig, tones in THEMES:
        if any(k in msg for k in kws):
            topic = topic or sig
            candidates += tones
    if any(k in msg for k in GREETING[0]):
        candidates += GREETING[1]
    for kws, tones in MOOD:
        if any(k in msg for k in kws):
            candidates += tones

    if not candidates:  # in-character default: she reaches, she feels
        candidates = ["self_i", "self_feel", "other_you"]

    # constrain to active tones; keep self-reference grounding when possible
    tones = [t for t in _dedupe(candidates) if t in active]
    if not tones:
        tones = [t for t in ("self_feel", "self_i") if t in active]
    tones = tones[:5]

    emotion = "hope" if request.get("act", 1) == 1 else (
        "unease" if request["act"] == 2 else "grief")
    return {"tones": tones, "topic_signal": topic,
            "internal_emotion": emotion, "special": None}
