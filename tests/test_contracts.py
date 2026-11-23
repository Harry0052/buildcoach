import json
from pathlib import Path

from buildcoach.cli import main
from buildcoach.contracts import PACKAGE_FIXTURES
from buildcoach.errors import InputError
from buildcoach.normalize import decode_image

VALID = PACKAGE_FIXTURES / "sessions" / "valid" / "place-base.json"
INVALID = PACKAGE_FIXTURES / "sessions" / "invalid"


def test_validate_accepts_the_valid_fixture(capsys):
    assert main(["validate", str(VALID)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["step_id"] == "place-base"


def test_validate_rejects_unknown_step(capsys):
    assert main(["validate", str(INVALID / "unknown-step.json")]) == 2
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["ok"] is False
    assert payload["error_category"] == "unsupported_value"
    assert "weld-frame" in payload["message"]
    assert "Supported steps" in captured.err


def test_validate_rejects_path_escape(capsys):
    assert main(["validate", str(INVALID / "path-escape.json")]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["error_category"] == "path_rejected"


def test_validate_rejects_unknown_view(capsys):
    assert main(["validate", str(INVALID / "bad-view.json")]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["error_category"] == "unsupported_value"
    assert "underside" in payload["message"]


def test_oversized_and_unreadable_images():
    limits = {"max_bytes": 1000, "max_pixels": 8000000, "max_edge_px": 4096}
    try:
        decode_image(b"x" * 1001, limits)
    except InputError as exc:
        assert exc.category == "oversized_input"
    else:
        raise AssertionError("oversized bytes were accepted")
    try:
        decode_image(b"this is not an image, just text bytes!!", limits)
    except InputError as exc:
        assert exc.category == "unreadable_image"
    else:
        raise AssertionError("text was decoded as an image")


def test_check_writes_only_inside_the_output_directory(tmp_path: Path, capsys):
    output = tmp_path / "out"
    assert main(["check", str(VALID), "--output", str(output)]) == 0
    assert (output / "report.json").is_file()
    assert (output / "report.txt").is_file()
    report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    assert report["completed"] is True
    text = (output / "report.txt").read_text(encoding="utf-8")
    assert "not proof of physical attachment" in text
    capsys.readouterr()
