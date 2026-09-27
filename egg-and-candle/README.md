# an egg & a candle

A HyperFrames animation of a five-page hand-drawn comic (about 5 minutes,
1920×1080). Each page opens on the real ink page landing on a desk, pushes into
its first panel, plays the panels as animated scenes, and pulls back to the
same page in color. The film ends on the title card.

| Page | Composition | Starts at | Story |
| --- | --- | --- | --- |
| 1 | `compositions/page1.html` | 0.0 s | title, meeting, the cold day, the race |
| 2 | `compositions/page2.html` | 54.3 s | rolling, the crash, stuck in the yolk, laughing, the memory of a friend leaving |
| 3 | `compositions/page3.html` | 114.6 s | crying, the close-ups, "NO!" / "Get out!", the candle walks away until his flame goes out |
| 4 | `compositions/page4.html` | 178.3 s | the storm, the search with an umbrella, found in a corner |
| 5 | `compositions/page5.html` | 232.9 s | "I am late!", the hug, the flame comes back, "his name is HOPE", end card |

Each page starts 1.5 s before the previous one ends: its ink sheet slides in
over the previous page's colored sheet while that one is still on screen.

## Pipeline

| Step | Command | Output |
| --- | --- | --- |
| Trace + color every character, bubble and caption on a page | `python3 scripts/extract_art.py source/pageN.json` | `assets/art/pN/*.svg`, `manifest.json` |
| Trace the full page (bookends) | `python3 scripts/page_art.py source/pageN.json` | `assets/art/pN/page-ink.svg`, `panels.json` |
| Print the sprite table used by a composition | `python3 scripts/art_table.py N` | JS `ART` table |
| List an element's paint regions (to pick seeds) | `python3 scripts/regions.py source/pageN.json <id> …` | text |
| Contact sheet of a page's sprites | `python3 scripts/sheet.py N sheet.png` | PNG |
| Score + effects for the whole film | `python3 scripts/score.py` | `assets/audio/score.m4a` |
| Check that no page timeline got shifted | `node scripts/check_timelines.mjs` | report |
| Validate / render | `npm run check` · `npm run render` | `renders/*.mp4` |

Requires Python 3 with numpy, scipy, opencv-python-headless; `potrace`;
`ffmpeg`; Node 22 (and the `playwright` package for the timeline check).

The comic's page photos (`source/pages/page1.jpg` … `page5.jpg`) and everything
traced from them (`assets/art/`, `renders/`) are not committed, because this
repository is public. Put the pages back in `source/pages/` and run the first
two steps for each page to rebuild the art before rendering.

### How the art is made

1. The photo's lighting is flattened (divide by a dilated/blurred paper
   estimate). Pages 2–5, shot in shadow, first subtract a large morphological
   opening ("tophat") to remove the camera's tone-mapping halos.
2. The ink map is upscaled 4× and each stroke keeps its half-of-local-maximum
   core, so faint pencil-light faces and bold outlines get a consistent weight.
3. Per element (boxes in `source/pageN.json`): neighbours cut by the box edge,
   stray specks and rain streaks are dropped; animated parts (flames, tears,
   the far friend on the road) are lifted onto their own layers with a pivot.
   A spec can also clip, erase, cut or mend strokes, drop leftover pieces, or
   seal an outline the panel edge cuts open (for close-ups).
4. Every enclosed hole of the drawing is a paint region; seeds in the page spec
   choose the paint (wax, melted cap, yolk, umbrella stripes, the rainbow
   bridge…), the rest takes the element's base color.
5. potrace vectorizes ink and paint into one layered SVG per element.

### Composition

Each page composition builds its scenes from its sprite table (bottom-centre
anchors, page-pixel boxes × the panel's zoom) with the shared kit
`assets/lib/ec.js` / `ec.css`, and drives one paused GSAP timeline. Motion is
property tweens only (the renderer seeks with events suppressed), with seeded
randomness for snow, rain, flicker and puffs. A page's opening push-in and
closing pull-back share its coordinates with the first and last panel, so the
drawing and the animated scene line up at the cut.

GSAP moves every child of a timeline later when any tween is placed before
time 0, which would silently delay a whole page; `scripts/check_timelines.mjs`
builds each page in headless Chromium and reports such a shift.

Fonts: Patrick Hand (SIL OFL, `assets/fonts/PatrickHand-OFL.txt`) for the "&"
in the title; every other word on screen is the artist's own lettering, kept as
written.
