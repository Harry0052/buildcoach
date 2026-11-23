"""Load a session from disk and run the evaluator. This is the public check path."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from buildcoach.contracts import PACKAGE_FIXTURES, load_kit, load_session
from buildcoach.evaluate import evaluate_step, observe_image
from buildcoach.normalize import decode_image
from buildcoach.report import summary_text


def check_session(session_path: Path, kit_path: Path | None = None, root: Path | None = None) -> dict:
    kit = load_kit(kit_path)
    allowed = root or PACKAGE_FIXTURES
    session = load_session(session_path, kit, allowed)
    limits = kit["limits"]
    observations = []
    for image in session["images"]:
        data = image["absolute_path"].read_bytes()
        gray = decode_image(data, limits)
        digest = hashlib.sha256(data).hexdigest()
        observations.append(
            observe_image(
                image["id"],
                gray,
                image.get("claimed_view"),
                digest,
                limits,
            )
        )
    report = evaluate_step(kit, session["step_id"], observations)
    report["session_path"] = session["session_path"]
    return report


def write_report(report: dict, output_dir: Path) -> tuple[Path, Path]:
    """Write JSON and text only inside output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    resolved = output_dir.resolve()
    json_path = (resolved / "report.json").resolve()
    text_path = (resolved / "report.txt").resolve()
    if not _inside(json_path, resolved) or not _inside(text_path, resolved):
        raise OSError("Refusing to write a report outside the output directory.")
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    text_path.write_text(summary_text(report), encoding="utf-8")
    return json_path, text_path


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
