"""Pages 2-5 of the score. Runs inside scripts/score.py's namespace (it is
exec'd there, after page 1), so it shares its buffers, instruments and effects.
Every cue is written in its page's local time and shifted by PAGE[n].
"""

CH.update({
    "A": ["A2", "C#3", "E3"], "A7": ["A2", "C#3", "G3"], "Gm7": ["G2", "Bb2", "F3"], "Dm7": ["D3", "F3", "C4"],
    "Bbmaj7": ["Bb2", "D3", "A3"], "Fadd9": ["F3", "A3", "G4"], "Csus": ["C3", "F3", "G3"], "Edim": ["E3", "G3", "Bb3"],
    "Dmadd9": ["D3", "F3", "E4"], "Eb": ["Eb3", "G3", "Bb3"],
})


def seq(inst, notes, t0, beat, gain, sparkle_oct=False):
    t = t0
    for name, beats in notes:
        if name:
            add(music, inst(hz(name)), t, gain)
            if sparkle_oct:
                add(music, glock(hz(name) * 2, 1.2), t + 0.005, gain * 0.18)
        t += beats * beat
    return t


def chord_pads(names, t0, each, gain, attack=0.8, release=0.9):
    for i, c in enumerate(names):
        add(music, pad([hz(n) * 2 for n in CH[c]], each + 0.9, attack, release), t0 + i * each, gain)


def walk(names, t0, each, beat, gain, steps=(0, 1, 2, 3)):
    for i, c in enumerate(names):
        for k, b in enumerate(steps):
            n = CH[c][0] if k % 2 == 0 else CH[c][2]
            add(music, pizz(hz(n)), t0 + i * each + b * beat, gain)


def low_drone(dur, notes=("D2", "A2"), gain=0.1):
    t = t_(dur)
    env = np.minimum(1, t / 2.0) * np.minimum(1, (dur - t) / 2.0)
    out = sum(np.sin(2 * np.pi * hz(n) * t + k) + 0.3 * np.sin(2 * np.pi * 2 * hz(n) * t) for k, n in enumerate(notes))
    wob = 1 + 0.15 * np.sin(2 * np.pi * 0.21 * t)
    return env * out * wob * gain / len(notes)


