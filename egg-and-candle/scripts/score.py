"""Original score + sound effects for page 1, synthesized from scratch.

100 bpm, F major. Bars (2.4 s each) follow the picture:
  0-1 title / page arrives · 2-7 theme A (egg & candle) · 8 snow comes ·
  9-12 winter theme · 13-14 "Really?" pizzicato · 15-16 the warm seat ·
  17 wind-up · 18-20 the race · 21-23 the colored page, final chord.
Effects are cued to the composition's timeline (compositions/page1.html).

Usage: python3 scripts/score.py
       -> assets/audio/page1-score.wav, then ffmpeg loudnorm -> page1-score.m4a
"""
import subprocess
import wave
from pathlib import Path

import numpy as np
from scipy import signal

ROOT = Path(__file__).resolve().parent.parent
SR = 48000
TOTAL = 57.0
BEAT = 0.6
BAR = 4 * BEAT
rng = np.random.default_rng(2020)

music = np.zeros(int(SR * (TOTAL + 3)))
sfx = np.zeros_like(music)

NOTE = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


def hz(name):
    p, o = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((12 * (o + 1) + NOTE[p] - 69) / 12)


def t_(n):
    return np.arange(int(SR * n)) / SR


def add(buf, sig, at, gain=1.0):
    i = int(at * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += gain * sig[: j - i]


# ------------------------------------------------------------------ instruments
def music_box(f, dur=2.6):
    t = t_(dur)
    env = np.exp(-t / 0.75) * np.minimum(1, t / 0.003)
    return env * (np.sin(2 * np.pi * f * t) + 0.32 * np.sin(2 * np.pi * 2.0 * f * t) * np.exp(-t / 0.3)
                  + 0.14 * np.sin(2 * np.pi * 3.02 * f * t) * np.exp(-t / 0.16) + 0.06 * np.sin(2 * np.pi * 4.23 * f * t) * np.exp(-t / 0.07))


def glock(f, dur=2.2):
    t = t_(dur)
    env = np.exp(-t / 0.55) * np.minimum(1, t / 0.002)
    return env * (np.sin(2 * np.pi * f * t) + 0.45 * np.sin(2 * np.pi * 2.76 * f * t) * np.exp(-t / 0.2)
                  + 0.25 * np.sin(2 * np.pi * 5.4 * f * t) * np.exp(-t / 0.08))


def pizz(f, dur=0.55):
    t = t_(dur)
    env = np.exp(-t / 0.14) * np.minimum(1, t / 0.004)
    bend = 1 + 0.004 * np.exp(-t / 0.02)
    ph = 2 * np.pi * f * np.cumsum(bend) / SR
    tone = np.sin(ph) + 0.5 * np.sin(2 * ph) * np.exp(-t / 0.06) + 0.25 * np.sin(3 * ph) * np.exp(-t / 0.04)
    click = rng.standard_normal(len(t)) * np.exp(-t / 0.003) * 0.15
    return env * tone + click


def pad(freqs, dur, attack=0.8, release=0.9):
    t = t_(dur)
    env = np.minimum(1, t / attack) * np.minimum(1, np.maximum(0, (dur - t) / release))
    out = np.zeros_like(t)
    for f in freqs:
        for det in (-0.35, 0.0, 0.4):
            out += np.sin(2 * np.pi * (f + det) * t + rng.uniform(0, 6.28)) + 0.18 * np.sin(2 * np.pi * 2 * (f + det) * t)
    return env * out / (3 * len(freqs))


def sleigh(dur=0.16):
    t = t_(dur)
    n = rng.standard_normal(len(t))
    b, a = signal.butter(2, [5200 / (SR / 2), 11000 / (SR / 2)], "band")
    jingle = signal.lfilter(b, a, n) * np.exp(-t / 0.045)
    tones = sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28)) for f in (5870, 7310, 8920)) * np.exp(-t / 0.05) * 0.2
    return jingle + tones


def woodblock(f=880, dur=0.12):
    t = t_(dur)
    return np.sin(2 * np.pi * f * t) * np.exp(-t / 0.025) + 0.4 * np.sin(2 * np.pi * 2.3 * f * t) * np.exp(-t / 0.012)


# ------------------------------------------------------------------ effects
def noise_band(dur, lo, hi, env):
    n = rng.standard_normal(int(SR * dur))
    b, a = signal.butter(2, [lo / (SR / 2), min(hi, SR / 2 - 100) / (SR / 2)], "band")
    return signal.lfilter(b, a, n) * env(t_(dur))


