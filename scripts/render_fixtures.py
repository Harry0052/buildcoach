"""Render original Desk Ledge tags, guide bits, and synthetic photos.

Seed 20261123. No third-party photographs. Run from the repository root:

    python scripts/render_fixtures.py
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "src" / "buildcoach" / "fixtures"
IMAGES = FIXTURES / "images"
TAGS = FIXTURES / "tags"
SESSIONS = FIXTURES / "sessions" / "valid"
SEED = 20261123
DICTIONARY = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)

CANVAS = (900, 1000)  # height, width


def tag_bitmap(marker_id: int, side: int, quarter_turn: bool = False) -> np.ndarray:
    image = cv2.aruco.generateImageMarker(DICTIONARY, marker_id, side)
    if quarter_turn:
        image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    return image


def destination(view: str, patch: int, origin: tuple[int, int]) -> np.ndarray:
    shrink = int(patch * 0.18)
    if view == "left":
        quad = np.array(
            [[0, shrink], [patch - 1, 0], [patch - 1, patch - 1], [0, patch - 1 - shrink]],
            dtype=np.float32,
        )
    elif view == "front":
        quad = np.array(
            [[shrink, 0], [patch - 1 - shrink, 0], [patch - 1, patch - 1], [0, patch - 1]],
            dtype=np.float32,
        )
    else:
        quad = np.array(
            [[0, 0], [patch - 1, 0], [patch - 1, patch - 1], [0, patch - 1]],
            dtype=np.float32,
        )
    return quad + np.array(origin, dtype=np.float32)


def stamp(
    image: np.ndarray,
    marker_id: int,
    origin: tuple[int, int],
    side: int,
    view: str,
    quarter_turn: bool = False,
) -> None:
    margin = max(10, side // 6)
    patch = side + 2 * margin
    tile = np.full((patch, patch), 228, np.uint8)
    bits = tag_bitmap(marker_id, side, quarter_turn)
    tile[margin : margin + side, margin : margin + side] = bits
    source = np.array([[0, 0], [patch - 1, 0], [patch - 1, patch - 1], [0, patch - 1]], dtype=np.float32)
    dest = destination(view, patch, origin)
    homography = cv2.getPerspectiveTransform(source, dest)
    warped = cv2.warpPerspective(tile, homography, (image.shape[1], image.shape[0]))
    mask = cv2.warpPerspective(np.full(tile.shape, 255, np.uint8), homography, (image.shape[1], image.shape[0]))
    image[mask > 0] = warped[mask > 0]


def background(kind: str, shape: tuple[int, int]) -> np.ndarray:
    rng = np.random.default_rng(SEED if kind != "paper" else SEED + 1)
    if kind == "plain":
        return np.full(shape, 228, np.uint8)
    if kind == "desk":
        noise = rng.integers(70, 120, shape, dtype=np.uint16)
        return cv2.GaussianBlur(noise.astype(np.uint8), (0, 0), 3)
    if kind == "paper":
        noise = rng.integers(205, 245, shape, dtype=np.uint16)
        return cv2.GaussianBlur(noise.astype(np.uint8), (0, 0), 1)
    stripes = np.full(shape, 48, np.uint8)
    stripes[::14, :] = 90
    return cv2.GaussianBlur(stripes, (0, 0), 0.6)


def roll(image: np.ndarray, degrees: float) -> np.ndarray:
    height, width = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), degrees, 1.0)
    return cv2.warpAffine(image, matrix, (width, height), borderValue=228)


def save(image: np.ndarray, name: str) -> None:
    path = IMAGES / name
    cv2.imwrite(str(path), image)


def ids_of(image: np.ndarray) -> list[int]:
    detector = cv2.aruco.ArucoDetector(DICTIONARY, cv2.aruco.DetectorParameters())
    _corners, ids, _rejected = detector.detectMarkers(image)
    if ids is None:
        return []
    return [int(item) for item in ids.flatten()]


def expect(image: np.ndarray, name: str, expected: list[int]) -> None:
    found = ids_of(image)
    if Counter(found) != Counter(expected):
        raise SystemExit(f"{name}: expected {expected}, detected {found}")


def write_tag_svg(marker_id: int) -> None:
    side = 60
    bits = tag_bitmap(marker_id, side)
    cell = 8
    quiet = cell
    canvas = side * cell + 2 * quiet
    rects = [
        f'<rect width="{canvas}" height="{canvas}" fill="white"/>',
        f'<rect x="{quiet}" y="{quiet}" width="{side * cell}" height="{side * cell}" fill="none" stroke="black"/>',
    ]
    for y in range(side):
        for x in range(side):
            if bits[y, x] < 128:
                rects.append(
                    f'<rect x="{quiet + x * cell}" y="{quiet + y * cell}" width="{cell}" height="{cell}" fill="black"/>'
                )
    label = f"Tag {marker_id}"
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas}" height="{canvas + 28}" '
        f'viewBox="0 0 {canvas} {canvas + 28}">'
        f"<title>{label}</title>"
        + "".join(rects)
        + (
            f'<text x="{canvas / 2}" y="{canvas + 20}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="16">{label}</text>'
        )
        + "</svg>\n"
    )
    (TAGS / f"tag-{marker_id}.svg").write_text(svg, encoding="utf-8")


def write_guide() -> None:
    guide = """<svg xmlns="http://www.w3.org/2000/svg" width="960" height="340" viewBox="0 0 960 340">