# ------------------------------------------------------------------ new effects
def sob(f0=340, dur=0.34):
    """a small "wu": a vowel-ish tone sliding down with a wobble"""
    t = t_(dur)
    f = f0 * (1 - 0.18 * t / dur) * (1 + 0.03 * np.sin(2 * np.pi * 7 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = sum((0.9 ** k) * np.sin(k * ph) for k in range(1, 9))
    b, a = signal.butter(2, 950 / (SR / 2), "low")
    return signal.lfilter(b, a, tone) * np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.2


def heartbeat(at, n, period=0.95, gain=0.45):
    for i in range(n):
        for d, g in ((0, 1.0), (0.2, 0.7)):
            add(sfx, thud(0.3, 55), at + i * period + d, gain * g)


def thunder(at, gain=1.0, crack=True, length=4.0):
    if crack:
        add(sfx, noise_band(0.5, 900, 7000, lambda x: np.exp(-x / 0.06) * np.minimum(1, x / 0.002)), at, 0.55 * gain)
        add(sfx, noise_band(1.2, 200, 2500, lambda x: np.exp(-x / 0.25) * np.minimum(1, x / 0.01)), at + 0.02, 0.4 * gain)
    rum = noise_band(length, 25, 220, lambda x: np.minimum(1, x / 0.15) * np.exp(-x / (length * 0.35)) * (0.6 + 0.4 * np.sin(2 * np.pi * 1.7 * x) * np.sin(2 * np.pi * 0.6 * x + 1)))
    add(sfx, rum, at + (0.05 if crack else 0), 1.6 * gain)


def rain_bed(t0, t1, level, seed):
    """steady rain: filtered noise plus random drops; level(t_local) shapes it"""
    dur = t1 - t0
    t = t_(dur)
    hiss = noise_band(dur, 400, 7500, lambda x: 1.0) * 0.5 + noise_band(dur, 120, 900, lambda x: 1.0) * 0.35
    env = np.minimum(1, t / 1.2) * np.minimum(1, (dur - t) / 1.5) * np.vectorize(level)(t)
    add(sfx, hiss * env, t0, 0.22)
    r = np.random.default_rng(seed)
    k = 0.0
    while k < dur:
        f = 2200 + r.random() * 3600
        add(sfx, pop(f, f * 0.6, 0.05), t0 + k, 0.03 * float(level(k)))
        k += 0.03 + r.random() * 0.07


def knock(at):
    add(sfx, woodblock(190, 0.14), at, 0.5)
    add(sfx, thud(0.18, 120), at, 0.35)


def stab(at, notes=("D4", "Eb4", "A4", "D5"), gain=0.34):
    for n in notes:
        add(music, pizz(hz(n), 0.8), at, gain)
    add(sfx, thud(0.45, 70), at, 0.5)
    add(sfx, noise_band(0.35, 300, 4000, lambda x: np.exp(-x / 0.08)), at, 0.18)


def splash_step(at, gain=0.12):
    add(sfx, noise_band(0.12, 250, 2600, lambda x: np.exp(-x / 0.035) * np.minimum(1, x / 0.004)), at, gain)
    add(sfx, pop(1800, 900, 0.05), at + 0.02, gain * 0.25)


def breath(at, dur=0.35, gain=0.08, lo=500, hi=3200):
    add(sfx, noise_band(dur, lo, hi, lambda x: np.sin(np.pi * np.clip(x / dur, 0, 1)) ** 2), at, gain)


def ignite(at):
    swell = noise_band(1.1, 90, 900, lambda x: np.minimum(1, x / 0.25) ** 2 * np.exp(-np.maximum(0, x - 0.25) / 0.25))
    add(sfx, swell, at - 0.15, 0.5)
    add(sfx, pop(180, 90, 0.4), at + 0.1, 0.35)
    sparkle(at + 0.05, 8, 1319, 1.122, 0.06, 0.2)


def ticks(at, n, gap=0.3, f=1500, gain=0.1):
    for i in range(n):
        add(sfx, woodblock(f, 0.06), at + i * gap, gain)


def P(n, t):
    return PAGE[n] + t


# ================================================================== PAGE 2 (the roll, the crash, the memory)
o = PAGE[2]
# page in: paper, push, the color blooms
add(sfx, paper(0.9), o + 0.05, 0.26)
add(sfx, whoosh(2.4, 200, 1400), o + 1.9, 0.1)
sparkle(o + 3.45, 6, 1175, 1.122, 0.14, 0.14)
for k, n in enumerate(["C5", "E5", "G5", "C6"]):
    add(music, music_box(hz(n)), o + 3.0 + k * 0.32, 0.14)
chord_pads(["C"], o + 2.6, 2.0, 0.06)

# A: "I can roll!" / "Humph!" — theme A, bouncy
seq(music_box, [("A4", .5), ("C5", .5), ("F5", .5), ("E5", .5), ("D5", .5), ("C5", .5), ("A4", 1)], o + 4.3, BEAT, 0.22)
seq(music_box, [("Bb4", .5), ("D5", .5), ("F5", .5), ("D5", .5), ("C5", 2)], o + 4.3 + BAR, BEAT, 0.22)
walk(["F", "Bb"], o + 4.3, BAR, BEAT / 2, 0.24, steps=range(8))
rolling = noise_band(4.2, 60, 500, lambda x: (0.6 + 0.4 * np.sin(2 * np.pi * 4.5 * x)) * np.minimum(1, x / 0.2) * np.minimum(1, (4.2 - x) / 0.3))
add(sfx, rolling, o + 4.6, 0.16)
add(sfx, pop(700, 300), o + 5.6, 0.2)
add(sfx, boing(420, 0.32), o + 7.0, 0.22)
add(sfx, pop(820, 360), o + 7.1, 0.2)
add(sfx, whoosh(0.9, 400, 3800), o + 8.5, 0.24)
add(sfx, whoosh(0.5, 600, 5200), o + 9.1, 0.18)

# B: the crash, dizzy stars, the candle laughs
add(sfx, thud(0.6, 60), o + 9.62, 0.75)
add(sfx, crunch(0.2), o + 9.62, 0.2)
add(sfx, noise_band(1.0, 200, 5000, lambda x: np.exp(-x / 0.2) * np.minimum(1, x / 0.01)), o + 9.62, 0.25)
add(sfx, pop(1200, 500, 0.14), o + 9.85, 0.26)
for k in range(9):
    add(sfx, glock(hz(["E6", "G6", "C7"][k % 3]), 0.6), o + 10.3 + k * 0.5, 0.07)
for t in np.arange(10.9, 11.9, 0.2):
    add(sfx, woodblock(900, 0.05), o + t, 0.05)
laugh = [("F5", .25), ("D5", .25), ("F5", .25), ("D5", .25), ("F5", .25), ("D5", .25), ("C5", .5)]
for b in range(3):
    seq(pizz, laugh, o + 12.2 + b * 1.25, BEAT, 0.26)
add(sfx, pop(640, 260), o + 12.45, 0.28)
chord_pads(["Dm", "Gm", "C"], o + 10.0, 2.0, 0.05)

# C: HA HA HA, "You're stuck!", the struggle to get up
add(sfx, whoosh(0.5, 500, 3500), o + 15.8, 0.2)
for k in range(5):
    add(sfx, woodblock(640 + 80 * k, 0.08), o + 16.3 + k * 0.26, 0.1)
sneak2 = [("D4", .5), (None, .5), ("F4", .5), (None, .5), ("A4", .5), (None, .5), ("G#4", .5), ("A4", .5)]
for b in range(3):
    seq(pizz, sneak2, o + 16.3 + b * BAR, BEAT, 0.34)
walk(["Dm", "Gm", "A7"], o + 16.3, BAR, BEAT, 0.2)
add(sfx, pop(560, 240), o + 17.4, 0.28)
for t in (18.3, 19.4, 20.5):
    add(sfx, slide_whistle(0.3, 520, 260), o + t + 0.2, 0.06)
    add(sfx, thud(0.25, 90), o + t + 0.34, 0.2)

# D: the slip into the yolk, "Huh!? I was stuck?", giggles
add(sfx, whoosh(0.5, 500, 3500), o + 22.5, 0.2)
add(sfx, slide_whistle(0.7, 900, 300), o + 22.6, 0.08)
add(sfx, thud(0.5, 75), o + 23.3, 0.55)
add(sfx, noise_band(0.4, 200, 1500, lambda x: np.exp(-x / 0.1)), o + 23.3, 0.25)
add(sfx, pop(1300, 700, 0.12), o + 23.8, 0.24)
seq(pizz, [("D4", .5), ("F4", .5), ("A4", .5), ("D5", .5)], o + 23.9, BEAT, 0.28)
add(sfx, pop(620, 260), o + 24.2, 0.28)
for t in (25.2, 27.3):
    for k in range(7):
        add(sfx, pop(1500 + 120 * (k % 3), 900, 0.07), o + t + k * 0.2, 0.08)
seq(music_box, [("C5", 1), ("A4", 1), ("F4", 1), ("A4", 1)], o + 25.0, BEAT, 0.18)
seq(music_box, [("G4", 1), ("Bb4", 1), ("A4", 2)], o + 25.0 + BAR, BEAT, 0.18)
chord_pads(["F", "C"], o + 25.0, BAR, 0.06)

# E: "After a while…" — warm theme A
add(sfx, glock(hz("A6"), 2.0), o + 29.6, 0.08)
add(sfx, paper(0.5), o + 30.3, 0.2)
for i, bar in enumerate(A[:3]):
    seq(music_box, bar, o + 29.9 + i * BAR, BEAT, 0.22)
walk(["F", "Dm", "Bb"], o + 29.9, BAR, BEAT, 0.22, steps=(0, 2))
chord_pads(["F", "Dm", "Bb"], o + 29.9, BAR, 0.08)
for k in range(5):
    add(sfx, woodblock(700 + 90 * k, 0.07), o + 31.4 + k * 0.32, 0.08)
for t in (32.2, 32.8, 33.4):
    add(sfx, pop(1100, 600, 0.12), o + t, 0.14)

# F: the memory — a slow music-box waltz in D minor
WB = 0.66  # waltz beat
waltz = [[("A4", 2), ("D5", 1)], [("C5", 2), ("A4", 1)], [("Bb4", 2), ("G4", 1)], [("A4", 3)],
         [("F4", 2), ("A4", 1)], [("G4", 2), ("E4", 1)], [("F4", 2), ("D4", 1)], [("E4", 3)]]
wch = ["Dm", "F", "Gm", "A", "Dm", "C", "Bb", "A"]
t0 = o + 36.0
for rep in range(1):
    for i, (bar, c) in enumerate(zip(waltz, wch)):
        tb = t0 + (rep * 8 + i) * 3 * WB
        seq(music_box, bar, tb, WB, 0.2)
        add(music, pizz(hz(CH[c][0])), tb, 0.2)
        for k in (1, 2):
            add(music, pizz(hz(CH[c][1]) * 2, 0.4), tb + k * WB, 0.08)
        add(music, pad([hz(n) * 2 for n in CH[c]], 3 * WB + 0.9), tb, 0.06)
add(sfx, whoosh(1.6, 1500, 300, rise=False), o + 35.6, 0.08)
add(sfx, paper(0.5), o + 36.7, 0.18)
add(sfx, pop(600, 260), o + 38.0, 0.24)
add(sfx, pop(520, 220), o + 40.1, 0.24)
for i in range(7):
    add(sfx, crunch(0.05), o + 42.3 + i * 0.34, 0.03)
add(sfx, whoosh(2.0, 300, 1100), o + 43.6, 0.07)
for i in range(18):
    add(sfx, crunch(0.03), o + 45.0 + i * 0.36, 0.012)
# "Bye!": a single high note, then the waltz ends on a held chord
add(sfx, pop(1400, 900, 0.1), o + 51.6, 0.16)
add(music, glock(hz("A6"), 3.0), o + 51.7, 0.1)
add(music, pad([hz(n) * 2 for n in CH["Dmadd9"]], 5.5, 1.0, 2.5), o + 52.0, 0.08)
# page out: the colored page, a soft rising figure into page 3
add(sfx, paper(0.6), o + 55.85, 0.16)
add(sfx, whoosh(2.4, 900, 200, rise=True), o + 56.6, 0.07)
for k, n in enumerate(["D4", "F4", "A4", "C5", "E5"]):
    add(music, music_box(hz(n), 3.0), o + 56.4 + k * 0.5, 0.13)

# ================================================================== PAGE 3 (push away; the light goes out)
o = PAGE[3]
SB = 0.86  # sad theme beat (70 bpm)
S = [[("A4", 1), ("F4", 1), ("G4", 1), ("E4", 1)], [("F4", 1), ("D4", 1), ("E4", 2)],
     [("F4", 1), ("A4", 1), ("D5", 1), ("C5", 1)], [("Bb4", 1), ("A4", 1), ("G4", 1), ("E4", 1)],
     [("F4", 1.5), ("E4", 0.5), ("D4", 2)]]
Sch = ["Dm", "Bb", "Dm", "Gm", "A7"]

add(sfx, paper(0.9), o + 0.05, 0.24)
add(sfx, whoosh(2.4, 200, 1200), o + 1.9, 0.08)
sparkle(o + 3.45, 4, 988, 1.122, 0.18, 0.1)
chord_pads(["Dm"], o + 2.4, 2.4, 0.07)

# A: "Wu Wu Wu Wu Wu"
for i, bar in enumerate(S[:2]):
    seq(music_box, bar, o + 4.4 + i * 4 * SB, SB, 0.2)
chord_pads(Sch[:2], o + 4.4, 4 * SB, 0.08)
for k in range(5):
    add(sfx, sob(360 - 12 * k), o + 4.6 + k * 0.4, 0.2)
for t in np.arange(5.0, 10.2, 0.8):
    add(sfx, glock(hz("E7"), 0.4), o + t + 0.55, 0.035)

# B: the close-ups — heartbeat, a held chord, the tears
add(sfx, whoosh(0.6, 1200, 300, rise=False), o + 9.75, 0.08)
heartbeat(o + 10.2, 7, 0.95, 0.35)
add(music, pad([hz(n) * 2 for n in CH["Dmadd9"]], 7.5, 1.5, 2.0), o + 9.9, 0.09)
for t in (10.6, 11.55, 12.5):
    add(music, glock(hz("A6"), 1.4), o + t, 0.06)
add(sfx, thud(0.3, 60), o + 13.4, 0.25)
add(music, slide_whistle(0.8, 1400, 700) * 0.4, o + 13.75, 0.1)
for t in np.arange(14.4, 16.9, 0.7):
    add(sfx, glock(hz("C7"), 0.4), o + t, 0.05)

# C: the candle bounds in, "Let's go play!" — "NO!"
seq(music_box, [("A4", .5), ("C5", .5), ("F5", .5), ("E5", .5), ("D5", .5), ("C5", .5), ("A4", 1)], o + 17.0, BEAT, 0.18)
walk(["F"], o + 17.0, BAR, BEAT / 2, 0.18, steps=range(8))
for t in np.arange(16.8, 18.2, 0.24):
    add(sfx, woodblock(1000, 0.05), o + t, 0.04)
add(sfx, boing(380, 0.32), o + 18.45, 0.2)
add(sfx, pop(900, 420), o + 18.8, 0.3)
stab(o + 21.05)
add(sfx, pop(420, 180), o + 21.1, 0.3)
add(music, low_drone(3.2, ("D2", "Ab2"), 0.1), o + 21.3)

# D: "You do not bother me!"
add(sfx, whoosh(0.5, 500, 3500), o + 24.0, 0.2)
add(sfx, thud(0.3, 100), o + 24.5, 0.3)
for t in (25.05, 25.45):
    add(sfx, thud(0.25, 120), o + t + 0.3, 0.3)
stab(o + 25.1, ("D3", "G#3", "D4", "F4"), 0.32)
add(sfx, noise_band(0.5, 60, 400, lambda x: np.exp(-x / 0.15)), o + 25.15, 0.5)
add(sfx, noise_band(0.25, 2000, 8000, lambda x: np.exp(-x / 0.05)), o + 25.25, 0.12)
for i in range(12):
    add(music, pizz(hz(["D3", "D3", "F3", "D3"][i % 4]), 0.4), o + 26.0 + i * 0.3, 0.2)
add(music, low_drone(4.5, ("D2", "A2"), 0.08), o + 26.0)

# E: "Get out!"
add(sfx, whoosh(0.5, 500, 3500), o + 30.4, 0.2)
stab(o + 30.9, ("C#4", "D4", "G#4", "D5"), 0.38)
add(sfx, noise_band(0.8, 40, 300, lambda x: np.exp(-x / 0.25)), o + 30.95, 0.6)
add(music, slide_whistle(2.2, 880, 440) * 0.3, o + 32.2, 0.06)
add(music, pad([hz("D3") * 2, hz("A3") * 2], 3.4, 1.0, 1.5), o + 32.0, 0.07)

# F–H: he walks away — the sad theme, slowly, as the dusk comes down
add(sfx, whoosh(0.5, 500, 3500), o + 35.0, 0.18)
add(sfx, paper(0.5), o + 35.5, 0.18)
breath(o + 36.2, 1.1, 0.06, 300, 1800)
t0 = o + 35.8
for i, (bar, c) in enumerate(zip(S[:4], Sch[:4])):
    seq(music_box, bar, t0 + i * 4 * SB, SB, 0.21)
    add(music, pad([hz(n) * 2 for n in CH[c]], 4 * SB + 0.9), t0 + i * 4 * SB, 0.08)
    add(music, pizz(hz(CH[c][0]) / 2, 0.9), t0 + i * 4 * SB, 0.22)
for (a0, a1, g) in ((37.8, 39.4, 0.05), (39.2, 43.6, 0.035), (43.4, 48.6, 0.02)):
    for t in np.arange(a0, a1, 0.44):
        add(sfx, crunch(0.05), o + t, g)
for t, g in ((39.0, 0.18), (43.2, 0.16)):
    add(sfx, whoosh(0.5, 500, 3500), o + t, g)
for t in (39.5, 43.7):
    add(sfx, paper(0.5), o + t, 0.16)
add(music, slide_whistle(4.0, 1320, 660) * 0.25, o + 44.2, 0.05)

# I: "Alas…" — the night, the caption, the far light goes out
wind_n = noise_band(12.0, 150, 900, lambda x: (0.5 + 0.5 * np.sin(2 * np.pi * 0.11 * x)) * np.minimum(1, x / 2) * np.minimum(1, (12 - x) / 2))
add(sfx, wind_n, o + 48.2, 0.05)
add(music, pad([hz(n) * 2 for n in CH["Dmadd9"]], 11.0, 2.0, 3.0), o + 48.4, 0.08)
for k, (t, f) in enumerate(((49.3, 1700), (49.6, 1900), (49.9, 2100), (50.25, 1500))):
    add(sfx, pop(f, f * 0.6, 0.08), o + t, 0.1)
for t, n in ((50.3, "D5"), (51.6, "A4"), (52.9, "F4"), (54.2, "E4"), (55.5, "D4"), (56.8, "A4")):
    add(music, music_box(hz(n), 3.0), o + t, 0.16)
add(sfx, paper(0.5), o + 52.9, 0.16)
for i in range(5):
    add(sfx, scribble(0.8), o + 53.6 + i * 1.02, 0.07)
add(music, glock(hz("D6"), 4.0), o + 57.7, 0.1)
add(music, slide_whistle(1.6, 1175, 587) * 0.3, o + 57.8, 0.05)
add(sfx, noise_band(1.6, 1500, 6000, lambda x: np.sin(np.pi * np.clip(x / 1.6, 0, 1)) ** 2), o + 58.6, 0.035)
add(sfx, paper(0.6), o + 59.3, 0.14)
add(music, pad([hz(n) * 2 for n in CH["Dm"]], 5.5, 1.5, 3.0), o + 60.0, 0.07)

# ================================================================== PAGE 4 (the storm, the search)
o = PAGE[4]
add(sfx, paper(0.9), o + 0.05, 0.24)
add(sfx, whoosh(2.4, 200, 1200), o + 1.9, 0.08)
thunder(o + 3.2, 0.25, crack=False, length=3.0)
add(music, low_drone(8.0, ("D2", "A2"), 0.11), o + 3.5)

# rain from the first thunder until the corner, then only drips under the eaves
lvl = lambda x: 0.5 + 0.5 * min(1.0, x / 3.0) if x < 30 else (1.0 if x < 34 else 0.7)
rain_bed(o + 5.3, o + 51.2, lvl, 404)
for t, g in ((5.3, 1.0), (6.8, 0.9), (8.3, 0.85)):
    thunder(o + t, g)
add(music, low_drone(10.0, ("D2", "Eb2"), 0.08), o + 8.0)

# B: "What happen?" — thunder rolling off
thunder(o + 10.95, 0.8)
for k, t in enumerate((12.0, 12.2, 12.4, 12.7)):
    add(sfx, pop(1500 + 200 * k, 900, 0.08), o + t, 0.1)
for t in (13.7, 14.9, 16.1):
    thunder(o + t - 0.05, 0.35, crack=False, length=3.0)
for i, n in enumerate(["D4", "F4", "E4", "D4", "C#4", "D4"]):
    add(music, music_box(hz(n), 2.0), o + 12.8 + i * 0.9, 0.14)

# C/D: the rain, the bolts
add(sfx, whoosh(0.5, 500, 3500), o + 18.2, 0.18)
add(sfx, whoosh(0.5, 500, 3500), o + 21.0, 0.18)
for t in (21.55, 22.1, 22.6, 23.05, 23.5):
    thunder(o + t, 0.55, length=2.0)

# E: the search — walking pizzicato in D minor, the umbrella in the rain
add(sfx, whoosh(0.5, 500, 3500), o + 24.0, 0.18)
t0 = o + 24.2
walk(["Dm", "Dm", "Gm", "A7"], t0, BAR, BEAT, 0.26)
for i, bar in enumerate([[("D5", 1), ("F5", 1), ("E5", 1), ("C5", 1)], [("D5", 2), ("A4", 2)],
                         [("Bb4", 1), ("D5", 1), ("C5", 1), ("Bb4", 1)], [("A4", 3), (None, 1)]]):
    seq(music_box, bar, t0 + i * BAR, BEAT, 0.2)
chord_pads(["Dm", "Dm", "Gm", "A7"], t0, BAR, 0.06)
for t in np.arange(24.1, 26.9, 0.36):
    splash_step(o + t, 0.1)
add(sfx, pop(700, 300), o + 28.4, 0.28)
thunder(o + 29.6, 0.3, crack=False, length=3.0)
for t in np.arange(31.0, 32.6, 0.36):
    splash_step(o + t, 0.08)

# F: "On that day…", "Hello?" / "Are you in?"
add(sfx, paper(0.5), o + 32.2, 0.18)
for i in range(3):
    add(sfx, scribble(0.5), o + 32.5 + i * 0.8, 0.07)
for t in (34.4, 34.65, 36.0, 36.25):
    knock(o + t)
add(sfx, pop(640, 280), o + 34.6, 0.26)
ticks(o + 35.4, 3, 0.3, 1600, 0.07)
add(sfx, pop(560, 240), o + 36.2, 0.26)
ticks(o + 37.1, 3, 0.3, 1400, 0.06)
thunder(o + 35.2, 0.2, crack=False, length=2.5)
add(music, pad([hz(n) * 2 for n in CH["Gm"]], 6.0, 1.5, 2.0), o + 32.0, 0.06)

# G: found in a corner — tender, the sad theme in the rain
add(sfx, whoosh(1.4, 1200, 300, rise=False), o + 38.2, 0.06)
t0 = o + 39.0
for i, (bar, c) in enumerate(zip(S[:3], Sch[:3])):
    seq(music_box, bar, t0 + i * 4 * SB, SB, 0.18)
    add(music, pad([hz(n) * 2 for n in CH[c]], 4 * SB + 0.9), t0 + i * 4 * SB, 0.07)
add(sfx, paper(0.5), o + 42.3, 0.16)
for i in range(6):
    add(sfx, scribble(0.7), o + 42.9 + i * 0.95, 0.06)
add(sfx, pop(700, 320), o + 48.6, 0.26)
add(music, music_box(hz("F5"), 3.0), o + 49.4, 0.14)
add(music, pad([hz(n) * 2 for n in CH["Bb"]], 5.0, 1.0, 2.5), o + 49.0, 0.07)
add(sfx, paper(0.6), o + 50.2, 0.14)

# ================================================================== PAGE 5 (the reunion, HOPE)
o = PAGE[5]
add(sfx, paper(0.9), o + 0.05, 0.24)
add(sfx, whoosh(2.4, 200, 1200), o + 1.9, 0.08)
rain_bed(o + 3.0, o + 28.8, lambda x: 1.0 if x < 22 else max(0.0, 1 - (x - 22) / 3.8), 505)

# A: running flat out — an urgent ostinato
for i in range(28):
    n = ["D3", "A3", "D3", "F3"][i % 4]
    add(music, pizz(hz(n), 0.35), o + 4.5 + i * 0.3, 0.24)
add(music, low_drone(8.0, ("D2", "A2"), 0.09), o + 4.3)
for t in np.arange(4.5, 9.1, 0.12):
    splash_step(o + t, 0.07)
seq(music_box, [("D5", 1), ("E5", 1), ("F5", 1), ("G5", 1), ("A5", 2), ("G5", 1), ("F5", 1)], o + 6.0, 0.3 * 2, 0.16)
thunder(o + 10.6, 0.6)
# B: lightning
add(sfx, whoosh(0.5, 500, 3500), o + 11.9, 0.18)
for t in (12.45, 12.95, 13.4, 13.85):
    thunder(o + t, 0.5, length=2.0)

# C: "I am late!" — the music turns toward F major
add(sfx, whoosh(0.5, 500, 3500), o + 14.5, 0.18)
for t in np.arange(14.7, 16.0, 0.16):
    splash_step(o + t, 0.08)
add(sfx, thud(0.35, 90), o + 16.0, 0.3)
add(sfx, pop(760, 320), o + 16.4, 0.3)
for t in np.arange(16.3, 22.0, 0.44):
    breath(o + t, 0.2, 0.05)
chord_pads(["Dm", "Bb", "C"], o + 16.8, 2.2, 0.08)
seq(music_box, [("A4", 1), ("C5", 1), ("F5", 1), ("E5", 1)], o + 17.2, 0.75, 0.18)
seq(music_box, [("D5", 1), ("C5", 1), ("A4", 2)], o + 20.2, 0.75, 0.18)
add(music, glock(hz("C6"), 2.0), o + 19.0, 0.08)

# D: the hug — theme A slow and warm; the rain stops
HB = 0.75
t0 = o + 23.0
for i, bar in enumerate(A[:3]):
    seq(music_box, bar, t0 + i * 4 * HB, HB, 0.21)
chord_pads(["F", "Dm", "Bb"], t0, 4 * HB, 0.1)
walk(["F", "Dm", "Bb"], t0, 4 * HB, HB, 0.18, steps=(0, 2))
add(sfx, pop(620, 260), o + 23.4, 0.26)
for k in range(4):
    add(sfx, sob(330 - 10 * k, 0.3), o + 23.6 + k * 0.45, 0.1)
add(sfx, pop(560, 240), o + 26.3, 0.26)
add(sfx, pop(700, 300), o + 29.3, 0.26)
for t in (30.3, 30.75, 31.2):
    add(sfx, pop(1100, 600, 0.12), o + t, 0.14)
sparkle(o + 30.2, 4, 1397, 1.19, 0.12, 0.1)

# E: the flame comes back — magic, then theme A in full color
add(sfx, whoosh(0.5, 500, 3500), o + 32.6, 0.16)
add(music, pad([hz(n) * 2 for n in CH["Csus"]], 1.8, 0.8, 0.6), o + 32.8, 0.08)
ignite(o + 34.2)
add(music, glock(hz("F6"), 3.0), o + 34.25, 0.12)
t0 = o + 34.6
for i, bar in enumerate(A):
    seq(music_box, bar, t0 + i * BAR, BEAT, 0.24, sparkle_oct=True)
walk(["F", "Dm", "Bb", "C", "F", "Bb"], t0, BAR, BEAT, 0.26)
chord_pads(["F", "Dm", "Bb", "C", "F", "Bb"], t0, BAR, 0.1)
add(sfx, pop(820, 360), o + 35.0, 0.3)
add(sfx, boing(380, 0.32), o + 36.0, 0.2)
add(sfx, pop(700, 300), o + 38.6, 0.3)
sparkle(o + 39.0, 5, 1568, 1.122, 0.1, 0.1)

# F: "We always are best friends" / "Yes, forever~" (theme A from E is still under it)
add(sfx, glock(hz("C7"), 2.0), o + 42.6, 0.06)
add(sfx, pop(640, 280), o + 43.6, 0.28)
add(sfx, pop(760, 330), o + 46.2, 0.28)
for t in (47.6, 48.1, 48.6):
    add(sfx, pop(1100, 600, 0.12), o + t, 0.14)
seq(music_box, [("C5", 1), ("A4", 1), ("F4", 1), ("A4", 1)], o + 49.0, BEAT, 0.2)
chord_pads(["F"], o + 49.0, BAR, 0.1)

# G: "his name is HOPE" — the whole theme, rising to the name
t0 = o + 51.4
for i, bar in enumerate(A[:4]):
    seq(music_box, bar, t0 + i * BAR, BEAT, 0.24, sparkle_oct=True)
walk(["F", "Dm", "Bb", "C"], t0, BAR, BEAT, 0.24)
chord_pads(["F", "Dm", "Bb", "C"], t0, BAR, 0.11)
add(sfx, paper(0.5), o + 52.9, 0.16)
add(sfx, scribble(1.6), o + 53.5, 0.07)
add(sfx, scribble(1.6), o + 55.5, 0.07)
ignite(o + 55.6)
t1 = t0 + 4 * BAR  # 61.0: the cadence home
for k, n in enumerate(["F4", "A4", "C5", "F5", "A5"]):
    add(music, music_box(hz(n), 4.5), t1 + k * 0.18, 0.2)
add(music, pad([hz(n) * 2 for n in CH["Fadd9"]], 8.0, 0.6, 4.0), t1, 0.12)
add(music, pizz(hz("F2"), 1.2), t1, 0.35)
add(music, glock(hz("C7"), 3.0), t1 + 0.9, 0.12)

# page out: the colored page, the theme's opening once more, slowly
add(sfx, paper(0.6), o + 64.3, 0.14)
seq(music_box, [("C5", 1), ("A4", 1), ("F4", 1), ("A4", 1), ("Bb4", 1), ("D5", 1), ("C5", 2)], o + 64.6, 0.75, 0.16)
chord_pads(["F", "Bb"], o + 64.5, 3.0, 0.08)
# the end card: the title once more, a last chord
add(sfx, whoosh(3.0, 900, 200, rise=True), o + 65.3, 0.07)
for k, n in enumerate(["F4", "A4", "C5", "F5", "A5", "C6"]):
    add(music, music_box(hz(n)), o + 70.8 + k * 0.3, 0.18)
add(sfx, scribble(0.95), o + 71.4, 0.18)
add(sfx, pop(760, 300), o + 72.3, 0.3)
add(sfx, scribble(1.05), o + 72.5, 0.18)
for k, n in enumerate(["F4", "A4", "C5", "F5"]):
    add(music, music_box(hz(n), 4.0), o + 73.2 + k * 0.16, 0.18)
add(music, pad([hz(n) * 2 for n in CH["F"]], 4.0, 0.4, 2.5), o + 73.2, 0.1)
add(music, glock(hz("F6"), 3.0), o + 73.6, 0.1)