def whoosh(dur=0.9, lo=300, hi=2600, rise=True):
    t = t_(dur)
    n = rng.standard_normal(len(t))
    out = np.zeros_like(n)
    steps = 24
    for k in range(steps):  # sweeping band-pass, stitched in short windows
        a0, a1 = int(k * len(t) / steps), int((k + 1) * len(t) / steps)
        c = lo + (hi - lo) * ((k / steps) if rise else 1 - k / steps)
        b, a = signal.butter(2, [max(60, c * 0.6) / (SR / 2), min(SR / 2 - 200, c * 1.6) / (SR / 2)], "band")
        seg = signal.lfilter(b, a, n[max(0, a0 - 2000): a1])[-(a1 - a0):]
        out[a0:a1] = seg
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5
    return out * env


def pop(f0=520, f1=180, dur=0.16):
    t = t_(dur)
    f = f1 + (f0 - f1) * np.exp(-t / 0.03)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.05) * np.minimum(1, t / 0.002)


def boing(f=260, dur=0.38):
    t = t_(dur)
    f_t = f * (1 + 0.9 * np.exp(-t / 0.05)) * (1 + 0.05 * np.sin(2 * np.pi * 18 * t))
    return np.sin(2 * np.pi * np.cumsum(f_t) / SR) * np.exp(-t / 0.12) * np.minimum(1, t / 0.004)


def thud(dur=0.4, f=85):
    t = t_(dur)
    body = np.sin(2 * np.pi * np.cumsum(f * (1 + 1.2 * np.exp(-t / 0.03))) / SR) * np.exp(-t / 0.1)
    return body + noise_band(dur, 80, 900, lambda x: np.exp(-x / 0.03)) * 0.4


def scribble(dur):
    t = t_(dur)
    strokes = 0.55 + 0.45 * np.sin(2 * np.pi * 7.5 * t + 2 * np.sin(2 * np.pi * 1.3 * t))
    return noise_band(dur, 1800, 7000, lambda x: np.minimum(1, x / 0.05) * np.minimum(1, (dur - x) / 0.08)) * strokes ** 2


def paper(dur=0.5):
    return noise_band(dur, 900, 6000, lambda x: np.sin(np.pi * np.clip(x / dur, 0, 1)) ** 2 * (0.6 + 0.4 * np.sin(2 * np.pi * 23 * x)))


def sparkle(at, n=5, base=1568, step=1.19, gap=0.07, gain=0.22):
    for i in range(n):
        add(sfx, glock(base * step ** i, 1.0), at + i * gap, gain * (1 - i * 0.08))


def crunch(dur=0.09):
    return noise_band(dur, 1500, 6500, lambda x: np.exp(-x / 0.02) * np.minimum(1, x / 0.003))


def slide_whistle(dur, f0, f1):
    t = t_(dur)
    f = f0 * (f1 / f0) ** (t / dur)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, t / 0.03) * np.minimum(1, (dur - t) / 0.05)


# ------------------------------------------------------------------ the score
CH = {
    "F": ["F3", "A3", "C4"], "Dm": ["D3", "F3", "A3"], "Bb": ["Bb2", "D3", "F3"], "C": ["C3", "E3", "G3"],
    "C7": ["C3", "E3", "Bb3"], "Gm": ["G2", "Bb2", "D3"], "Am": ["A2", "C3", "E3"],
}


def bar_t(b):
    return b * BAR


def melody(inst, notes, start_bar, gain, octave_sparkle=False):
    t = bar_t(start_bar)
    for name, beats in notes:
        if name:
            add(music, inst(hz(name)), t, gain)
            if octave_sparkle:
                add(music, glock(hz(name) * 2, 1.2), t + 0.005, gain * 0.18)
        t += beats * BEAT


def bass_pizz(chords, start_bar, gain=0.34, pattern=(0, 2)):
    for i, c in enumerate(chords):
        root = CH[c][0]
        for k, beat in enumerate(pattern):
            n = root if k % 2 == 0 else CH[c][2]
            add(music, pizz(hz(n)), bar_t(start_bar + i) + beat * BEAT, gain)


def pads(chords, start_bar, gain=0.1, bars_each=1):
    for i, c in enumerate(chords):
        add(music, pad([hz(n) * 2 for n in CH[c]], BAR * bars_each + 0.9), bar_t(start_bar + i * bars_each), gain)


