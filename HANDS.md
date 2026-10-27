# 타이리 (Tyri) — face-adjacent hands v2

Hands are independent transparent layers. This revision replaces oversized, distant v1 hands with smaller hands next to the cheeks, lips and chin, using a shared warm 12-color palette.

12 gestures: wave, write, peace, shush, heart, finger_heart, thumbs_up, ok, point, clap, thanks, cheer.

Open `hands_preview.html` locally. Select head direction, gesture, and hand/surface. Previews: `previews/hands_contact.png`, `previews/hands_orientation.png`, and `previews/hands_9directions.gif`.

## Hand and surface conventions

- **right / left** always means the character's anatomical right / left. In the front view, the character's right hand is on the viewer's left.
- **palm** means the palm is visible to the viewer; **back** means the back of the hand is visible. These are separately drawn source images, not a mirrored palm pretending to be a back view.
- Eight single-hand gestures have `right_palm`, `right_back`, `left_palm`, `left_back` variants. Left hands are mirrored from the corresponding right-hand surface.
- Writing has `right_prop` and `left_prop` (dominant writing hand).
- Heart, clap and thanks use `pair`, representing both hands. These deliberately have no misleading single-hand selector.
- This provides two surface views, not a full 3D hand rotation for every head direction. Placement follows each direction's face anchors.

## Integration — v2 schema

- `hands_atlas.png`: 96 × 888 atlas; cells are **24 × 24**. 37 variants × 4 timing slots = 148 slots. Held poses can repeat.
- Single hands occupy at most 12 × 16 pixels before the small wave rotation. Paired gestures occupy at most 19 × 14 pixels.
- Draw the existing 64 × 64 face at **(8, 4)** on an **80 × 80** canvas, then draw the hand layer.
- The default anchor is the cell center; shush uses the fingertip, one pixel above the direction-specific mouth anchor.
- All hand positions are close to the face. Do not reuse v1 canvas offsets or 32-pixel source rectangles.

```js
const v = hands.gestures[gesture].variants[variant];
const p = hands.directions[direction].placements[gesture][variant].position;
const f = Math.floor(timeMs / hands.duration_ms) % v.frames.length;
ctx.imageSmoothingEnabled = false;
ctx.drawImage(handAtlas, ...v.frames[f],
  p[0] - v.anchor[0], p[1] - v.anchor[1], 24, 24);
```

Face expression, speech viseme and hand gesture remain independent. Shush is a held pose; REST is recommended. Writing is a small pencil-motion loop, not dynamically rendered text; clap is a stylized squash loop.

## Rebuild and checks

Install Pillow, then run `python build_hands.py`. The build uses `sources/hands_source.png` for paired gestures and writing, and `sources/hands_orientation_source.png` for single-hand surfaces. It exports `hands_v2/` with 148 individual PNG slots, an atlas, JSON, self-contained preview HTML and GIF/contact sheets. The v2 ZIP contains these files. The old v1 package is retained as an older release.

`hands_tests.json` checks canvas bounds for 1,332 compositions and binary transparency. These numerical checks do not prove anatomical correctness or visual quality. The front contact sheet and three-gesture hand/surface comparison were visually inspected. No live speech synchronization is tested here.

## Artwork provenance

The source sheet was generated with the built-in image generation tool. Final prompt specification: 4 × 4 transparent grid; eight right-hand gestures, each with separate palm/back drawings; palm thumb on viewer-left and back thumb on viewer-right where applicable; visible back fingernails; five-finger anatomy; small peach pixel art, brown outline; no decorations, arms, body or text. Left hands are mirrored only within the same surface. The source is sampled to native pixels and mapped to the shared palette.

## Usage conditions

The repository LICENSE applies: personal and noncommercial research only. Preserve **타이리 / Tyri** and include **타이리 (Tyri)** with the required attribution. Do not rename the character.