<title>Desk Ledge practice guide</title>
<rect width="960" height="340" fill="#f7f4ee"/>
<text x="24" y="32" font-family="sans-serif" font-size="20">Desk Ledge — three visible checks</text>
<text x="24" y="54" font-family="sans-serif" font-size="13">Practice kit only. Not a load or safety check.</text>
<g font-family="sans-serif" font-size="14">
  <rect x="24" y="78" width="280" height="220" fill="white" stroke="#222"/>
  <text x="40" y="104">1. Place the base</text>
  <rect x="90" y="140" width="150" height="100" fill="#d9d3c7" stroke="#222"/>
  <rect x="130" y="165" width="70" height="50" fill="white" stroke="#222"/>
  <text x="148" y="195">tag 0</text>
  <text x="40" y="276">Top view. Tag 0 square to the camera.</text>
  <rect x="340" y="78" width="280" height="220" fill="white" stroke="#222"/>
  <text x="356" y="104">2. Seat the upright</text>
  <rect x="400" y="210" width="160" height="36" fill="#d9d3c7" stroke="#222"/>
  <rect x="430" y="120" width="28" height="100" fill="#b7c4b1" stroke="#222"/>
  <rect x="404" y="150" width="22" height="40" fill="white" stroke="#222"/>
  <text x="470" y="176">tag 1</text>
  <text x="356" y="276">Left view. Tag 1 parallel to tag 0.</text>
  <rect x="656" y="78" width="280" height="220" fill="white" stroke="#222"/>
  <text x="672" y="104">3. Set the lip</text>
  <rect x="710" y="210" width="160" height="36" fill="#d9d3c7" stroke="#222"/>
  <rect x="750" y="150" width="80" height="22" fill="#c4b7a6" stroke="#222"/>
  <rect x="768" y="154" width="44" height="14" fill="white" stroke="#222"/>
  <text x="720" y="276">Front view. Tag 2 above tag 0.</text>