# bars 0-1: title arpeggio, page arrives
for k, n in enumerate(["F4", "A4", "C5", "F5", "A5", "C6"]):
    add(music, music_box(hz(n)), 0.25 + k * 0.3, 0.2)
pads(["F", "C"], 0, 0.07)
for k, n in enumerate(["G4", "C5", "E5", "G5"]):
    add(music, music_box(hz(n)), bar_t(1) + 0.3 + k * 0.45, 0.13)

# bars 2-7: theme A
A = [
    [("A4", 1), ("C5", 1), ("F5", 1), ("E5", 1)],
    [("D5", 1), ("C5", 1), ("A4", 2)],
    [("Bb4", 1), ("D5", 1), ("F5", 1), ("D5", 1)],
    [("C5", 3), ("G4", 1)],
    [("A4", 1), ("C5", 1), ("F5", 1), ("G5", 1)],
    [("A5", 1), ("G5", 1), ("F5", 1), ("E5", 1)],
]
for i, bar in enumerate(A):
    melody(music_box, bar, 2 + i, 0.24)
bass_pizz(["F", "Dm", "Bb", "C", "F", "Bb"], 2, 0.3, pattern=(0, 1, 2, 3))
pads(["F", "Dm", "Bb", "C", "F", "Bb"], 2, 0.075)

# bar 8: the snow comes — suspended, sleigh-bell shimmer
melody(glock, [("F5", 2), ("D5", 2)], 8, 0.16)
pads(["Dm"], 8, 0.1)
for k in range(12):
    add(music, sleigh(), bar_t(8) + 0.9 + k * 0.125, 0.05 + 0.012 * k)

# bars 9-12: winter theme (glockenspiel over pads, sleigh bells on eighths)
B = [
    [("D5", 2), ("A4", 2)],
    [("Bb4", 1), ("C5", 1), ("D5", 2)],
    [("C5", 2), ("A4", 1), ("F4", 1)],
    [("G4", 2), ("E4", 1), ("C5", 1)],
]
for i, bar in enumerate(B):
    melody(glock, bar, 9 + i, 0.2, octave_sparkle=True)
pads(["Dm", "Bb", "F", "C"], 9, 0.1)
bass_pizz(["Dm", "Bb", "F", "C"], 9, 0.24, pattern=(0, 2))
for b in range(9, 13):
    for k in range(8):
        add(music, sleigh(0.12), bar_t(b) + k * BEAT / 2, 0.045 if k % 2 else 0.07)

# bars 13-14: "Really?" / "What?" — sneaky pizzicato
sneak = [[("D4", 0.5), (None, 0.5), ("F4", 0.5), (None, 0.5), ("A4", 0.5), (None, 0.5), ("G#4", 0.5), ("A4", 0.5)],
         [("Bb4", 0.5), (None, 0.5), ("A4", 0.5), (None, 0.5), ("F4", 0.5), ("E4", 0.5), ("D4", 1)]]
for i, bar in enumerate(sneak):
    melody(pizz, bar, 13 + i, 0.4)
bass_pizz(["Dm", "Gm"], 13, 0.26, pattern=(0, 1, 2, 3))
pads(["Dm", "Gm"], 13, 0.05)

# bars 15-16: the warm seat — cozy F major
melody(music_box, [("C5", 1), ("A4", 1), ("F4", 1), ("A4", 1)], 15, 0.24)
melody(music_box, [("Bb4", 1), ("D5", 1), ("C5", 2)], 16, 0.24)
pads(["F", "Bb"], 15, 0.12)
bass_pizz(["F", "Bb"], 15, 0.22, pattern=(0, 2))

# bar 17: wind-up to the race
for k, n in enumerate(["C4", "E4", "G4", "Bb4", "C5", "E5", "G5", "Bb5"]):
    add(music, pizz(hz(n)), bar_t(17) + k * BEAT / 2, 0.3)
pads(["C7"], 17, 0.07)

# bars 18-20: the race — eighth-note ostinato, woodblock, theme A in staccato eighths
R = [
    [("A4", .5), ("C5", .5), ("F5", .5), ("E5", .5), ("D5", .5), ("C5", .5), ("A4", .5), ("C5", .5)],
    [("Bb4", .5), ("D5", .5), ("F5", .5), ("D5", .5), ("C5", .5), ("E5", .5), ("G5", .5), ("E5", .5)],
    [("F5", .5), ("E5", .5), ("D5", .5), ("C5", .5), ("Bb4", .5), ("A4", .5), ("G4", .5), ("C5", .5)],
]
for i, bar in enumerate(R):
    melody(music_box, bar, 18 + i, 0.2)
