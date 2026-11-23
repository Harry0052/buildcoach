# Validation

Recorded 2026-11-23 on this workspace host.

## Environment

| Item | Observed |
| --- | --- |
| OS | Linux 6.12.113+ x86_64, glibc 2.39 |
| Python | 3.12.3 |
| OpenCV | 4.12.0 via `opencv-python-headless==4.12.0.88` |
| NumPy | 2.2.6 |
| Fixture tree | 2.6 MB, 13 PNGs, 2,076,282 bytes of images |
| Dataset | Synthetic only, seed `20261123`. Not a phone-camera set and not an external benchmark. |

Tolerances are the kit values: relative edge angle `0 ± 12` degrees, lip center `[0.62, -1.57]` base-tag widths with tolerance `[0.4, 0.4]`, minimum tag side 48 px, perspective deviation above 0.55 is not scored. Angle agreement between a photo and the same photo rolled with the camera must stay inside 2 degrees.

## Acceptance metric

Command: `python -m buildcoach demo --output out/demo`

| Gate | Required | Observed |
| --- | --- | --- |
| Occluded completions | 0 | 0 |
| Contradictory completions | 0 | 0 |
| Clear correct completions | 3 of 3 | 3 of 3 |
| Demo elapsed | under 5.0 s | 0.159 s on this host; the test budget is 5.0 s |

The 5 second budget is the time a workshop check of these 14 sessions should not exceed, including a slower CI runner. The measured run is far under it.

Case results from the same command and from `pytest`:

| Case | Completed | Observed category |
| --- | --- | --- |
| Top photo hides tag 1 | no | `needs_another_view`, request `left` |
| Top plus correct left | yes | orientation supported, relative angle inside 12° |
| Correct left, camera rolled 28° | yes | relative angle within 2° of the unrolled photo |
| Upright tag quarter-turned | no | `orientation_mismatch` on `left-rotated` (about 98°) |
| Tag 1 hidden in top and left | no | request `left`, completion 0 |
| Clean parallel view plus clean quarter turn | no | `retake`, both image ids kept, area ignored |
| Wrong tag id | no | `identity_mismatch` |
| Duplicate tag 0 | no | `duplicate_marker` |
| Mirrored photo | no | `mirrored_layout` |
| Tag 1 far from the base tag | no | `implausible_layout` |
| Tags under 48 px | no | `low_resolution` |
| Lip in band | yes | placement supported |
| Lip shifted aside | no | `implausible_layout` and `placement_mismatch` |
| Unknown step `weld-frame` | rejected | exit 2, `unsupported_value` |
| Path escaping the fixture root | rejected | `path_rejected` |
| Claimed view `underside` | rejected | `unsupported_value` |
| Oversized or non-image bytes | rejected | `oversized_input` or `unreadable_image` |
| Grazing tag, deviation over 0.55 | no | `poor_perspective`, no angle emitted |

`python -m pytest -q` — 28 passed in about 1 second, including the demo budget.

`python -m ruff check`, `ruff format --check`, and `python -m compileall` passed. This project does not compile its own C or C++ extension, so an address sanitizer job is not applicable. OpenCV is used as the pinned wheel.

## Domain safeguard

A repeated or loosely placed tag must not become a completion.

- Duplicate ids reject the photo before rules run.
- Co-visible tags whose center is farther than 2.6 base-tag widths are `implausible_layout`.
- A horizontal mirror is detected by decoding the flipped image and is not used as evidence.
- Images over the byte, edge, or pixel caps are rejected and are not downscaled.
- The report text says a visible tag is not proof of physical attachment.

## Trust boundary

- Session paths cannot leave the fixture root. The upload page ignores the client filename except as a sanitized id.
- Reports are written only under `--output`.
- The page binds to `127.0.0.1` and does not fetch URLs.
- No child process is launched for a check.
- CI uses `permissions: contents: read` and no secrets.
- deps.dev reported no advisory for `opencv-python-headless` 4.12.0.88 on 2026-11-23. CVE-2025-53644 affects OpenCV 4.10.0 and 4.11.0 and is fixed in 4.12.0. GHSA-m6vm-8g8v-xfjh / CVE-2019-5063 last affects the headless wheel at 4.1.0.25. Snyk listed no direct advisory for NumPy 2.2.6. This was a public-advisory lookup, not a full commercial scan.

## Wheel

`python -m build --wheel` produced `buildcoach-0.1.0-py3-none-any.whl` containing the kit, images, guide, tags, sessions, and manifest (37 fixture files). The wheel is not committed. Build it from the tag when a file artifact is needed.

## Residual limits

- Printed cards and phone cameras were not measured. The app says so.
- View class uses the base tag's edge-length ratios, not a calibrated camera. It is a framing check for these synthetic photos.
- The far-but-parallel upright can still show a supported orientation finding. The step stays incomplete because the layout rule fails.
- No native sanitizer was run on the OpenCV wheel.
