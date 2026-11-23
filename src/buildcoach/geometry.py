"""Marker-corner geometry. Angles are degrees. Positions are base-tag widths."""

from __future__ import annotations

import math

import cv2
import numpy as np

CANONICAL = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]], dtype=np.float32)


def edge_lengths(corners: np.ndarray) -> tuple[float, float, float, float]:
    """Return top, bottom, left, right edge lengths in pixels.

    Corner order is the ArUco order: top-left, top-right, bottom-right, bottom-left
    in the tag's own frame, not in screen-up.
    """
    points = np.asarray(corners, dtype=np.float64).reshape(4, 2)

    def length(i: int, j: int) -> float:
        return float(np.hypot(points[i, 0] - points[j, 0], points[i, 1] - points[j, 1]))

    return length(0, 1), length(3, 2), length(0, 3), length(1, 2)


def edge_ratios(corners: np.ndarray) -> tuple[float, float] | None:
    """Return (top/bottom, left/right). None when a side has collapsed."""
    top, bottom, left, right = edge_lengths(corners)
    if min(top, bottom, left, right) < 1e-6:
        return None
    return top / bottom, left / right


def mean_side_px(corners: np.ndarray) -> float:
    top, bottom, left, right = edge_lengths(corners)
    return (top + bottom + left + right) / 4.0


def x_axis_deg(corners: np.ndarray) -> float:
    """Image-plane angle of the tag +X edge, in degrees. Positive is clockwise on screen."""
    points = np.asarray(corners, dtype=np.float64).reshape(4, 2)
    return math.degrees(math.atan2(points[1, 1] - points[0, 1], points[1, 0] - points[0, 0]))


def wrap_deg(delta: float) -> float:
    """Wrap a difference into (-180, 180]."""
    return (delta + 180.0) % 360.0 - 180.0


def relative_x_axis_deg(reference: np.ndarray, subject: np.ndarray) -> float:
    """Signed angle from the reference tag +X edge to the subject +X edge."""
    return wrap_deg(x_axis_deg(subject) - x_axis_deg(reference))


def classify_view(
    corners: np.ndarray,
    parallel_max: float = 0.08,
    axis_min: float = 0.15,
) -> str | None:
    """Classify a view from the base tag's ordered corners.

    A nearly square projection is `top`. Unequal vertical edges mean the camera
    is off to the side (`left` when the tag's left edge is the shorter one).
    Unequal horizontal edges mean the camera is off the front or back.
    Anything between the two thresholds is unknown. The caller must not trust
    a filename or a form label in that case.
    """
    ratios = edge_ratios(corners)
    if ratios is None:
        return None
    rx, ry = ratios
    dx = abs(rx - 1.0)
    dy = abs(ry - 1.0)
    if dx <= parallel_max and dy <= parallel_max:
        return "top"
    if dy >= axis_min and dy > dx + 0.05:
        return "left" if ry < 1.0 else "right"
    if dx >= axis_min and dx > dy + 0.05:
        return "front" if rx < 1.0 else "back"
    return None


def perspective_deviation(corners: np.ndarray) -> float | None:
    ratios = edge_ratios(corners)
    if ratios is None:
        return None
    rx, ry = ratios
    return max(abs(rx - 1.0), abs(ry - 1.0))


def marker_frame_center(reference: np.ndarray, subject: np.ndarray) -> tuple[float, float]:
    """Map the subject center into the reference tag's unit square.

    The square has its origin at the reference top-left and +Y toward the
    reference bottom-left. One unit is one reference-tag width.
    """
    ref = np.asarray(reference, dtype=np.float32).reshape(4, 2)
    sub = np.asarray(subject, dtype=np.float32).reshape(4, 2)
    homography = cv2.getPerspectiveTransform(ref, CANONICAL)
    center = sub.mean(axis=0).reshape(1, 1, 2)
    mapped = cv2.perspectiveTransform(center, homography).reshape(2)
    return float(mapped[0]), float(mapped[1])


def quad_area(corners: np.ndarray) -> float:
    points = np.asarray(corners, dtype=np.float64).reshape(4, 2)
    x = points[:, 0]
    y = points[:, 1]
    return float(0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))
