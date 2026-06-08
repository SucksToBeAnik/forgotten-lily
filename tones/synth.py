"""Procedural tone synthesis for Forgotten Lily (PLAN 6.4).

Reads data/tones.json and renders one WAV per tone into app/static/tones/.
No neural audio — every tone is a designed, deterministic sound. Run:

    python tones/synth.py            # generate all 24
    python tones/synth.py self_i     # generate one (debug)
    python tones/synth.py --verify   # FFT-check every tone lands on the scale
    python tones/synth.py --demo      # render sample PHRASES (glyphs as melody)

MUSIC (the reason tones combine into something beautiful):
    Every pitched tone sits on ONE shared scale — A minor pentatonic (A C D E G) —
    so any sequence of glyphs is consonant by construction. A tone's pitch is set by
    `note` (a scale step from ROOT=A3): note_to_hz(0)=220, +5 = one octave up, negative
    = down. Bell-like timbres + a reverb tail let notes ring into each other so a reply
    plays like a melody on a music box, not a row of beeps. See data/tones.json.

Audio profile schema (see data/tones.json):
    note      : scale step from ROOT (int) — the musical pitch. null for breath.
    base_freq : resolved Hz (recomputed from `note`; 0 for the pure-noise 'breath')
    waveform  : sine | triangle | saw | square | breath
    duration  : seconds (the dry core; a reverb tail is appended on top)
    harmonics : [a1, a2, a3, ...] amplitudes of harmonic multiples (1x, 2x, 3x...)
    envelope  : bell | pad | swell | fade | pluck | breath
    interval  : null | [semitone offsets]  (chord; arpeggiated only when envelope==pluck)
    mod       : null | {type: tremolo|vibrato|glide|detune, ...}
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 44100
ROOT = Path(__file__).resolve().parent.parent
TONES_JSON = ROOT / "data" / "tones.json"
OUT_DIR = ROOT / "app" / "static" / "tones"
DEMO_DIR = OUT_DIR / "demo"

TARGET_RMS = 0.12      # perceptual loudness target shared across tones
EDGE_FADE_S = 0.008    # anti-click fade on every tone edge

# --- the scale -------------------------------------------------------------
# A minor pentatonic, rooted at A3. `note` in tones.json is a step index into
# this scale; combinations of these pitches are always consonant.
ROOT_HZ = 220.0                  # A3 = step 0
PENTATONIC = [0, 3, 5, 7, 10]    # minor pentatonic semitone degrees (A C D E G)


def note_to_hz(step):
    """Scale step -> Hz. 0=root, +len(PENTATONIC)=octave up, negatives go down."""
    octave, degree = divmod(step, len(PENTATONIC))
    semitones = octave * 12 + PENTATONIC[degree]
    return ROOT_HZ * (2.0 ** (semitones / 12.0))


def _osc(freq_curve, waveform, t):
    """Oscillator that accepts a per-sample frequency curve (enables glide/vibrato)."""
    phase = 2.0 * np.pi * np.cumsum(freq_curve) / SR
    if waveform == "sine":
        return np.sin(phase)
    if waveform == "triangle":
        return signal.sawtooth(phase, width=0.5)
    if waveform == "saw":
        return signal.sawtooth(phase)
    if waveform == "square":
        return signal.square(phase)
    raise ValueError(f"unknown waveform {waveform}")


def _freq_curve(base, n, mod):
    """Constant base frequency, optionally bent by glide/vibrato."""
    f = np.full(n, base, dtype=np.float64)
    if not mod:
        return f
    if mod["type"] == "glide":
        target = base * (2.0 ** (mod["semitones"] / 12.0))
        f = np.linspace(base, target, n)
    elif mod["type"] == "vibrato":
        t = np.arange(n) / SR
        depth_hz = base * (2.0 ** (mod["depth"] / 12.0) - 1.0)
        f = base + depth_hz * np.sin(2.0 * np.pi * mod["rate"] * t)
    return f


def _harmonic_stack(base, harmonics, waveform, n, mod):
    """Sum the fundamental + harmonic multiples."""
    amps = harmonics if harmonics else [1.0]
    out = np.zeros(n)
    for i, amp in enumerate(amps):
        mult = i + 1
        out += amp * _osc(_freq_curve(base * mult, n, mod), waveform, np.arange(n))
    return out / max(sum(amps), 1e-6)


def _envelope(kind, n):
    e = np.ones(n)
    idx = np.arange(n)
    if kind == "bell":         # soft attack, long ringing exponential decay (music box)
        a = max(int(0.01 * n), 1)
        e[:a] = np.linspace(0, 1, a)
        e[a:] = np.exp(-2.4 * (idx[a:] - a) / max(n - a, 1))
    elif kind == "pad":        # gentle attack/sustain/release
        a, r = int(0.15 * n), int(0.20 * n)
        e[:a] = np.linspace(0, 1, a)
        e[n - r:] = np.linspace(1, 0, r)
    elif kind == "swell":      # slow fade-in, soft release
        a, r = int(0.45 * n), int(0.30 * n)
        e[:a] = np.linspace(0, 1, a) ** 1.5
        e[n - r:] = np.linspace(1, 0, r)
    elif kind == "fade":       # quick attack, long exponential decay
        a = int(0.04 * n)
        e[:a] = np.linspace(0, 1, a)
        e[a:] = np.exp(-3.0 * (idx[a:] - a) / max(n - a, 1))
    elif kind == "pluck":      # near-instant attack, exponential decay
        a = max(int(0.005 * n), 1)
        e[:a] = np.linspace(0, 1, a)
        e[a:] = np.exp(-5.0 * (idx[a:] - a) / max(n - a, 1))
    elif kind == "breath":     # soft bell, for near-silent pause
        e = np.hanning(n)
    return e


def _render(profile):
    n = int(profile["duration"] * SR)
    waveform = profile["waveform"]
    mod = profile.get("mod")
    env = _envelope(profile["envelope"], n)

    if waveform == "breath":
        # filtered noise: a held breath, not a pitch
        rng = np.random.default_rng(1729)  # fixed seed -> deterministic builds
        noise = rng.standard_normal(n)
        b, a = signal.butter(2, [300 / (SR / 2), 1800 / (SR / 2)], btype="band")
        sig = signal.lfilter(b, a, noise)
        return sig * env

    base = profile["base_freq"]
    interval = profile.get("interval")

    if interval and profile["envelope"] == "pluck" and len(interval) > 2:
        # arpeggio: spread notes sequentially across the duration (e.g. happy)
        sig = np.zeros(n)
        seg = n // len(interval)
        for k, semis in enumerate(interval):
            f = base * (2.0 ** (semis / 12.0))
            start = k * seg
            sub_n = n - start
            tone = _harmonic_stack(f, profile["harmonics"], waveform, sub_n, mod)
            sig[start:] += tone * _envelope("pluck", sub_n)
        return sig * (env if profile["envelope"] != "pluck" else 1.0)

    if interval:
        # simultaneous chord (us = fifth, love = fifth, afraid = minor-second tension)
        sig = np.zeros(n)
        for semis in interval:
            f = base * (2.0 ** (semis / 12.0))
            sig += _harmonic_stack(f, profile["harmonics"], waveform, n, mod)
        sig /= len(interval)
    else:
        sig = _harmonic_stack(base, profile["harmonics"], waveform, n, mod)

    # detune partner: a faint, slightly off second voice (forget/lost -> beating)
    if mod and mod["type"] == "detune":
        f2 = base * (2.0 ** (mod["cents"] / 1200.0))
        sig = 0.5 * sig + 0.5 * _harmonic_stack(f2, profile["harmonics"], waveform, n, None)

    # tremolo: amplitude pulsing (now, always)
    if mod and mod["type"] == "tremolo":
        t = np.arange(n) / SR
        lfo = 1.0 - mod["depth"] * (0.5 - 0.5 * np.cos(2.0 * np.pi * mod["rate"] * t))
        sig = sig * lfo

    return sig * env


# --- reverb ----------------------------------------------------------------
# A gentle plate-ish tail: notes ring out and bleed into the next, so a sequence
# of glyphs flows as one phrase. Deterministic (fixed seed) for reproducible builds.
def _make_ir():
    rng = np.random.default_rng(20260609)
    length = int(1.0 * SR)
    t = np.arange(length) / SR
    ir = rng.standard_normal(length) * np.exp(-t / 0.30)
    b, a = signal.butter(2, 6000 / (SR / 2), btype="low")  # warm, no hiss
    ir = signal.lfilter(b, a, ir)
    ir[: int(0.02 * SR)] = 0.0   # small pre-delay so the dry attack stays clear
    return ir / (np.max(np.abs(ir)) or 1.0)


_IR = _make_ir()


def _reverb(sig, wet=0.30):
    """Convolve with the IR and append the tail so the tone rings out."""
    rev = signal.fftconvolve(sig, _IR)
    rev *= (np.max(np.abs(sig)) or 1e-9) / (np.max(np.abs(rev)) or 1e-9)
    out = np.zeros(len(rev))
    out[: len(sig)] += sig
    out += wet * rev
    return out


def _level(sig, profile):
    """RMS-normalize to a shared loudness; keep Truth-category sparseness."""
    rms = np.sqrt(np.mean(sig ** 2)) or 1e-9
    sig = sig * (TARGET_RMS / rms)
    if profile["envelope"] == "breath":
        sig *= 0.35                       # pause ≈ near-silence
    elif profile["base_freq"] and profile["base_freq"] < 60:
        sig *= 0.6                        # sub-bass end barely there
    return sig


def _finish(sig):
    """Anti-click edges + peak limit."""
    f = int(EDGE_FADE_S * SR)
    if len(sig) > 2 * f:
        sig[:f] *= np.linspace(0, 1, f)
        sig[-f:] *= np.linspace(1, 0, f)
    peak = np.max(np.abs(sig)) or 1.0
    if peak > 0.95:
        sig *= 0.95 / peak
    return sig


def _build(profile):
    """Full pipeline: resolve pitch from the scale, render, level, reverb, finish."""
    profile = dict(profile)
    if profile.get("note") is not None:
        profile["base_freq"] = note_to_hz(profile["note"])
    core = _level(_render(profile), profile)
    if profile["waveform"] != "breath":      # keep the breath dry (truly quiet)
        core = _reverb(core)
    return _finish(core)


def _write_wav(path, sig):
    pcm = np.int16(np.clip(sig, -1, 1) * 32767)
    wavfile.write(path, SR, pcm)
    return pcm


def main(only=None):
    data = json.loads(TONES_JSON.read_text())
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    made = 0
    for tone in data["tones"]:
        if only and tone["id"] != only:
            continue
        pcm = _write_wav(OUT_DIR / f"{tone['id']}.wav", _build(tone["audio_profile"]))
        dur = len(pcm) / SR
        print(f"  {tone['glyph']} {tone['id']:14s} {dur:4.2f}s  {tone['meaning']}")
        made += 1
    print(f"\nWrote {made} tone(s) to {OUT_DIR}")


# --- verification: every pitched tone should land on a scale frequency -------
def verify():
    data = json.loads(TONES_JSON.read_text())
    # all scale frequencies within our register range, for nearest-match
    scale_hz = sorted(note_to_hz(s) for s in range(-12, 13))
    print(f"\n{'tone':16s} {'note':>4s} {'target':>8s} {'detected':>9s}  on-scale")
    print("-" * 52)
    bad = 0
    for tone in data["tones"]:
        p = tone["audio_profile"]
        if p["waveform"] == "breath":
            print(f"{tone['id']:16s} {'—':>4s} {'breath':>8s}")
            continue
        sig = _render({**p, "base_freq": note_to_hz(p["note"]), "mod": None,
                       "interval": None})  # bare fundamental for a clean FFT
        spec = np.abs(np.fft.rfft(sig * np.hanning(len(sig))))
        freqs = np.fft.rfftfreq(len(sig), 1 / SR)
        detected = freqs[np.argmax(spec)]
        target = note_to_hz(p["note"])
        nearest = min(scale_hz, key=lambda h: abs(h - detected))
        cents = 1200 * np.log2(detected / nearest) if detected > 0 else 999
        ok = abs(cents) < 35
        bad += not ok
        print(f"{tone['id']:16s} {p['note']:>4d} {target:8.1f} {detected:9.1f}  "
              f"{'ok' if ok else f'OFF {cents:+.0f}c'}")
    print(f"\n{'PASS' if bad == 0 else 'FAIL'} — {bad} tone(s) off the scale\n")


# --- demo: render sample PHRASES so glyph-melodies can be heard --------------
# Phrases are in Lily's reading order (see app/game.GRAMMAR_ORDER).
DEMOS = {
    "i_feel_sad":            ["self_i", "self_feel", "emo_sad"],
    "i_feel_now":            ["self_i", "self_feel", "time_now"],
    "i_love_you":            ["self_i", "emo_love", "other_you"],
    "i_remember_him_before": ["self_i", "self_remember", "other_him", "time_before"],
    "yes_i_afraid":          ["truth_yes", "self_i", "emo_afraid"],
    "finale":                ["self_i", "act_fall", "self_remember", "other_you",
                              "emo_happy", "other_him", "truth_no", "truth_nothing"],
}


def demo(stride_s=0.62):
    """Overlap-add tone renders into phrase WAVs: each note's onset is `stride_s`
    after the previous, so tails ring into each other and the phrase flows as a
    melody (an arpeggio), not a row of spaced beeps. This is how in-game playback
    should be timed — trigger the next glyph before the last has decayed."""
    data = {t["id"]: t for t in json.loads(TONES_JSON.read_text())["tones"]}
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    stride = int(stride_s * SR)
    for name, ids in DEMOS.items():
        renders = [_build(data[tid]["audio_profile"]) for tid in ids]
        total = stride * (len(renders) - 1) + max(len(r) for r in renders)
        buf = np.zeros(total)
        for k, r in enumerate(renders):
            start = k * stride
            buf[start:start + len(r)] += r
        phrase = _finish(buf)
        _write_wav(DEMO_DIR / f"{name}.wav", phrase)
        gloss = " ".join(data[t]["meaning"].split(" / ")[0] for t in ids)
        print(f"  {name:24s} {len(phrase)/SR:4.1f}s  \"{gloss}\"")
    print(f"\nWrote {len(DEMOS)} demo phrase(s) to {DEMO_DIR} (overlapping, ~{stride_s}s/note)")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg == "--verify":
        verify()
    elif arg == "--demo":
        main()   # ensure tones are fresh, then build phrases
        demo()
    else:
        main(arg)
