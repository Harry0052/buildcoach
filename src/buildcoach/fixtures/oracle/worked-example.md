# Oracle for Desk Ledge geometry

This note is the reference method. It does not call the detector.

## Relative edge angle

Tag corners are ordered top-left, top-right, bottom-right, bottom-left in the tag frame.
The +X edge is corner 0 to corner 1. Its image angle is `atan2(y1 - y0, x1 - x0)` in degrees.
The relative angle is the subject angle minus the reference angle, wrapped into (-180, 180].

Worked square, no perspective:

- Base corners: (0, 0), (100, 0), (100, 100), (0, 100). +X vector (100, 0). Angle `atan2(0, 100) = 0°`.
- Upright corners: (0, -160), (100, -160), (100, -60), (0, -60). +X vector (100, 0). Angle `0°`.
- Relative angle: `0 - 0 = 0°`. The kit band is `0 ± 12°`, so this pair supports `upright-orientation`.

Quarter turn of the upright, still using the same base:

- Upright corners after a clockwise quarter turn of the bits, with the top edge now running down the image: (0, 0), (0, 100), (-100, 100), (-100, 0).
- +X vector (0, 100). Angle `atan2(100, 0) = 90°`.
- Relative angle: `90°`, outside `±12°`, so the rule is a visible mismatch.

A roll of the camera adds the same number to both angles, so the difference stays `0°` for the correct pair. Raster resampling may move the measured difference by a fraction of a degree. The fixture gate allows 2° between the unrolled and rolled correct photos.

## Position in base-tag widths

Map the reference corners onto the unit square (0, 0), (1, 0), (1, 1), (0, 1) with a homography.
Transform the subject center. +Y points from the reference top edge toward its bottom edge.

Worked identity homography:

- Reference corners are already the unit square.
- Subject corners: (0, -1.5), (1, -1.5), (1, -0.5), (0, -0.5).
- Center: (0.5, -1.0).

The lip rule on the fixture uses the band stored in `kit/desk-ledge.json`. A center outside that band is a placement mismatch. A center farther than `max_abs_center` on either axis is an implausible layout even before the band is applied.

## What the photos must do

| Session | Completed | Why, from the rules above |
| --- | --- | --- |
| place-base | yes | Top view, tag 0 present. |
| seat-top-only | no | Tag 1 is absent. Request view `left`. |
| seat-complete | yes | Left view adds tag 1 parallel to tag 0. |
| seat-rolled | yes | Same pair after a camera roll. Relative angle stays inside 12°. |
| seat-rotated | no | Quarter-turned tag 1. Orientation mismatch on that image. |
| seat-occluded | no | Tag 1 hidden in both views. Request `left`. Zero completions. |
| seat-contradictory | no | One clean parallel view and one clean quarter turn. Retake. Area is ignored. |
| seat-mirror | no | Horizontal mirror. No completion from the flipped bits. |
| seat-duplicate | no | Two copies of tag 0. |
| seat-wrong-id | no | Tag 2 is in the upright slot. |
| seat-far | no | Tag 1 is too far from tag 0 in tag widths. |
| seat-tiny | no | Tags are under 48 px. |
| lip-ok | yes | Front view, tag 2 inside the placement band. |
| lip-misplaced | no | Tag 2 is outside the band. |
