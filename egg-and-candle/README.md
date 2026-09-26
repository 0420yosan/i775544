# an egg & a candle

A HyperFrames animation of a five-page hand-drawn comic. This directory holds
the page-1 sample: the title, the ink page arriving on a desk and pushing into
panel 1, the six panels animated, then the whole page again in color.

## Pipeline

| Step | Command | Output |
| --- | --- | --- |
| Trace + color every character, bubble and caption on a page | `python3 scripts/extract_art.py source/page1.json` | `assets/art/p1/*.svg`, `manifest.json` |
| Trace the full page (bookends) | `python3 scripts/page_art.py source/page1.json` | `assets/art/p1/page-ink.svg`, `panels.json` |
| Print the sprite table used by the composition | `python3 scripts/art_table.py 1` | JS `ART` table |
| Contact sheet of all sprites | `python3 scripts/sheet.py 1 sheet.png` | PNG |
| Score + effects | `python3 scripts/score.py` | `assets/audio/page1-score.m4a` |
| Validate / render | `npm run check` · `npm run render` | `renders/*.mp4` |

Requires Python 3 with numpy, scipy, opencv-python-headless; `potrace`;
`ffmpeg`; Node 22.

The comic's page photos (`source/pages/page1.jpg` … `page5.jpg`) and everything
traced from them (`assets/art/`, `renders/`) are not committed, because this
repository is public. Put the pages back in `source/pages/` and run the first
two steps to rebuild the art before rendering.

### How the art is made

1. The photo's lighting is flattened (divide by a dilated/blurred paper estimate).
2. The ink map is upscaled 4× and each stroke keeps its half-of-local-maximum
   core, so faint pencil-light faces and bold outlines get a consistent weight.
3. Per element (`source/page1.json` boxes): neighbours cut by the box edge,
   stray specks and snow dots are dropped; animated parts (flames, arms) are
   lifted onto their own layers with a pivot.
4. Every enclosed hole of the drawing is a paint region; seeds in the page spec
   choose the paint (scarf, earmuffs, wax cap…), the rest takes the element's
   base color.
5. potrace vectorizes ink and paint into one layered SVG per element.

### Composition

`compositions/page1.html` builds each scene from the sprite table (bottom-centre
anchors, page-pixel boxes × scale) and drives one paused GSAP timeline. Motion
is property tweens only (the renderer seeks with events suppressed), with
seeded randomness for snow, flicker and puffs. The opening push-in and the
closing pull-back share the page's coordinates with panels 1 and 6, so the
drawing and the animated scene line up exactly at the cut.

Fonts: Patrick Hand (SIL OFL, `assets/fonts/PatrickHand-OFL.txt`) for the one
typed line; every other word on screen is the artist's own lettering.
