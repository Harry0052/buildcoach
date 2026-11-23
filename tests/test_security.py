from pathlib import Path

import numpy as np

from buildcoach.contracts import load_kit
from buildcoach.errors import InputError
from buildcoach.evaluate import ImageObservation, Marker, evaluate_step
from buildcoach.normalize import decode_image
from buildcoach.pipeline import write_report


def test_poor_perspective_does_not_score_an_angle():
    kit = load_kit()
    # Left edge much shorter than the right edge, so the view is "left"
    # and the deviation is past the kit limit.
    corners = np.array([[0, 30], [100, 0], [100, 100], [0, 70]], dtype=float)
    marker = Marker(1, corners, side_px=80, area_px=4000)
    base = Marker(0, corners, side_px=80, area_px=4000)
    observation = ImageObservation(
        image_id="grazing",
        claimed_view="left",
        width=200,
        height=200,
        sha256="abc",
        markers=[base, marker],
        view_class="left",
    )
    report = evaluate_step(kit, "seat-upright", [observation])
    orientation = next(item for item in report["findings"] if item["rule_id"] == "upright-orientation")
    assert report["completed"] is False
    assert orientation["category"] == "poor_perspective"
    assert "relative_deg" not in orientation.get("evidence", {})


def test_decode_rejects_a_huge_edge(tmp_path: Path):
    import cv2

    image = np.full((50, 50), 255, np.uint8)
    path = tmp_path / "small.png"
    cv2.imwrite(str(path), image)
    data = path.read_bytes()
    limits = {"max_bytes": 8000000, "max_pixels": 100, "max_edge_px": 40}
    try:
        decode_image(data, limits)
    except InputError as exc:
        assert exc.category == "oversized_input"
        assert "not resized" in exc.message
    else:
        raise AssertionError("oversized pixel count was accepted")


def test_report_writer_rejects_a_path_outside_the_directory(tmp_path: Path):
    report = {
        "kit_id": "desk-ledge",
        "kit_version": "1.0.0",
        "step_title": "Place the base",
        "completed": False,
        "limitations": ["A visible tag is not proof of physical attachment."],
        "findings": [],
        "inputs": [],
    }
    output = tmp_path / "out"
    json_path, text_path = write_report(report, output)
    assert json_path.parent == output.resolve()
    assert text_path.parent == output.resolve()
    assert not (tmp_path / "report.json").exists()
