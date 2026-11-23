import json
import threading
import urllib.request
from pathlib import Path

from buildcoach.contracts import PACKAGE_FIXTURES
from buildcoach.web import make_server, parse_multipart, render_page


def test_page_exposes_keyboard_and_status_hooks():
    html = render_page()
    assert 'for="step"' in html
    assert 'id="step"' in html
    assert 'for="photo1"' in html
    assert ":focus-visible" in html
    assert 'role="status"' in html
    assert 'aria-live="polite"' in html
    assert 'name="viewport"' in html
    assert "max-width: 480px" in html
    assert "Not a strength" in html or "safe to load" in html


def test_parse_multipart_round_trip():
    body, content_type = _encode(
        [("step_id", "seat-upright")],
        [("photo1", "top.png", b"\x89PNG fake", "image/png")],
    )
    fields, files = parse_multipart(content_type, body)
    assert fields["step_id"] == "seat-upright"
    assert files["photo1"][0] == "top.png"
    assert files["photo1"][1].startswith(b"\x89PNG")


def test_sample_and_upload_round_trip(tmp_path: Path):
    server = make_server(tmp_path, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        page = urllib.request.urlopen(f"http://127.0.0.1:{port}/sample/seat-top-only").read().decode()
        assert "Show the left side so tag 1 and the base tag are visible together." in page
        assert "top-hidden" in page
        assert "Completed: no" in page
        export = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/export.json").read())
        assert export["completed"] is False
        text = urllib.request.urlopen(f"http://127.0.0.1:{port}/export.txt").read().decode()
        assert "top-hidden" in text
        image = (PACKAGE_FIXTURES / "images" / "seat-left-rotated.png").read_bytes()
        body, content_type = _encode(
            [("step_id", "seat-upright")],
            [("photo1", "turned.png", image, "image/png")],
        )
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/check",
            data=body,
            headers={"Content-Type": content_type},
        )
        uploaded = urllib.request.urlopen(request).read().decode()
        assert "orientation mismatch" in uploaded or "turned" in uploaded
        assert "turned.png" in uploaded
        bad = urllib.request.Request(
            f"http://127.0.0.1:{port}/check",
            data=b"nope",
            headers={"Content-Type": "text/plain"},
        )
        try:
            urllib.request.urlopen(bad)
        except urllib.error.HTTPError as exc:
            assert exc.code == 400
            explanation = exc.read().decode()
            assert "boundary" in explanation.lower() or "form" in explanation.lower()
        else:
            raise AssertionError("malformed upload was accepted")
    finally:
        server.shutdown()
        server.server_close()


def _encode(fields, files):
    boundary = "----BuildCoachBoundary"
    parts = []
    for key, value in fields:
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    for key, filename, data, content_type in files:
        parts.append(
            (
                f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"; filename="{filename}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode()
            + data
            + b"\r\n"
        )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"
