"""Synthesize an original music-box lullaby for 《小光》 (F major, 67 bpm, 20 bars ≈ 72s).

Usage: python3 scripts/lullaby.py && ffmpeg -y -i assets/lullaby.wav -c:a aac -b:a 160k assets/lullaby.m4a
"""
import wave

import numpy as np

SR = 44100
BPM = 67
BEAT = 60 / BPM
TOTAL = 72.0

NOTES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "Bb": 10, "B": 11}


def freq(name):
    pitch, octave = name[:-1], int(name[-1])
    midi = 12 * (octave + 1) + NOTES[pitch]
    return 440.0 * 2 ** ((midi - 69) / 12)


def music_box(f, dur, amp):
    t = np.arange(int(SR * dur)) / SR
    env = np.exp(-t / 0.9) * np.minimum(1, t / 0.004)
    tone = (
        np.sin(2 * np.pi * f * t)
        + 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.35)
        + 0.12 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t / 0.2)
        + 0.05 * np.sin(2 * np.pi * 4.2 * f * t) * np.exp(-t / 0.08)
    )
    return amp * env * tone


def pad(freqs, dur, amp):
    t = np.arange(int(SR * dur)) / SR
    env = np.minimum(1, t / 1.2) * np.minimum(1, (dur - t) / 1.2)
    out = sum(np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t) for f in freqs)
    return amp * env * out / len(freqs)


# (melody notes with beat lengths) — one 8-bar verse
VERSE = [
    [("A4", 1), ("C5", 1), ("A4", 2)],
    [("G4", 1), ("A4", 1), ("F4", 2)],
    [("D4", 1), ("F4", 1), ("G4", 1), ("A4", 1)],
    [("G4", 3), (None, 1)],
    [("A4", 1), ("C5", 1), ("D5", 1), ("C5", 1)],
    [("D5", 1), ("C5", 1), ("A4", 2)],
    [("G4", 1), ("A4", 1), ("C5", 1), ("A4", 1)],
    [("G4", 2), ("F4", 2)],
]
CHORDS = {
    "F": ["F3", "A3", "C4"],
    "Dm": ["D3", "F3", "A3"],
    "Bb": ["Bb2", "D3", "F3"],
    "C": ["C3", "E3", "G3"],
}
PROGRESSION = ["F", "Dm", "Bb", "C", "F", "Dm", "Bb", "C"]

out = np.zeros(int(SR * (TOTAL + 4)))


def add(sig, start):
    i = int(start * SR)
    out[i : i + len(sig)] += sig[: len(out) - i]


bar_len = 4 * BEAT
# bars 0-1: intro arpeggio; bars 2-9: verse; bars 10-17: verse (softer, octave up sparkle); 18-19: ending
for bar in range(20):
    chord = PROGRESSION[bar % 8] if bar < 18 else "F"
    start = bar * bar_len
    notes = CHORDS[chord]
    add(pad([freq(n) for n in notes], bar_len + 0.6, 0.05), start)
    add(music_box(freq(notes[0]), 3.0, 0.16), start)
    add(music_box(freq(notes[2]), 2.5, 0.07), start + 2 * BEAT)
    if bar < 2 or bar >= 18:
        for k, n in enumerate(notes + [notes[1]]):
            add(music_box(freq(n.replace("3", "4").replace("2", "3")), 2.0, 0.08), start + k * BEAT)

for rep, (first_bar, gain, octave_up) in enumerate([(2, 0.22, False), (10, 0.17, True)]):
    for b, bar_notes in enumerate(VERSE):
        t = (first_bar + b) * bar_len
        for name, beats in bar_notes:
            if name:
                add(music_box(freq(name), 2.8, gain), t)
                if octave_up:
                    add(music_box(freq(name) * 2, 1.6, gain * 0.25), t + 0.01)
            t += beats * BEAT

add(music_box(freq("F5"), 5.0, 0.12), 18 * bar_len + 2 * BEAT)
add(music_box(freq("C5"), 5.0, 0.10), 19 * bar_len)
add(music_box(freq("F4"), 5.0, 0.12), 19 * bar_len)

# simple reverb: decaying noise impulse (fixed seed → deterministic)
rng = np.random.default_rng(7)
ir_t = np.arange(int(SR * 2.2)) / SR
ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t / 0.55)
ir[0] = 0
wet = np.fft.irfft(np.fft.rfft(out, len(out) + len(ir)) * np.fft.rfft(ir, len(out) + len(ir)))[: len(out)]
wet /= np.max(np.abs(wet)) + 1e-9
dry = out / (np.max(np.abs(out)) + 1e-9)
left = 0.8 * dry + 0.22 * np.roll(wet, 0)
right = 0.8 * dry + 0.22 * np.roll(wet, int(SR * 0.013))

n = int(SR * TOTAL)
left, right = left[:n], right[:n]
fade = np.ones(n)
fade[-int(SR * 3) :] = np.linspace(1, 0, int(SR * 3))
fade[: int(SR * 0.05)] = np.linspace(0, 1, int(SR * 0.05))
stereo = np.stack([left * fade, right * fade], axis=1)
stereo *= 0.85 / np.max(np.abs(stereo))

with wave.open("assets/lullaby.wav", "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((stereo * 32767).astype(np.int16).tobytes())
print("wrote assets/lullaby.wav", n / SR, "s")
