"""Ambient background bed for Forgotten Lily (PLAN 6.5).

A soft, slow piano figure — gentle arpeggiated chords that ring and decay — that
plays continuously and ducks to silence only while Lily's tones sound.

Generated procedurally (no external asset). Piano-ness comes from three things a
sustained pad lacks:
  1. a struck envelope: near-instant attack, continuous exponential decay;
  2. a bright-to-dark spectrum: many partials, higher ones decaying faster;
  3. slight inharmonicity (stretched partials), like real strings.

Seamless loop: each note is mixed in with CIRCULAR (wrap-around) indexing, so a
ringing tail that runs past the loop end folds back onto the start — the last
chord rings into the first, exactly as it will every loop. No seam, no fade.

    python tones/ambient.py   ->  app/static/audio/ambient.wav
"""
from pathlib import Path

import numpy as np
from scipy.io import wavfile

SR = 44100
T = 16.0                      # loop length (s); 4 chords x 4s
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "app" / "static" / "audio" / "ambient.wav"

# note name -> frequency (just the few octaves we need)
N = {
    "F2": 87.31, "G2": 98.00, "A2": 110.00, "C3": 130.81, "E3": 164.81,
    "F3": 174.61, "G3": 196.00, "A3": 220.00, "B3": 246.94, "C4": 261.63,
    "D4": 293.66, "E4": 329.63, "F4": 349.23, "G4": 392.00, "A4": 440.00,
}

# A gentle, slightly wistful progression: Am – F – C – G (vi–IV–I–V).
# Each entry: (bass note, [arpeggio notes played low->high]).
PROGRESSION = [
    ("A2", ["A3", "C4", "E4"]),
    ("F2", ["F3", "A3", "C4"]),
    ("C3", ["C4", "E4", "G4"]),
    ("G2", ["G3", "B3", "D4"]),
]
CHORD_S = T / len(PROGRESSION)     # seconds per chord
ARP_OFFSETS = [0.0, 0.5, 1.0]      # when each arpeggio note is struck within a chord
NOTE_LEN = 4.0                     # how long a struck note is rendered (rings + decays)


def piano_note(freq, vel):
    """One struck, decaying, slightly inharmonic piano-ish tone."""
    n = int(NOTE_LEN * SR)
    t = np.arange(n) / SR
    B = 0.0005                      # inharmonicity coefficient
    sig = np.zeros(n)
    for k in range(1, 13):
        fk = freq * k * np.sqrt(1 + B * k * k)
        if fk > SR / 2:
            break
        amp = 1.0 / (k ** 1.3)              # spectral rolloff
        decay = np.exp(-t * (0.6 + 0.4 * k))   # slow ring; higher partials die faster -> mellows
        sig += amp * decay * np.sin(2 * np.pi * fk * t)
    atk = int(0.004 * SR)                   # hammer attack
    sig[:atk] *= np.linspace(0, 1, atk)
    return sig * vel


def add_circular(buf, note, start_sample):
    """Mix `note` into `buf` (length N) starting at start_sample, wrapping around
    the loop boundary so tails fold onto the start -> seamless."""
    n = len(buf)
    idx = (start_sample + np.arange(len(note))) % n
    np.add.at(buf, idx, note)


def main():
    n = int(T * SR)
    buf = np.zeros(n)
    for c, (bass, notes) in enumerate(PROGRESSION):
        base = c * CHORD_S
        add_circular(buf, piano_note(N[bass], 0.55), int(base * SR))       # soft bass
        for off, name in zip(ARP_OFFSETS, notes):
            add_circular(buf, piano_note(N[name], 0.40), int((base + off) * SR))

    buf = buf / (np.max(np.abs(buf)) + 1e-9) * 0.7
    pcm = np.int16(np.clip(buf, -1, 1) * 32767)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(OUT, SR, pcm)
    print(f"Wrote {T:.0f}s seamless piano bed -> {OUT}  ({pcm.nbytes / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
