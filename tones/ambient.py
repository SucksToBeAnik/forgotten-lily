"""Ambient background bed for Forgotten Lily (PLAN 6.5).

A soft, slow DRONE PAD — not piano. Layered, slightly detuned sine voices spell a
quiet A-minor chord low and wide; each voice swells in and out on its own slow LFO,
so the bed breathes and drifts without ever restating a melody. A faint high shimmer
rises and falls over the top. The result sits under the tones as warm air, not music
that competes with them.

Seamless loop with NO crossfade needed: every component is exactly periodic over the
loop length T. Voice frequencies are snapped to an integer number of cycles per loop
(`snap`), and every LFO runs a whole number of cycles across T — so the waveform at
the loop's end meets its start with matching phase. No seam, no click.

    python tones/ambient.py   ->  app/static/audio/ambient.wav
"""
from pathlib import Path

import numpy as np
from scipy.io import wavfile

SR = 44100
T = 20.0                       # loop length (s) — long enough that the drift isn't obvious
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "app" / "static" / "audio" / "ambient.wav"

# A-minor, voiced low and open: A2 E3 A3 C4 E4 (root, fifth, octave, minor-third, fifth).
VOICES_HZ = [110.00, 164.81, 220.00, 261.63, 329.63]
# Three slightly detuned copies per voice -> a slow natural chorus/beating.
DETUNE_HZ = [-0.16, 0.0, 0.13]
# Soft, dark spectrum per voice (mostly fundamental, a little 2nd/3rd) -> warm, not buzzy.
HARMONICS = [1.0, 0.22, 0.08]


def snap(f):
    """Snap a frequency to a whole number of cycles over the loop -> seamless."""
    return round(f * T) / T


def voice(f0, t):
    """One warm, detuned, multi-harmonic drone voice at fundamental f0."""
    sig = np.zeros(len(t))
    for det in DETUNE_HZ:
        for k, amp in enumerate(HARMONICS, start=1):
            sig += amp * np.sin(2 * np.pi * snap((f0 + det) * k) * t)
    return sig / (len(DETUNE_HZ) * sum(HARMONICS))


def main():
    n = int(T * SR)
    t = np.arange(n) / SR
    buf = np.zeros(n)

    for i, f0 in enumerate(VOICES_HZ):
        # each voice breathes on its own slow swell — an integer number of cycles
        # across the loop (1..5), so it stays seamless while the blend keeps shifting.
        cycles = i + 1
        lfo = 0.45 + 0.45 * np.sin(2 * np.pi * (cycles / T) * t - np.pi / 2)
        weight = 0.95 / (1 + 0.55 * i)        # lower voices carry more weight
        buf += weight * lfo * voice(f0, t)

    # a faint high shimmer (E5) that fades in and out twice across the loop
    shimmer_lfo = 0.5 + 0.5 * np.sin(2 * np.pi * (2 / T) * t)
    buf += 0.06 * shimmer_lfo * np.sin(2 * np.pi * snap(659.25) * t)

    buf = buf / (np.max(np.abs(buf)) + 1e-9) * 0.55
    pcm = np.int16(np.clip(buf, -1, 1) * 32767)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(OUT, SR, pcm)
    print(f"Wrote {T:.0f}s seamless drone bed -> {OUT}  ({pcm.nbytes / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
