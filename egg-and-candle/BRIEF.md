---
workflow: general-video
flow: companion
storyboard: no
message: "The hand-drawn comic of an egg and her candle friend, brought to life exactly as drawn"
aspect: 1920x1080
language: en
length: sample = page 1 of 5 (57 s); full film after approval
---

## Intent

Animate the user's 5-page hand-drawn comic (black ink on paper, English
lettering) with HyperFrames + FFmpeg. The characters, poses, lettering and
story come from the comic itself; color is free to choose. First deliver a
sample covering the opening page(s), then animate the whole story once the
look is approved.

## Assets

- source/pages/page1.jpg … page5.jpg — photos of the five comic pages (from the user's .docx); every sprite is traced from these. Kept out of git (public repo) until the owner agrees to publish.

## Customizations

- Original line art is vectorized (not redrawn); fills added under the ink.
- Each page opens on the real comic page and closes on the same page in color.
- Original score and effects synthesized locally (no stock audio).

## Notes

- Keep the artist's English lettering as drawn (including spelling) unless the user asks for corrections or Chinese subtitles.
- Story order: page 1 (meet, cold day, race) → 2 (roll, stuck, flashback) → 3 (push away, flame dies) → 4 (storm, search) → 5 (reunion, "his name is HOPE").
