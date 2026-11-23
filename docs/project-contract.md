# Project contract

Status: accepted for implementation after the overlap review. This is a visible-evidence checker for one practice kit, not a measurement lab and not a safety system.

## User and task

Makers and workshop instructors who are helping someone check a visible step on a simple practice kit.

The user selects one of three steps for an original cardboard desk stand (the Desk Ledge), submits one or two local photos of known fiducial tags, and reads a line-by-line result: supported, visible mismatch, or a request for a named view. Each line names the image it came from.

## Kit

Desk Ledge, version 1.0.0. Three flat pieces, none of them load-bearing:

1. Base, tag 0 on the top face.
2. Upright, tag 1 on the left face.
3. Lip, tag 2 on the front face.

Steps: place the base (top), seat the upright (left), set the lip (front). Tags are OpenCV `DICT_4X4_50`. The guide and the tag sheets are original files in this repository.

## Minimum dependencies

- Python 3.11 or newer.
- `opencv-python-headless==4.12.0.88` (OpenCV Apache-2.0, wrapper MIT, FFmpeg LGPLv2.1 inside the wheel).
- `numpy==2.2.6` (BSD-3-Clause), as required by that wheel.
- Development only: `pytest==8.4.2`, `ruff==0.14.14`.

No paid API, no account, and no network fetch while a check runs. Fixture images ship in the repository.

## Acceptance case

Session: step `seat-upright`, only the authored top photo, tag 1 not visible.

Required result: `completed` is false, and the report requests the view `left`. The prompt names tag 1 and the base tag.

Then add the authored left photo where tag 0 and tag 1 are both visible and their top edges agree within 12 degrees. Required result: `completed` is true.

Separate gates on the same kit, same state labels:

- Tag 1 hidden in every supplied view: named `left` request, zero completions.
- The correct left photo rolled with the camera: the relative-orientation verdict stays supported.
- Wrong tag identity, duplicate tag ids, a mirrored image, and an implausible layout each fail on their own.
- Two clean views that disagree request a retake and do not keep the larger detection.
- A keyboard user can submit the sample and reach the text that matches the overlay.

The zero-completion rule applies to the occluded fixture and the contradictory fixture. Completions on clear correct fixtures are counted separately. The metric is about this kit and these files, not about all furniture.

## Out of scope

Strength, fastener torque, hidden mating surfaces, electrical work, machinery, and any instruction a person might treat as safe-to-use. A detected tag is not proof the piece is attached. Calibrated millimetre measurement belongs to a different product. Firmware fault injection belongs to a different product.

## Provenance path

Authored SVG guide, tag bitmaps generated from the pinned OpenCV dictionary, and synthetic photos rendered by `scripts/render_fixtures.py` with seed `20261123`. No Epoch, IKEA, or Assembly101 images.
