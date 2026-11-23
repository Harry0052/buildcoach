"""Rule evaluation. File loading and HTML stay outside this module."""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from buildcoach import __version__
from buildcoach.errors import InputError
from buildcoach.geometry import (
    classify_view,
    marker_frame_center,
    perspective_deviation,
    relative_x_axis_deg,
    x_axis_deg,
)
from buildcoach.markers import Marker, detect_markers

LIMITATIONS = [
    "Visible tag checks for the Desk Ledge practice kit only.",
    "A passing result does not show that a part is fastened, square as a structure, or safe to load.",
    "Angles are degrees between tag edges in the photograph. Positions are in widths of the base tag.",
    "A visible tag is not proof of physical attachment.",
    "These checks were validated on the synthetic fixture, not on a separate phone-camera set.",
]


@dataclass
class ImageObservation:
    image_id: str
    claimed_view: str | None
    width: int
    height: int
    sha256: str
    markers: list[Marker]
    mirrored: bool = False
    view_class: str | None = None
    notes: list[str] = field(default_factory=list)

    def by_id(self) -> dict[int, list[Marker]]:
        grouped: dict[int, list[Marker]] = {}
        for marker in self.markers:
            grouped.setdefault(marker.marker_id, []).append(marker)
        return grouped


def merge_statuses(records: list[dict]) -> dict:
    """Combine per-image rule results. Detection area is recorded and never used to choose."""
    if not records:
        return {
            "status": "needs_another_view",
            "category": "insufficient_evidence",
            "image_ids": [],
            "detail": "No image was available for this rule.",
        }
    ordered = sorted(records, key=lambda item: item["image_id"])
    supports = [item for item in ordered if item["status"] == "supported"]
    mismatches = [item for item in ordered if item["status"] == "visible_mismatch"]
    if supports and mismatches:
        return {
            "status": "retake",
            "category": "contradictory_views",
            "image_ids": [item["image_id"] for item in supports + mismatches],
            "detail": (
                "Clean views disagree. Take the named view again. The larger tag was not treated as the winner."
            ),
            "evidence": {"ignored_confidence_area_px": [item.get("confidence_area") for item in ordered]},
        }
    if supports:
        return {
            "status": "supported",
            "category": "supported",
            "image_ids": [item["image_id"] for item in supports],
            "detail": supports[0]["detail"],
            "evidence": supports[0].get("evidence", {}),
        }
    if mismatches:
        chosen = mismatches[0]
        return {
            "status": "visible_mismatch",
            "category": chosen.get("category", "visible_mismatch"),
            "image_ids": [item["image_id"] for item in mismatches],
            "detail": chosen["detail"],
            "evidence": chosen.get("evidence", {}),
            "request": chosen.get("request"),
        }
    chosen = ordered[0]
    return {
        "status": chosen["status"],
        "category": chosen.get("category", "insufficient_evidence"),
        "image_ids": [item["image_id"] for item in ordered],
        "detail": chosen["detail"],
        "evidence": chosen.get("evidence", {}),
        "request": chosen.get("request"),
    }


def observe_image(
    image_id: str,
    gray: np.ndarray,
    claimed_view: str | None,
    sha256: str,
    limits: dict,
) -> ImageObservation:
    markers = detect_markers(gray)
    observation = ImageObservation(
        image_id=image_id,
        claimed_view=claimed_view,
        width=int(gray.shape[1]),
        height=int(gray.shape[0]),
        sha256=sha256,
        markers=markers,
    )
    if not markers:
        flipped = detect_markers(cv2.flip(gray, 1))
        if flipped:
            observation.mirrored = True
            observation.notes.append("The photo matches a mirrored tag sheet. Submit the unmirrored photo.")
            return observation
        observation.notes.append("No kit tag was detected.")
        return observation
    grouped = observation.by_id()
    duplicates = sorted(marker_id for marker_id, group in grouped.items() if len(group) > 1)
    if duplicates:
        observation.notes.append("Duplicate tag ids: " + ", ".join(str(marker_id) for marker_id in duplicates) + ".")
        return observation
    base = grouped.get(0, [None])[0]
    if base is None:
        observation.notes.append("The base tag (id 0) is not visible, so the view was not classified.")
        return observation
    observation.view_class = classify_view(
        base.corners,
        parallel_max=float(limits["view_parallel_max"]),
        axis_min=float(limits["view_axis_min"]),
    )
    if observation.view_class is None:
        observation.notes.append(
            "The base tag is visible, but the viewing angle is between the top, left, and front bins."
        )
    elif claimed_view and claimed_view != observation.view_class:
        observation.notes.append(
            f"The form said {claimed_view}, and the base tag geometry says {observation.view_class}. Geometry is used."
        )
    return observation


