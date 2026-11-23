"""Versioned session and kit files."""

from __future__ import annotations

import json
from pathlib import Path

from buildcoach.errors import InputError

SCHEMA_VERSION = "1.0.0"
ALLOWED_VIEWS = {"top", "left", "right", "front", "back"}
PACKAGE_FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_json(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError("unavailable_input", f"Could not read {path.name}.", str(path)) from exc
    try:
        body = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InputError(
            "malformed_input",
            f"{path.name} is not valid JSON: {exc.msg} at line {exc.lineno}.",
            str(path),
        ) from exc
    if not isinstance(body, dict):
        raise InputError("malformed_input", f"{path.name} must be a JSON object.", str(path))
    return body


def load_kit(path: Path | None = None) -> dict:
    kit_path = path or (PACKAGE_FIXTURES / "kit" / "desk-ledge.json")
    kit = load_json(kit_path)
    if kit.get("schema_version") != SCHEMA_VERSION:
        raise InputError(
            "unsupported_value",
            f"Kit schema_version must be {SCHEMA_VERSION}.",
            "schema_version",
        )
    if kit.get("kit_id") != "desk-ledge":
        raise InputError("unsupported_value", "This build only loads the desk-ledge kit.", "kit_id")
    steps = kit.get("steps")
    if not isinstance(steps, list) or not steps:
        raise InputError("malformed_input", "Kit steps are missing.", "steps")
    return kit


def step_by_id(kit: dict, step_id: str) -> dict:
    for step in kit["steps"]:
        if step.get("id") == step_id:
            return step
    known = ", ".join(step["id"] for step in kit["steps"])
    raise InputError(
        "unsupported_value",
        f"Unknown step_id {step_id!r}. Supported steps: {known}.",
        "step_id",
    )


def _require_str(body: dict, key: str) -> str:
    value = body.get(key)
    if not isinstance(value, str) or not value.strip():
        raise InputError("malformed_input", f"{key} is required and must be a non-empty string.", key)
    return value


def validate_session_body(body: dict, kit: dict) -> dict:
    """Validate a session object. Does not read image bytes."""
    if body.get("schema_version") != SCHEMA_VERSION:
        raise InputError(
            "unsupported_value",
            f"schema_version must be {SCHEMA_VERSION}.",
            "schema_version",
        )
    kit_id = _require_str(body, "kit_id")
    if kit_id != kit["kit_id"]:
        raise InputError(
            "unsupported_value",
            f"kit_id must be {kit['kit_id']!r}.",
            "kit_id",
        )
    step_id = _require_str(body, "step_id")
    step_by_id(kit, step_id)
    images = body.get("images")
    if not isinstance(images, list):
        raise InputError("malformed_input", "images must be a list.", "images")
    limits = kit["limits"]
    if len(images) < int(limits["min_images"]) or len(images) > int(limits["max_images"]):
        raise InputError(
            "malformed_input",
            (f"Submit {limits['min_images']} or {limits['max_images']} images. This session has {len(images)}."),
            "images",
        )
    seen: set[str] = set()
    cleaned = []
    for index, image in enumerate(images):
        prefix = f"images[{index}]"
        if not isinstance(image, dict):
            raise InputError("malformed_input", f"{prefix} must be an object.", prefix)
        image_id = image.get("id")
        if not isinstance(image_id, str) or not image_id.strip():
            raise InputError("malformed_input", f"{prefix}.id is required.", f"{prefix}.id")
        if image_id in seen:
            raise InputError("malformed_input", f"Duplicate image id {image_id!r}.", f"{prefix}.id")
        seen.add(image_id)
        rel = image.get("path")
        if not isinstance(rel, str) or not rel.strip():
            raise InputError("malformed_input", f"{prefix}.path is required.", f"{prefix}.path")
        claimed = image.get("claimed_view")
        if claimed is not None:
            if not isinstance(claimed, str) or claimed not in ALLOWED_VIEWS:
                allowed = ", ".join(sorted(ALLOWED_VIEWS))
                raise InputError(
                    "unsupported_value",
                    f"{prefix}.claimed_view must be one of: {allowed}. Got {claimed!r}.",
                    f"{prefix}.claimed_view",
                )
        cleaned.append({"id": image_id, "path": rel, "claimed_view": claimed})
    return {
        "schema_version": SCHEMA_VERSION,
        "kit_id": kit_id,
        "step_id": step_id,
        "images": cleaned,
    }


def resolve_image_path(session_path: Path, relative: str, root: Path) -> Path:
    """Resolve an image path and keep it inside the allowed root."""
    raw = Path(relative)
    if raw.is_absolute() or "\\" in relative:
        raise InputError(
            "path_rejected",
            "Image paths must be relative to the session file and stay inside the fixture root.",
            relative,
        )
    if any(part == ".." for part in raw.parts) and not _stays_inside(session_path, raw, root):
        raise InputError(
            "path_rejected",
            "That image path leaves the allowed fixture directory. Use a path inside the kit folder.",
            relative,
        )
    # Reject odd parts even when they would normalize inside.
    if any(part in {"", ".", ".."} and part == "" for part in raw.parts):
        raise InputError("path_rejected", "Image path is empty.", relative)
    candidate = (session_path.parent / raw).resolve()
    allowed = root.resolve()
    if not _is_relative_to(candidate, allowed):
        raise InputError(
            "path_rejected",
            "That image path leaves the allowed fixture directory. Use a path inside the kit folder.",
            relative,
        )
    if not candidate.is_file():
        raise InputError(
            "unavailable_input",
            f"Image file {relative} was not found next to the session.",
            relative,
        )
    return candidate


def _stays_inside(session_path: Path, raw: Path, root: Path) -> bool:
    try:
        candidate = (session_path.parent / raw).resolve()
    except OSError:
        return False
    return _is_relative_to(candidate, root.resolve())


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def load_session(session_path: Path, kit: dict, root: Path | None = None) -> dict:
    """Validate a session file and attach absolute image paths."""
    body = validate_session_body(load_json(session_path), kit)
    allowed = root or PACKAGE_FIXTURES
    images = []
    for image in body["images"]:
        resolved = resolve_image_path(session_path, image["path"], allowed)
        images.append({**image, "absolute_path": resolved})
    body["images"] = images
    body["session_path"] = str(session_path)
    return body