</g>
</svg>
"""
    (FIXTURES / "guide" / "desk-ledge.svg").write_text(guide, encoding="utf-8")


def scene(view: str, kind: str, stamps: list[tuple], degrees: float = 0, mirror: bool = False) -> np.ndarray:
    image = background(kind, CANVAS)
    for marker_id, origin, side, quarter in stamps:
        stamp(image, marker_id, origin, side, view, quarter)
    if degrees:
        image = roll(image, degrees)
    if mirror:
        image = cv2.flip(image, 1)
    return image


def session(name: str, step_id: str, images: list[tuple[str, str, str]]) -> None:
    body = {
        "schema_version": "1.0.0",
        "kit_id": "desk-ledge",
        "step_id": step_id,
        "images": [
            {"id": image_id, "path": f"../../images/{filename}", "claimed_view": claimed}
            for image_id, filename, claimed in images
        ],
    }
    (SESSIONS / name).write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")


def checksums() -> dict[str, str]:
    records = {}
    for path in sorted(FIXTURES.rglob("*")):
        if not path.is_file() or path.name == "MANIFEST.json":
            continue
        relative = path.relative_to(FIXTURES).as_posix()
        records[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return records


def main() -> None:
    IMAGES.mkdir(parents=True, exist_ok=True)
    TAGS.mkdir(parents=True, exist_ok=True)
    SESSIONS.mkdir(parents=True, exist_ok=True)
    for marker_id in (0, 1, 2):
        write_tag_svg(marker_id)
    write_guide()

    base = (360, 560)
    near = (370, 230)
    far = (40, 230)
    side = 170
    tiny = 26
    lip_base = (200, 620)
    lip_near = (210, 420)
    lip_far = (500, 420)

    place = scene("top", "wood", [(0, base, side, False)])
    top = scene("top", "paper", [(0, base, side, False)])
    left = scene("left", "desk", [(0, base, side, False), (1, near, side, False)])
    rolled = roll(left, 28)
    rotated = scene("left", "desk", [(0, base, side, False), (1, near, side, True)])
    occluded = scene("left", "plain", [(0, base, side, False)])
    mirror = cv2.flip(left, 1)
    duplicate = scene(
        "left",
        "plain",
        [(0, base, side, False), (0, (40, 560), 110, False), (1, near, side, False)],
    )
    wrong = scene("left", "paper", [(0, base, side, False), (2, near, side, False)])
    distant = scene("left", "plain", [(0, base, side, False), (1, far, side, False)])
    small = scene("left", "plain", [(0, (420, 620), tiny, False), (1, (430, 360), tiny, False)])
    lip = scene("front", "paper", [(0, lip_base, side, False), (2, lip_near, side, False)])
    lip_far_image = scene("front", "paper", [(0, lip_base, side, False), (2, lip_far, side, False)])

    specs = [
        ("place-base-top.png", place, [0]),
        ("seat-top-hidden.png", top, [0]),
        ("seat-left-ok.png", left, [0, 1]),
        ("seat-left-rolled.png", rolled, [0, 1]),
        ("seat-left-rotated.png", rotated, [0, 1]),
        ("seat-left-occluded.png", occluded, [0]),
        ("seat-left-mirror.png", mirror, []),
        ("seat-left-duplicate.png", duplicate, [0, 0, 1]),
        ("seat-left-wrong.png", wrong, [0, 2]),
        ("seat-left-far.png", distant, [0, 1]),
        ("seat-left-tiny.png", small, [0, 1]),
        ("lip-front-ok.png", lip, [0, 2]),
        ("lip-front-misplaced.png", lip_far_image, [0, 2]),
    ]
    for name, image, expected_ids in specs:
        expect(image, name, expected_ids)
        save(image, name)

    session("place-base.json", "place-base", [("top-wood", "place-base-top.png", "top")])
    session("seat-top-only.json", "seat-upright", [("top-hidden", "seat-top-hidden.png", "top")])
    session(
        "seat-complete.json",
        "seat-upright",
        [("top-hidden", "seat-top-hidden.png", "top"), ("left-ok", "seat-left-ok.png", "left")],
    )
    session("seat-rolled.json", "seat-upright", [("left-rolled", "seat-left-rolled.png", "left")])
    session("seat-rotated.json", "seat-upright", [("left-rotated", "seat-left-rotated.png", "left")])
    session(
        "seat-occluded.json",
        "seat-upright",
        [
            ("top-hidden", "seat-top-hidden.png", "top"),
            ("left-occluded", "seat-left-occluded.png", "left"),
        ],
    )
    session(
        "seat-contradictory.json",
        "seat-upright",
        [("left-ok", "seat-left-ok.png", "left"), ("left-rotated", "seat-left-rotated.png", "left")],
    )
    session("seat-mirror.json", "seat-upright", [("left-mirror", "seat-left-mirror.png", "left")])
    session("seat-duplicate.json", "seat-upright", [("left-duplicate", "seat-left-duplicate.png", "left")])
    session("seat-wrong-id.json", "seat-upright", [("left-wrong", "seat-left-wrong.png", "left")])
    session("seat-far.json", "seat-upright", [("left-far", "seat-left-far.png", "left")])
    session("seat-tiny.json", "seat-upright", [("left-tiny", "seat-left-tiny.png", "left")])
    session("lip-ok.json", "set-lip", [("front-ok", "lip-front-ok.png", "front")])
    session("lip-misplaced.json", "set-lip", [("front-misplaced", "lip-front-misplaced.png", "front")])

    manifest = {
        "schema_version": "1.0.0",
        "seed": SEED,
        "generator": "scripts/render_fixtures.py",
        "opencv_dictionary": "DICT_4X4_50",
        "opencv_python_headless": "4.12.0.88",
        "license": "MIT, same as the repository. Original synthetic images. No people are depicted.",
        "sources": [
            {
                "item": "ArUco dictionary DICT_4X4_50",
                "url": "https://github.com/opencv/opencv/releases/tag/4.12.0",
                "license": "Apache-2.0",
                "use": "Tag bit patterns generated locally. No OpenCV sample photos are shipped.",
            }
        ],
        "files": {},
    }
    # Hash after the other files exist, then write the manifest without hashing itself.
    manifest["files"] = checksums()
    (FIXTURES / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote fixtures under {FIXTURES}")


if __name__ == "__main__":
    main()
