import json
from pathlib import Path

from buildcoach.contracts import PACKAGE_FIXTURES
from buildcoach.pipeline import check_session

ROOT = PACKAGE_FIXTURES / "sessions" / "valid"


def _report(name: str) -> dict:
    return check_session(ROOT / name)


def _finding(report: dict, rule_id: str) -> dict:
    return next(item for item in report["findings"] if item["rule_id"] == rule_id)


def test_hidden_top_requests_left_and_does_not_complete():
    report = _report("seat-top-only.json")
    assert report["completed"] is False
    finding = _finding(report, "upright-co-visible")
    assert finding["status"] == "needs_another_view"
    assert finding["request"]["view"] == "left"
    assert finding["request"]["prompt"] == ("Show the left side so tag 1 and the base tag are visible together.")
    assert finding["image_ids"] == ["top-hidden"]


def test_adding_the_left_view_completes():
    report = _report("seat-complete.json")
    assert report["completed"] is True
    orientation = _finding(report, "upright-orientation")
    assert orientation["status"] == "supported"
    assert orientation["image_ids"] == ["left-ok"]
    assert abs(orientation["evidence"]["relative_deg"]) <= 12


def test_quarter_turn_is_a_mismatch_on_that_image():
    report = _report("seat-rotated.json")
    assert report["completed"] is False
    orientation = _finding(report, "upright-orientation")
    assert orientation["status"] == "visible_mismatch"
    assert orientation["category"] == "orientation_mismatch"
    assert orientation["image_ids"] == ["left-rotated"]
    assert abs(orientation["evidence"]["relative_deg"]) > 45


def test_camera_roll_preserves_the_orientation_verdict():
    plain = _report("seat-complete.json")
    rolled = _report("seat-rolled.json")
    assert plain["completed"] is True
    assert rolled["completed"] is True
    plain_angle = _finding(plain, "upright-orientation")["evidence"]["relative_deg"]
    rolled_angle = _finding(rolled, "upright-orientation")["evidence"]["relative_deg"]
    assert abs(plain_angle - rolled_angle) < 2


def test_occluded_and_contradictory_have_zero_completions():
    occluded = _report("seat-occluded.json")
    contradictory = _report("seat-contradictory.json")
    assert occluded["completed"] is False
    assert contradictory["completed"] is False
    assert _finding(occluded, "upright-co-visible")["request"]["view"] == "left"
    retake = _finding(contradictory, "upright-orientation")
    assert retake["status"] == "retake"
    assert retake["category"] == "contradictory_views"
    assert set(retake["image_ids"]) == {"left-ok", "left-rotated"}
    assert retake["request"]["view"] == "left"


def test_clear_correct_cases_complete_separately():
    assert _report("place-base.json")["completed"] is True
    assert _report("seat-complete.json")["completed"] is True
    assert _report("lip-ok.json")["completed"] is True


def test_independent_failures():
    wrong = _report("seat-wrong-id.json")
    duplicate = _report("seat-duplicate.json")
    mirror = _report("seat-mirror.json")
    far = _report("seat-far.json")
    tiny = _report("seat-tiny.json")
    misplaced = _report("lip-misplaced.json")
    assert wrong["completed"] is False
    assert _finding(wrong, "upright-co-visible")["category"] == "identity_mismatch"
    assert duplicate["completed"] is False
    assert duplicate["findings"][0]["category"] == "duplicate_marker"
    assert mirror["completed"] is False
    assert mirror["findings"][0]["category"] == "mirrored_layout"
    assert far["completed"] is False
    assert _finding(far, "upright-co-visible")["category"] == "implausible_layout"
    assert tiny["completed"] is False
    assert _finding(tiny, "upright-co-visible")["category"] == "low_resolution"
    assert misplaced["completed"] is False


def test_reported_angle_matches_the_independent_formula():
    from tests.oracle_math import relative_deg

    report = _report("seat-rotated.json")
    evidence = _finding(report, "upright-orientation")["evidence"]
    reference = [tuple(point) for point in evidence["corners_px"]["0"]]
    subject = [tuple(point) for point in evidence["corners_px"]["1"]]
    assert abs(relative_deg(reference, subject) - evidence["relative_deg"]) < 0.05


def test_manifest_checksums_match_the_files():
    import hashlib

    manifest = json.loads((PACKAGE_FIXTURES / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["seed"] == 20261123
    for relative, digest in manifest["files"].items():
        path = PACKAGE_FIXTURES / relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest


def test_fixture_root_exists():
    assert (PACKAGE_FIXTURES / "guide" / "desk-ledge.svg").is_file()
    assert (PACKAGE_FIXTURES / "tags" / "tag-0.svg").is_file()
    assert Path(PACKAGE_FIXTURES / "images" / "seat-left-ok.png").stat().st_size > 1000
