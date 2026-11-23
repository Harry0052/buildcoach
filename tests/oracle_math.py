"""Independent geometry used by the oracle tests. Does not import buildcoach.geometry."""

from __future__ import annotations

import math


def x_axis_deg(corners: list[tuple[float, float]]) -> float:
    x0, y0 = corners[0]
    x1, y1 = corners[1]
    return math.degrees(math.atan2(y1 - y0, x1 - x0))


def relative_deg(reference: list[tuple[float, float]], subject: list[tuple[float, float]]) -> float:
    delta = x_axis_deg(subject) - x_axis_deg(reference)
    return (delta + 180.0) % 360.0 - 180.0