def _round(value: float, digits: int = 2) -> float:
    return round(float(value), digits)


def _corners(marker: Marker) -> list[list[float]]:
    return [[_round(x, 1), _round(y, 1)] for x, y in marker.corners.tolist()]


def _known_ids(kit: dict) -> set[int]:
    return {int(part["marker_id"]) for part in kit["parts"]}


def _duplicate_ids(observation: ImageObservation) -> list[int]:
    grouped = observation.by_id()
    return sorted(marker_id for marker_id, group in grouped.items() if len(group) > 1)


def _request(rule: dict) -> dict:
    missing = rule.get("on_missing") or {}
    return {"view": missing.get("view"), "prompt": missing.get("prompt")}


def evaluate_step(kit: dict, step_id: str, observations: list[ImageObservation]) -> dict:
    """Evaluate one step. `completed` is true only when every rule is supported."""
    matches = [item for item in kit["steps"] if item["id"] == step_id]
    if not matches:
        known = ", ".join(item["id"] for item in kit["steps"])
        raise InputError("unsupported_value", f"Unknown step_id {step_id!r}. Supported steps: {known}.", "step_id")
    step = matches[0]
    limits = kit["limits"]
    known = _known_ids(kit)
    findings: list[dict] = []
    blocked = False

    for observation in observations:
        if observation.mirrored:
            blocked = True
            findings.append(
                {
                    "rule_id": "image-integrity",
                    "status": "visible_mismatch",
                    "category": "mirrored_layout",
                    "image_ids": [observation.image_id],
                    "detail": (
                        f"{observation.image_id} is a mirrored photo. Tag checks were not taken from it. "
                        "Unmirror the image and submit it again."
                    ),
                    "evidence": {"sha256": observation.sha256},
                }
            )
        duplicates = _duplicate_ids(observation)
        if duplicates:
            blocked = True
            findings.append(
                {
                    "rule_id": "image-integrity",
                    "status": "visible_mismatch",
                    "category": "duplicate_marker",
                    "image_ids": [observation.image_id],
                    "detail": (
                        f"{observation.image_id} contains more than one tag with id "
                        f"{', '.join(str(item) for item in duplicates)}. "
                        "A repeated tag can make the wrong piece look plausible, so this photo was rejected."
                    ),
                    "evidence": {"duplicate_ids": duplicates, "sha256": observation.sha256},
                }
            )

    rule_findings = []
    if not blocked:
        for rule in step["rules"]:
            rule_findings.append(_evaluate_rule(rule, observations, limits, known))
    findings.extend(rule_findings)

    completed = (not blocked) and bool(rule_findings) and all(item["status"] == "supported" for item in rule_findings)
    return {
        "schema_version": "1.0.0",
        "buildcoach_version": __version__,
        "kit_id": kit["kit_id"],
        "kit_version": kit["kit_version"],
        "step_id": step_id,
        "step_title": step["title"],
        "completed": completed,
        "units": {
            "angle": "degree",
            "position": "base_marker_widths",
            "marker_side": "pixel",
        },
        "limitations": list(LIMITATIONS),
        "inputs": [_input_record(observation) for observation in observations],
        "findings": findings,
    }


def _input_record(observation: ImageObservation) -> dict:
    grouped = observation.by_id()
    return {
        "image_id": observation.image_id,
        "sha256": observation.sha256,
        "claimed_view": observation.claimed_view,
        "view_class": observation.view_class,
        "width_px": observation.width,
        "height_px": observation.height,
        "mirrored": observation.mirrored,
        "detected_ids": [marker.marker_id for marker in observation.markers],
        "duplicate_ids": _duplicate_ids(observation),
        "notes": list(observation.notes),
        "markers": [
            {
                "id": marker.marker_id,
                "corners_px": _corners(marker),
                "side_px": _round(marker.side_px, 1),
                "area_px": _round(marker.area_px, 1),
            }
            for marker in observation.markers
            if len(grouped.get(marker.marker_id, [])) == 1
        ],
    }