for i, c in enumerate(["F", "Bb", "C7"]):
    for k in range(8):
        n = CH[c][0] if k % 2 == 0 else CH[c][2]
        add(music, pizz(hz(n)), bar_t(18 + i) + k * BEAT / 2, 0.26)
        add(music, woodblock(1100 if k % 2 else 760), bar_t(18 + i) + k * BEAT / 2 + (BEAT / 4 if k % 2 else 0), 0.06)
pads(["F", "Bb", "C7"], 18, 0.06)

# bars 21-23: the colored page — slow cadence, final chord, bell
melody(music_box, [("F5", 2), ("D5", 2)], 21, 0.22)
pads(["Bb"], 21, 0.1)
for k, n in enumerate(["F4", "A4", "C5", "F5"]):
    add(music, music_box(hz(n), 4.0), bar_t(22) + k * 0.16, 0.2)
add(music, pad([hz(n) * 2 for n in CH["F"]], 5.5, attack=0.4, release=3.0), bar_t(22), 0.13)
add(music, pizz(hz("F2"), 1.0), bar_t(22), 0.35)
add(music, glock(hz("C6"), 3.0), 54.0, 0.17)
add(music, glock(hz("F6"), 3.0), 54.12, 0.12)

# ------------------------------------------------------------------ effects cue sheet
add(sfx, scribble(0.95), 0.3, 0.22)
add(sfx, pop(620, 240), 0.55, 0.35)
add(sfx, pop(900, 400, 0.12), 1.2, 0.28)
add(sfx, scribble(1.05), 1.4, 0.22)
add(sfx, pop(760, 300), 1.55, 0.35)
add(sfx, boing(300), 2.55, 0.18)
add(sfx, boing(380), 2.7, 0.16)
add(sfx, paper(0.9), 3.28, 0.28)
add(sfx, whoosh(2.4, 200, 1400), 4.5, 0.1)
sparkle(5.75, 7, 1047, 1.122, 0.13, 0.16)
add(sfx, paper(0.35), 7.45, 0.2)
add(sfx, boing(260), 8.45, 0.26)
sparkle(8.9, 3, 2093, 1.26, 0.12, 0.18)
sparkle(11.3, 4, 1397, 1.19, 0.06, 0.16)
add(sfx, whoosh(1.4, 250, 1800), 12.6, 0.14)
for t, f in ((12.75, 280), (13.35, 300), (13.95, 320)):
    add(sfx, boing(f), t, 0.18)
add(sfx, paper(0.45), 14.4, 0.24)
add(sfx, boing(360), 14.75, 0.2)
add(sfx, paper(0.45), 16.3, 0.24)
add(sfx, noise_band(0.5, 300, 2400, lambda x: np.sin(np.pi * np.clip(x / 0.5, 0, 1))), 16.9, 0.18)
for t, f in ((17.5, 260), (17.55, 350), (18.15, 280), (18.2, 370)):
    add(sfx, boing(f), t, 0.16)
add(sfx, pop(1000, 500, 0.14), 18.45, 0.24)
sparkle(18.5, 3, 2637, 1.12, 0.08, 0.12)
add(sfx, whoosh(2.2, 150, 900), 19.0, 0.09)

# winter: soft wind bed and crunchy steps
wind_len = 43.7 - 20.4
wt = t_(wind_len)
wind = noise_band(wind_len, 180, 1100, lambda x: (0.55 + 0.45 * np.sin(2 * np.pi * 0.13 * x + 1.2) * np.sin(2 * np.pi * 0.07 * x)) * np.minimum(1, x / 1.5) * np.minimum(1, (wind_len - x) / 1.5))
add(sfx, wind, 20.4, 0.05)
t = 20.4
while t < 29.9:
    add(sfx, crunch(), t, 0.05)
    t += 0.36
t = 20.5
while t < 29.9:
    add(sfx, crunch(0.07), t, 0.035)
    t += 0.42
add(sfx, pop(560, 220), 22.0, 0.3)
for i in range(6):
    add(sfx, noise_band(0.5, 400, 2500, lambda x: np.sin(np.pi * np.clip(x / 0.5, 0, 1)) ** 2), 22.3 + i * 1.25, 0.05)
