"""Count full-screen flashes in a rendered video (photosensitivity check).

A flash is a pair of opposing changes of at least 10% relative luminance
where the darker state is below 0.80 (the WCAG 2.3.1 "general flash" rule),
measured on the frame's mean relative luminance, so only large-area
changes (lightning) count. Reports the worst one-second window; more than
3 flashes in any second fails.

Usage: python3 scripts/flash_check.py renders/egg-and-candle.mp4
"""
import subprocess
import sys

import numpy as np

path = sys.argv[1]
W, H, FPS = 64, 36, 30
raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-vf", f"fps={FPS},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                     check=True, capture_output=True).stdout
frames = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3).astype(np.float32) / 255
lin = np.where(frames <= 0.04045, frames / 12.92, ((frames + 0.055) / 1.055) ** 2.4)
lum = (lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)).mean(axis=(1, 2))

# turning points: a new transition once luminance moves 0.1 against the current trend
transitions = []  # (frame index, direction)
lo = hi = lum[0]
trend = 0
for i, v in enumerate(lum):
    if trend >= 0:
        if v > hi:
            hi = v
        if hi - v >= 0.1 and min(v, hi) < 0.8:
            transitions.append((i, -1)); trend = -1; lo = v
    if trend <= 0:
        if v < lo:
            lo = v
        if v - lo >= 0.1 and min(v, lo) < 0.8:
            transitions.append((i, 1)); trend = 1; hi = v

idx = np.array([t for t, _ in transitions])
worst, at = 0.0, 0.0
for k, t in enumerate(idx):
    n = np.sum((idx >= t) & (idx < t + FPS))
    if n / 2 > worst:
        worst, at = n / 2, t / FPS
print(f"{len(transitions) // 2} flashes in {len(lum) / FPS:.1f} s; worst one-second window: {worst:g} flashes at {at:.2f} s -> {'FAIL' if worst > 3 else 'ok'}")
sys.exit(1 if worst > 3 else 0)
