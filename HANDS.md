# 타이리 (Tyri) — independent hand sprites

12 gestures: wave, write, peace, shush, heart, finger_heart, thumbs_up, ok, point, clap, thanks, cheer.

Open `hands_preview.html` locally to select a direction and gesture. No server is required. See `previews/hands_9directions.gif` and `previews/hands_contact.png` for previews.

## Integration

- `hands_atlas.png`: 128 × 384 transparent atlas; each cell 32 × 32.
- `hands.json`: four animation slots per gesture, 150 ms per slot; 9 direction placements.
- Draw the existing 64 × 64 face at (16, 8) on a 96 × 96 logical canvas, then draw the hand on top.
- Destination top-left = `directions[direction].positions[gesture] - gestures[gesture].anchor`.
- `shush` uses a fingertip anchor matched to each face's mouth. It is intentionally a held pose.
- Face expression, mouth viseme and hand gesture are independent. Use REST for shushing, or choose any existing emotion/viseme for other gestures.
- Disable image smoothing and display at integer scales.

```js
const g = hands.gestures[gesture];
const p = hands.directions[direction].positions[gesture];
const frame = Math.floor(timeMs / hands.duration_ms) % g.frames.length;
ctx.imageSmoothingEnabled = false;
ctx.drawImage(handAtlas, ...g.frames[frame],
  p[0] - g.anchor[0], p[1] - g.anchor[1], 32, 32);
```

Hands use a shared screen-facing view with direction-specific positions, not nine independently drawn hand perspectives. Animations use small pixel-grid rotations, translations and squash; the writing gesture is a pencil-motion loop rather than dynamically rendered text. The clap is a stylized squash loop. The face source pixels are unchanged.

## Rebuild and validation

Install Pillow, then run `python build_hands.py`. This extracts a 4 × 3 generated sheet from `sources/hands_source.png`, thresholds alpha, samples to a 32 px grid, quantizes each gesture, and exports individual PNGs under `hands/`, the atlas, JSON, HTML and previews. The release ZIP includes all 48 individual PNG slots. `hands_tests.json` records alpha and canvas-bounds checks for 432 combinations. Visual previews are reviewed separately; this does not validate live speech synchronization.

## Artwork provenance

Source generated with the built-in image generation tool. Prompt specification: transparent 4-column × 3-row sheet of hands only; warm peach skin, reddish-brown pixel outline; 12 gestures in the order above; clean five-finger anatomy; no face/body/text; chunky limited-palette pixel art. Generated source then sampled to the final native pixel grid.

## Usage conditions

The repository LICENSE applies. Personal and noncommercial research use only. Preserve the official character name **타이리 / Tyri** and include **타이리 (Tyri)** with the required attribution. Do not rename the character.
