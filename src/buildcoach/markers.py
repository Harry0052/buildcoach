"""ArUco detection. Identity and corners only; no pose in millimetres."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from buildcoach.geometry import mean_side_px, quad_area

DICTIONARY_NAME = "DICT_4X4_50"


@dataclass(frozen=True)
class Marker:
    marker_id: int
    corners: np.ndarray
    side_px: float
    area_px: float


def _dictionary():
    return cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)


def detect_markers(gray: np.ndarray) -> list[Marker]:
    """Return detections in a stable order: id, then top-left x, then y."""
    if gray.ndim != 2:
        raise ValueError("detect_markers expects a grayscale image")
    detector = cv2.aruco.ArucoDetector(_dictionary(), cv2.aruco.DetectorParameters())
    corners, ids, _rejected = detector.detectMarkers(gray)
    if ids is None or len(ids) == 0:
        return []
    found: list[Marker] = []
    for index, marker_id in enumerate(ids.flatten().tolist()):
        points = np.asarray(corners[index], dtype=np.float64).reshape(4, 2)
        found.append(
            Marker(
                marker_id=int(marker_id),
                corners=points,
                side_px=mean_side_px(points),
                area_px=quad_area(points),
            )
        )
    found.sort(key=lambda marker: (marker.marker_id, marker.corners[0, 0], marker.corners[0, 1]))
    return found
