"""Procedural tone synthesis for Forgotten Lily (PLAN 6.4).

Reads data/tones.json and renders one WAV per tone into app/static/tones/.
No neural audio — every tone is a designed, deterministic sound. Run:

    python tones/synth.py            # generate all 24
    python tones/synth.py self_i     # generate one (debug)

Audio profile schema (see data/tones.json):
    base_freq : Hz of the fundamental (0 for pure-noise 'breath')
    waveform  : sine | triangle | saw | square | breath
    duration  : seconds
    harmonics : [a1, a2, a3, ...] amplitudes of harmonic multiples (1x, 2x, 3x...)
    envelope  : pad | swell | fade | pluck | breath
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

TARGET_RMS = 0.12      # perceptual loudness target shared across tones
EDGE_FADE_S = 0.008    # anti-click fade on every tone edge


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
    if kind == "pad":          # gentle attack/sustain/release
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
        # simultaneous chord (us, sad minor, love, afraid dissonance)
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


def _normalize(sig, profile):
    rms = np.sqrt(np.mean(sig ** 2)) or 1e-9
    sig = sig * (TARGET_RMS / rms)
    # Truth-category sparseness: pause near-silent, sub-bass end barely there.
    if profile["envelope"] == "breath":
        sig *= 0.35
    elif profile["base_freq"] and profile["base_freq"] < 60:
        sig *= 0.55
    # anti-click edges
    f = int(EDGE_FADE_S * SR)
    if len(sig) > 2 * f:
        sig[:f] *= np.linspace(0, 1, f)
        sig[-f:] *= np.linspace(1, 0, f)
    peak = np.max(np.abs(sig)) or 1.0
    if peak > 0.95:
        sig *= 0.95 / peak
    return sig


def main(only=None):
    data = json.loads(TONES_JSON.read_text())
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    made = 0
    for tone in data["tones"]:
        if only and tone["id"] != only:
            continue
        sig = _normalize(_render(tone["audio_profile"]), tone["audio_profile"])
        pcm = np.int16(np.clip(sig, -1, 1) * 32767)
        out = OUT_DIR / f"{tone['id']}.wav"
        wavfile.write(out, SR, pcm)
        dur = len(pcm) / SR
        print(f"  {tone['glyph']} {tone['id']:14s} {dur:4.2f}s  {tone['meaning']}")
        made += 1
    print(f"\nWrote {made} tone(s) to {OUT_DIR}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
