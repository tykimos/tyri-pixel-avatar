# Greeting review

The 3 GIFs each display all 9 directions simultaneously using the repaired v6 sprite atlas with 12 mouth shapes.
Mouth positions and down-view sizes were corrected; glasses are reinforced.

- Korean: 안녕, 난 타이리야, 반가워
- English: Hi, I’m Tyri. Nice to meet you!
- Japanese: こんにちは、タイリだよ。よろしくね。

GIF has no sound. Cues are hand-authored phonetic approximations, not measured
speech timings. The Japanese sentence is a natural greeting equivalent, not
a word-by-word translation. Tyri is approximated as “타이리 / タイリ”.

`full_sheet_small.png` is a nearest-neighbor 50% overview of all 324 frames.
Rows follow manifest direction order; each row has open, half-closed and closed
eye groups, each containing the same 12 mouth states in manifest order.

Repair checks: all 324 mouth layers stay inside the skin region and preserve the
head silhouette. Side-view mouth projection remains approximate and low-resolution
lip contours remain stylized. Real multilingual audio synchronization remains untested.

All files are covered by the repository's personal/noncommercial research license.

## Centered UP base (v6)

The UP pose now uses a dedicated frontal, upward-pitched source with centered nose, glasses and mouth landmarks. Other eight directions are unchanged. See `up_before_after.png`. The pitch is stylized, not a calibrated 3D angle.

## Emotions and winks v2

- `emotions_contact.png`: 24 expressions, frontal view.
- `happy_9directions.png`: closed smiling eyes correctly fitted in all nine directions.
- `emotions_9directions.gif`: 24 expressions in all directions with speech-mouth tests.
- `winks_9directions.gif`: anatomical left/right winks.

The lens interiors are fully cleared before drawing, preventing leftover irises.
These GIFs are silent and use manual timing.

`eye_repair_check.png` compares original open eyes, repaired closed lids, sleepy and wink states across all nine directions.