def _usable(observation: ImageObservation) -> bool:
    return not observation.mirrored and not _duplicate_ids(observation)


def _evaluate_rule(rule: dict, observations: list[ImageObservation], limits: dict, known: set[int]) -> dict:
    kind = rule["type"]
    per_image = []
    for observation in observations:
        if not _usable(observation):
            continue
        if kind == "marker_present":
            per_image.append(_marker_present(rule, observation, limits))
        elif kind == "co_visible":
            per_image.append(_co_visible(rule, observation, limits, known))
        elif kind == "relative_x_axis":
            record = _relative(rule, observation, limits)
            if record is not None:
                per_image.append(record)
        elif kind == "marker_frame_position":
            record = _position(rule, observation, limits)
            if record is not None:
                per_image.append(record)
        else:
            per_image.append(
                {
                    "status": "needs_another_view",
                    "category": "insufficient_evidence",
                    "image_id": observation.image_id,
                    "detail": f"Rule type {kind} is not implemented.",
                    "confidence_area": 0,
                }
            )
    merged = merge_statuses(per_image)
    if merged["status"] in {"needs_another_view", "retake"} and not merged.get("request"):
        merged["request"] = _request(rule)
    finding = {
        "rule_id": rule["id"],
        "status": merged["status"],
        "category": merged.get("category"),
        "image_ids": merged.get("image_ids", []),
        "detail": merged.get("detail", ""),
        "evidence": merged.get("evidence", {}),
    }
    if merged.get("request"):
        finding["request"] = merged["request"]
    return finding


def _low_resolution(rule: dict, observation: ImageObservation, markers: list[Marker], limits: dict) -> dict | None:
    floor = float(limits["min_marker_side_px"])
    small = [marker for marker in markers if marker.side_px < floor]
    if not small:
        return None
    ids = " and ".join(str(marker.marker_id) for marker in small)
    return {
        "status": "needs_another_view",
        "category": "low_resolution",
        "image_id": observation.image_id,
        "confidence_area": min(marker.area_px for marker in small),
        "detail": (
            f"Tags {ids} are under {floor:.0f} px on a side in {observation.image_id}. "
            "Move closer and retake the view so the tags are large enough to check."
        ),
        "request": _request(rule),
        "evidence": {"min_side_px": _round(min(marker.side_px for marker in small), 1), "limit_px": floor},
    }


def _marker_present(rule: dict, observation: ImageObservation, limits: dict) -> dict:
    marker_id = int(rule["marker_id"])
    view = rule["view"]
    request = _request(rule)
    if observation.view_class != view:
        return {
            "status": "needs_another_view",
            "category": "insufficient_evidence",
            "image_id": observation.image_id,
            "confidence_area": 0,
            "detail": request["prompt"],
            "request": request,
            "evidence": {"view_class": observation.view_class, "required_view": view},
        }
    grouped = observation.by_id()
    group = grouped.get(marker_id, [])
    if len(group) != 1:
        return {
            "status": "needs_another_view",
            "category": "insufficient_evidence",
            "image_id": observation.image_id,
            "confidence_area": 0,
            "detail": request["prompt"],
            "request": request,
            "evidence": {"detected_ids": [marker.marker_id for marker in observation.markers]},
        }
    low = _low_resolution(rule, observation, group, limits)
    if low:
        return low
    marker = group[0]
    return {
        "status": "supported",
        "category": "supported",
        "image_id": observation.image_id,
        "confidence_area": marker.area_px,
        "detail": f"Tag {marker_id} is visible in the {view} view ({observation.image_id}).",
        "evidence": {
            "marker_id": marker_id,
            "corners_px": _corners(marker),
            "side_px": _round(marker.side_px, 1),
            "view_class": observation.view_class,
        },
    }