add(sfx, whoosh(1.2, 250, 1600), 23.9, 0.11)
add(sfx, pop(700, 300), 25.2, 0.3)
add(sfx, noise_band(0.6, 250, 2200, lambda x: np.sin(np.pi * np.clip(x / 0.6, 0, 1))), 25.3, 0.18)
sparkle(25.35, 3, 1319, 1.26, 0.09, 0.12)
add(sfx, whoosh(1.5, 300, 1200, rise=False), 27.0, 0.08)
add(sfx, whoosh(0.55, 500, 5000), 29.95, 0.28)
add(sfx, pop(640, 260), 31.3, 0.3)
add(sfx, boing(520, 0.3), 32.95, 0.24)
add(sfx, noise_band(0.4, 400, 3000, lambda x: np.sin(np.pi * np.clip(x / 0.4, 0, 1))), 33.0, 0.2)
add(sfx, pop(820, 360), 33.15, 0.3)
sparkle(34.6, 2, 2349, 1.33, 0.1, 0.14)
add(sfx, slide_whistle(0.36, 300, 1200), 35.35, 0.08)
add(sfx, whoosh(0.45, 600, 4200), 35.68, 0.2)
add(sfx, thud(0.5, 70), 36.28, 0.6)
add(sfx, noise_band(0.9, 200, 5000, lambda x: np.exp(-x / 0.22) * np.minimum(1, x / 0.01)), 36.28, 0.3)
add(sfx, pop(600, 250), 37.6, 0.3)
for t in (37.9, 38.45, 39.0):
    add(sfx, pop(1100, 600, 0.12), t, 0.16)
add(sfx, pop(360, 160, 0.2), 39.5, 0.3)
for t in (39.7, 40.9):
    for k in range(7):
        add(sfx, woodblock(420 + 40 * (k % 3), 0.06), t + k * 0.1, 0.05)
add(sfx, paper(0.6), 42.0, 0.24)
add(sfx, paper(0.7), 43.5, 0.16)
add(sfx, boing(420, 0.3), 43.95, 0.2)
add(sfx, pop(700, 300), 44.0, 0.3)
t = 44.2
while t < 50.6:
    add(sfx, crunch(0.05), t, 0.03)
    t += 0.1
add(sfx, whoosh(1.1, 300, 2000), 45.35, 0.12)
for t in (45.75, 46.2, 46.65, 48.4, 48.85):
    add(sfx, thud(0.3, 110), t + 0.36, 0.25)
add(sfx, pop(900, 380), 46.0, 0.32)
add(sfx, whoosh(1.3, 250, 1200, rise=False), 47.7, 0.08)
add(sfx, pop(700, 300), 48.2, 0.24)
add(sfx, paper(0.6), 50.7, 0.14)
add(sfx, whoosh(2.4, 900, 200, rise=True), 51.35, 0.08)
add(sfx, scribble(1.3), 54.0, 0.18)

# ------------------------------------------------------------------ mix
n = int(SR * TOTAL)
mix = music[:n] * 0.9 + sfx[:n]
# small room: seeded noise-burst reverb on the music bus only
ir_t = t_(1.8)
ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t / 0.4)
ir[: int(0.012 * SR)] = 0
wet = signal.fftconvolve(music[:n], ir)[:n]
wet *= 0.16 * np.max(np.abs(music[:n])) / (np.max(np.abs(wet)) + 1e-9)
left = mix + wet
right = mix + np.roll(wet, int(SR * 0.011))
fade = np.ones(n)
fade[-int(SR * 1.2):] = np.linspace(1, 0, int(SR * 1.2)) ** 1.5
fade[: int(SR * 0.02)] = np.linspace(0, 1, int(SR * 0.02))
stereo = np.stack([left * fade, right * fade], axis=1)
stereo *= 0.89 / np.max(np.abs(stereo))

out = ROOT / "assets" / "audio"
out.mkdir(parents=True, exist_ok=True)
with wave.open(str(out / "page1-score.wav"), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((stereo * 32767).astype(np.int16).tobytes())
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(out / "page1-score.wav"),
                "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", str(out / "page1-score.m4a")], check=True)
(out / "page1-score.wav").unlink()
print("wrote", out / "page1-score.m4a", f"{TOTAL:.1f}s")
