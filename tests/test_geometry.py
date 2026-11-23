import math

import numpy as np

from buildcoach.evaluate import merge_statuses
from buildcoach.geometry import (
    classify_view,
    marker_frame_center,
    perspective_deviation,
    relative_x_axis_deg,
)
from tests.oracle_math import relative_deg


def test_worked_square_matches_the_hand_calculation():
    base = [(0, 0), (100, 0), (100, 100), (0, 100)]
    upright = [(0, -160), (100, -160), (100, -60), (0, -60)]
    assert relative_deg(base, upright) == 0
    turned = [(0, 0), (0, 100), (-100, 100), (-100, 0)]
    assert relative_deg(base, turned) == 90
    engine = relative_x_axis_deg(np.array(base, dtype=float), np.array(upright, dtype=float))
    assert engine == 0
    engine_turn = relative_x_axis_deg(np.array(base, dtype=float), np.array(turned, dtype=float))
    assert math.isclose(engine_turn, 90.0, abs_tol=1e-9)


def test_identity_homography_center():
    reference = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=float)
    subject = np.array([[0, -1.5], [1, -1.5], [1, -0.5], [0, -0.5]], dtype=float)
    x, y = marker_frame_center(reference, subject)
    assert math.isclose(x, 0.5, abs_tol=1e-6)
    assert math.isclose(y, -1.0, abs_tol=1e-6)


def test_view_bins_are_roll_invariant_in_corner_identity():
    top = np.array([[10, 10], [110, 10], [110, 110], [10, 110]], dtype=float)
    left = np.array([[10, 30], [110, 10], [110, 110], [10, 90]], dtype=float)
    front = np.array([[30, 10], [90, 10], [110, 110], [10, 110]], dtype=float)
    assert classify_view(top) == "top"
    assert classify_view(left) == "left"
    assert classify_view(front) == "front"
    # A 90 degree roll moves every corner. Reconstruct by rotating coordinates,
    # which preserves edge lengths identified by corner index.
    rotated = np.stack([-left[:, 1], left[:, 0]], axis=1)
    assert classify_view(rotated) == "left"


def test_merge_ignores_detection_area():
    small_good = {
        "status": "supported",
        "image_id": "small",
        "confidence_area": 10,
        "detail": "ok",
    }
    large_bad = {
        "status": "visible_mismatch",
        "image_id": "large",
        "confidence_area": 99999,
        "detail": "turned",
        "category": "orientation_mismatch",
    }
    swapped = merge_statuses(
        [
            {**large_bad, "confidence_area": 10},
            {**small_good, "confidence_area": 99999},
        ]
    )
    original = merge_statuses([small_good, large_bad])
    assert original["status"] == "retake"
    assert original["category"] == "contradictory_views"
    assert original["status"] == swapped["status"]
    assert original["image_ids"] == swapped["image_ids"] == ["small", "large"]


def test_extreme_foreshortening_is_measurable():
    corners = np.array([[0, 30], [100, 0], [100, 100], [0, 70]], dtype=float)
    deviation = perspective_deviation(corners)
    assert deviation is not None and deviation > 0.55
    assert classify_view(corners) == "left"