def _co_visible(rule: dict, observation: ImageObservation, limits: dict, known: set[int]) -> dict:
    required = [int(marker_id) for marker_id in rule["marker_ids"]]
    view = rule["view"]
    request = _request(rule)
    grouped = observation.by_id()
    if observation.view_class != view:
        return {
            "status": "needs_another_view",
            "category": "insufficient_evidence",
            "image_id": observation.image_id,
            "confidence_area": 0,
            "detail": request["prompt"],
            "request": request,
            "evidence": {
                "view_class": observation.view_class,
                "required_view": view,
                "detected_ids": [marker.marker_id for marker in observation.markers],
            },
        }
    missing = [marker_id for marker_id in required if len(grouped.get(marker_id, [])) != 1]
    if missing:
        foreign = sorted(set(grouped) & known - set(required))
        if foreign:
            return {
                "status": "visible_mismatch",
                "category": "identity_mismatch",
                "image_id": observation.image_id,
                "confidence_area": max((marker.area_px for marker in observation.markers), default=0),
                "detail": (
                    f"{observation.image_id} shows tag {', '.join(str(item) for item in foreign)} "
                    f"where tag {', '.join(str(item) for item in missing)} is required."
                ),
                "evidence": {"missing_ids": missing, "unexpected_ids": foreign},
            }
        return {
            "status": "needs_another_view",
            "category": "insufficient_evidence",
            "image_id": observation.image_id,
            "confidence_area": 0,
            "detail": (
                f"{request['prompt']} Tag {', '.join(str(item) for item in missing)} "
                f"is still hidden in {observation.image_id}."
            ),
            "request": request,
            "evidence": {"missing_ids": missing, "view_class": observation.view_class},
        }
    markers = [grouped[marker_id][0] for marker_id in required]
    low = _low_resolution(rule, observation, markers, limits)
    if low:
        return low
    reference = grouped[int(rule.get("reference_marker", required[0]))][0]
    subject = grouped[int(rule.get("subject_marker", required[-1]))][0]
    center = marker_frame_center(reference.corners, subject.corners)
    max_abs = float(rule.get("max_abs_center", limits.get("max_abs_center", 4.0)))
    if abs(center[0]) > max_abs or abs(center[1]) > max_abs:
        return {
            "status": "visible_mismatch",
            "category": "implausible_layout",
            "image_id": observation.image_id,
            "confidence_area": subject.area_px,
            "detail": (
                f"Tags {reference.marker_id} and {subject.marker_id} are both visible in "
                f"{observation.image_id}, but their separation is outside the kit layout "
                f"({_round(center[0], 2)}, {_round(center[1], 2)} base-tag widths)."
            ),
            "evidence": {"center_marker_widths": [_round(center[0], 3), _round(center[1], 3)]},
        }
    return {
        "status": "supported",
        "category": "supported",
        "image_id": observation.image_id,
        "confidence_area": min(marker.area_px for marker in markers),
        "detail": (
            f"Tags {', '.join(str(marker_id) for marker_id in required)} are visible together "
            f"in the {view} view ({observation.image_id})."
        ),
        "evidence": {
            "marker_ids": required,
            "corners_px": {str(marker.marker_id): _corners(marker) for marker in markers},
            "view_class": observation.view_class,
            "center_marker_widths": [_round(center[0], 3), _round(center[1], 3)],
        },
    }


def _pair(rule: dict, observation: ImageObservation, limits: dict) -> tuple[Marker, Marker] | dict:
    if observation.view_class != rule["view"]:
        return {
            "status": "needs_another_view",
            "category": "insufficient_evidence",
            "image_id": observation.image_id,
            "confidence_area": 0,
            "detail": _request(rule)["prompt"],
            "request": _request(rule),
            "evidence": {"view_class": observation.view_class},
        }
    grouped = observation.by_id()
    ref_id = int(rule["reference_marker"])
    sub_id = int(rule["subject_marker"])
    if len(grouped.get(ref_id, [])) != 1 or len(grouped.get(sub_id, [])) != 1:
        return {
            "status": "needs_another_view",
            "category": "insufficient_evidence",
            "image_id": observation.image_id,
            "confidence_area": 0,
            "detail": _request(rule)["prompt"],
            "request": _request(rule),
            "evidence": {"detected_ids": [marker.marker_id for marker in observation.markers]},
        }
    reference = grouped[ref_id][0]
    subject = grouped[sub_id][0]
    low = _low_resolution(rule, observation, [reference, subject], limits)
    if low:
        return low
    max_dev = float(limits["max_perspective_deviation"])
    deviations = []
    for marker in (reference, subject):
        deviation = perspective_deviation(marker.corners)
        if deviation is None or deviation > max_dev:
            return {
                "status": "needs_another_view",
                "category": "poor_perspective",
                "image_id": observation.image_id,
                "confidence_area": marker.area_px,
                "detail": (
                    f"Tag {marker.marker_id} in {observation.image_id} is too foreshortened "
                    "to score this rule. Retake the view more head-on."
                ),
                "request": _request(rule),
                "evidence": {"perspective_deviation": None if deviation is None else _round(deviation, 3)},
            }
        deviations.append(deviation)
    return reference, subject


def _relative(rule: dict, observation: ImageObservation, limits: dict) -> dict | None:
    pair = _pair(rule, observation, limits)
    if isinstance(pair, dict):
        return pair
    reference, subject = pair
    delta = relative_x_axis_deg(reference.corners, subject.corners)
    expected = float(rule["expected_deg"])
    tolerance = float(rule["tolerance_deg"])
    evidence = {
        "relative_deg": _round(delta, 2),
        "expected_deg": expected,
        "tolerance_deg": tolerance,
        "reference_axis_deg": _round(_axis(reference), 2),
        "subject_axis_deg": _round(_axis(subject), 2),
        "unit": "degree",
        "corners_px": {
            str(reference.marker_id): _corners(reference),
            str(subject.marker_id): _corners(subject),
        },
    }
    if abs(delta - expected) <= tolerance:
        return {
            "status": "supported",
            "category": "supported",
            "image_id": observation.image_id,
            "confidence_area": min(reference.area_px, subject.area_px),
            "detail": (
                f"Tag {subject.marker_id} is within {tolerance:.0f}° of the expected edge "
                f"in {observation.image_id} (measured {_round(delta, 1)}°)."
            ),
            "evidence": evidence,
        }
    return {
        "status": "visible_mismatch",
        "category": "orientation_mismatch",
        "image_id": observation.image_id,
        "confidence_area": subject.area_px,
        "detail": (
            f"Tag {subject.marker_id} is turned in {observation.image_id}: "
            f"{_round(delta, 1)}° from tag {reference.marker_id}, outside ±{tolerance:.0f}°."
        ),
        "evidence": evidence,
    }


def _axis(marker: Marker) -> float:
    return x_axis_deg(marker.corners)


def _position(rule: dict, observation: ImageObservation, limits: dict) -> dict | None:
    pair = _pair(rule, observation, limits)
    if isinstance(pair, dict):
        return pair
    reference, subject = pair
    center = marker_frame_center(reference.corners, subject.corners)
    expected = rule["expected_center"]
    tolerance = rule["tolerance"]
    dx = abs(center[0] - float(expected[0]))
    dy = abs(center[1] - float(expected[1]))
    evidence = {
        "center_marker_widths": [_round(center[0], 3), _round(center[1], 3)],
        "expected_center": [float(expected[0]), float(expected[1])],
        "tolerance": [float(tolerance[0]), float(tolerance[1])],
        "unit": "base_marker_widths",
        "corners_px": {
            str(reference.marker_id): _corners(reference),
            str(subject.marker_id): _corners(subject),
        },
    }
    if dx <= float(tolerance[0]) and dy <= float(tolerance[1]):
        return {
            "status": "supported",
            "category": "supported",
            "image_id": observation.image_id,
            "confidence_area": subject.area_px,
            "detail": (
                f"Tag {subject.marker_id} sits in the expected band on tag {reference.marker_id} "
                f"in {observation.image_id}."
            ),
            "evidence": evidence,
        }
    return {
        "status": "visible_mismatch",
        "category": "placement_mismatch",
        "image_id": observation.image_id,
        "confidence_area": subject.area_px,
        "detail": (
            f"Tag {subject.marker_id} is outside the placement band in {observation.image_id} "
            f"(measured {_round(center[0], 2)}, {_round(center[1], 2)} base-tag widths)."
        ),
        "evidence": evidence,
    }
