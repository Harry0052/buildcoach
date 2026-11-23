"""Small local upload page. Binds to loopback. No accounts and no remote calls."""

from __future__ import annotations

import hashlib
import html
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from buildcoach.contracts import PACKAGE_FIXTURES, load_kit
from buildcoach.errors import InputError
from buildcoach.evaluate import LIMITATIONS, evaluate_step, observe_image
from buildcoach.normalize import decode_image
from buildcoach.pipeline import check_session
from buildcoach.report import summary_text

MAX_BODY = 16_000_000


def make_server(output_dir: Path, port: int = 0) -> ThreadingHTTPServer:
    output_dir.mkdir(parents=True, exist_ok=True)
    return ThreadingHTTPServer(("127.0.0.1", port), _handler_factory(output_dir))


def serve(port: int, output_dir: Path) -> None:
    server = make_server(output_dir, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return
    finally:
        server.server_close()


def render_page(report: dict | None = None, error: str | None = None) -> str:
    status = "Choose a step and submit one or two photos."
    if error:
        status = error
    elif report is not None:
        status = "Check finished. Completed: " + ("yes" if report["completed"] else "no") + "."
    findings = ""
    overlay = "[]"
    if report is not None:
        overlay = json.dumps(_overlay_payload(report)).replace("<", "\\u003c")
        blocks = []
        for finding in report["findings"]:
            images = ", ".join(finding.get("image_ids") or []) or "none"
            request = finding.get("request") or {}
            extra = ""
            if request.get("prompt"):
                extra = f"<p>{html.escape(request['prompt'])}</p>"
            evidence = finding.get("evidence") or {}
            corner_rows = _corner_rows(evidence)
            blocks.append(
                "<li>"
                f"<p><strong>{html.escape(finding['rule_id'])}</strong> "
                f"{html.escape(finding['status'].replace('_', ' '))} "
                f"on image {html.escape(images)}.</p>"
                f"<p>{html.escape(finding['detail'])}</p>"
                f"{extra}{corner_rows}</li>"
            )
        findings = '<ol id="findings">' + "".join(blocks) + "</ol>" + _input_corner_table(report)
    limits = "".join(f"<li>{html.escape(item)}</li>" for item in LIMITATIONS)
    empty_findings = '<p id="findings">No check yet.</p>'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BuildCoach</title>
<style>
  body {{ margin: 1rem; font-family: sans-serif; max-width: 52rem; line-height: 1.4; }}
  :focus-visible {{ outline: 3px solid #0b6; outline-offset: 2px; }}
  label {{ display: block; margin-top: 0.8rem; font-weight: 600; }}
  input, select, button, a {{ font: inherit; }}
  button, .samples a {{ margin: 0.4rem 0.4rem 0 0; }}
  canvas {{ max-width: 100%; height: auto; background: #eee; margin-top: 1rem; }}
  table {{ border-collapse: collapse; width: 100%; }}
  td, th {{ border: 1px solid #ccc; padding: 0.3rem; text-align: left; }}
  @media (max-width: 480px) {{
    body {{ margin: 0.5rem; }}
    button, input, select {{ width: 100%; }}
  }}
</style>
</head>
<body>
<a href="#step">Skip to the step control</a>
<h1>BuildCoach</h1>
<p>Desk Ledge practice kit. Check visible tags, then read the text under the drawing.</p>
<ul>{limits}</ul>
<form method="post" action="/check" enctype="multipart/form-data">
  <label for="step">Step</label>
  <select id="step" name="step_id">
    <option value="place-base">1. Place the base</option>
    <option value="seat-upright" selected>2. Seat the upright</option>
    <option value="set-lip">3. Set the lip</option>
  </select>
  <label for="photo1">First photo</label>
  <input id="photo1" name="photo1" type="file" accept="image/png,image/jpeg">
  <label for="photo2">Second photo, optional</label>
  <input id="photo2" name="photo2" type="file" accept="image/png,image/jpeg">
  <button type="submit">Check evidence</button>
</form>
<p class="samples">Samples:
  <a href="/sample/seat-top-only">Top photo hides the upright</a>
  <a href="/sample/seat-complete">Add the left photo</a>
  <a href="/sample/seat-rotated">Upright tag turned</a>
</p>
<div id="status" role="status" aria-live="polite">{html.escape(status)}</div>
<canvas id="overlay" width="640" height="480" aria-hidden="true"></canvas>
<h2>Text evidence</h2>
{findings or empty_findings}
<p><a href="/export.json">Download JSON</a> <a href="/export.txt">Download summary</a></p>
<script>
const payload = {overlay};
const canvas = document.getElementById("overlay");
const ctx = canvas.getContext("2d");
function draw() {{
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (!payload.length) return;
  const item = payload[0];
  const maxX = Math.max(...item.markers.flatMap(m => (m.corners_px || []).map(p => p[0])), 1);
  const maxY = Math.max(...item.markers.flatMap(m => (m.corners_px || []).map(p => p[1])), 1);
  const sx = canvas.width / maxX;
  const sy = canvas.height / maxY;
  ctx.strokeStyle = "#083";
  ctx.lineWidth = 2;
  ctx.font = "14px sans-serif";
  for (const marker of item.markers) {{
    ctx.beginPath();
    (marker.corners_px || []).forEach((point, index) => {{
      const x = point[0] * sx;
      const y = point[1] * sy;
      if (index === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }});
    ctx.closePath();
    ctx.stroke();
    const origin = (marker.corners_px || [[0, 0]])[0];
    ctx.fillText("tag " + marker.id + " " + item.image_id, origin[0] * sx, origin[1] * sy);
  }}
}}
draw();
</script>
</body>
</html>
"""


def _overlay_payload(report: dict) -> list[dict]:
    payload = []
    for item in report["inputs"]:
        payload.append(
            {
                "image_id": item["image_id"],
                "markers": item.get("markers") or [],
            }
        )
    return payload


def _input_corner_table(report: dict) -> str:
    rows = []
    for item in report["inputs"]:
        for marker in item.get("markers") or []:
            rows.append(
                "<tr><td>"
                + html.escape(item["image_id"])
                + "</td><td>"
                + html.escape(str(marker["id"]))
                + "</td><td>"
                + html.escape(json.dumps(marker.get("corners_px")))
                + "</td></tr>"
            )
    if not rows:
        return ""
    return (
        "<table id=\"overlay-corners\"><caption>Corners drawn on the overlay</caption>"
        "<thead><tr><th>Image</th><th>Tag</th><th>Corners px</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _corner_rows(evidence: dict) -> str:
    corners = evidence.get("corners_px")
    if not isinstance(corners, dict):
        return ""
    rows = []
    for marker_id, points in corners.items():
        rows.append(
            "<tr><td>" + html.escape(str(marker_id)) + "</td><td>" + html.escape(json.dumps(points)) + "</td></tr>"
        )
    return (
        "<table><caption>Overlay corners in pixels</caption>"
        "<thead><tr><th>Tag</th><th>Corners</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def _handler_factory(output_dir: Path):
    state = {"report": None, "text": ""}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            return

        def do_GET(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            if path == "/favicon.ico":
                self._send(204, "image/x-icon", b"")
                return
            if path == "/":
                page = render_page(state["report"])
                self._send(200, "text/html; charset=utf-8", page.encode("utf-8"))
                return
            if path.startswith("/sample/"):
                name = path.removeprefix("/sample/")
                self._sample(name)
                return
            if path == "/export.json":
                if state["report"] is None:
                    self._send(404, "application/json", b'{"ok": false, "message": "No report yet."}\n')
                    return
                body = json.dumps(state["report"], indent=2, sort_keys=True).encode("utf-8")
                self._send(200, "application/json", body)
                return
            if path == "/export.txt":
                if not state["text"]:
                    self._send(404, "text/plain; charset=utf-8", b"No report yet.\n")
                    return
                self._send(200, "text/plain; charset=utf-8", state["text"].encode("utf-8"))
                return
            self._send(404, "text/plain; charset=utf-8", b"Not found.\n")

        def do_POST(self) -> None:  # noqa: N802
            if self.path.split("?", 1)[0] != "/check":
                self._send(404, "text/plain; charset=utf-8", b"Not found.\n")
                return
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY:
                self._fail("The upload is empty or larger than 16 MB.")
                return
            body = self.rfile.read(length)
            try:
                fields, files = parse_multipart(self.headers.get("Content-Type", ""), body)
            except ValueError as exc:
                self._fail(str(exc))
                return
            step_id = fields.get("step_id", "seat-upright")
            try:
                kit = load_kit()
                observations = []
                for key in ("photo1", "photo2"):
                    upload = files.get(key)
                    if upload is None:
                        continue
                    filename, data = upload
                    if not data:
                        continue
                    gray = decode_image(data, kit["limits"])
                    observations.append(
                        observe_image(
                            _safe_id(filename or key),
                            gray,
                            None,
                            hashlib.sha256(data).hexdigest(),
                            kit["limits"],
                        )
                    )
                if not observations:
                    self._fail("Choose at least one PNG or JPEG.")
                    return
                if len(observations) > int(kit["limits"]["max_images"]):
                    self._fail("Submit at most two photos.")
                    return
                report = evaluate_step(kit, step_id, observations)
            except InputError as exc:
                self._fail(exc.message)
                return
            self._store(report)
            page = render_page(report)
            self._send(200, "text/html; charset=utf-8", page.encode("utf-8"))

        def _sample(self, name: str) -> None:
            allowed = {
                "seat-top-only": "sessions/valid/seat-top-only.json",
                "seat-complete": "sessions/valid/seat-complete.json",
                "seat-rotated": "sessions/valid/seat-rotated.json",
            }
            relative = allowed.get(name)
            if relative is None:
                self._fail("Unknown sample.")
                return
            try:
                report = check_session(PACKAGE_FIXTURES / relative)
            except InputError as exc:
                self._fail(exc.message)
                return
            self._store(report)
            page = render_page(report)
            self._send(200, "text/html; charset=utf-8", page.encode("utf-8"))

        def _store(self, report: dict) -> None:
            state["report"] = report
            state["text"] = summary_text(report)
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "report.json").write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            (output_dir / "report.txt").write_text(state["text"], encoding="utf-8")

        def _fail(self, message: str) -> None:
            page = render_page(state["report"], error=message)
            self._send(400, "text/html; charset=utf-8", page.encode("utf-8"))

        def _send(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    return Handler


def _safe_id(filename: str) -> str:
    stem = Path(filename).name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip(".-")
    return (cleaned or "photo")[:80]


def parse_multipart(content_type: str, body: bytes) -> tuple[dict[str, str], dict[str, tuple[str, bytes]]]:
    match = re.search(r"boundary=([^;]+)", content_type)
    if not match:
        raise ValueError("The form body is missing a multipart boundary.")
    boundary = match.group(1).strip().strip('"').encode("utf-8")
    fields: dict[str, str] = {}
    files: dict[str, tuple[str, bytes]] = {}
    for chunk in body.split(b"--" + boundary):
        if not chunk or chunk in {b"--", b"--\r\n"} or chunk.strip() in {b"", b"--"}:
            continue
        chunk = chunk.removeprefix(b"\r\n").removesuffix(b"\r\n").removesuffix(b"--")
        header_blob, separator, data = chunk.partition(b"\r\n\r\n")
        if not separator:
            continue
        header_text = header_blob.decode("utf-8", errors="replace")
        disposition = ""
        for line in header_text.split("\r\n"):
            if line.lower().startswith("content-disposition:"):
                disposition = line
        name_match = re.search(r'name="([^"]+)"', disposition)
        if not name_match:
            continue
        name = name_match.group(1)
        file_match = re.search(r'filename="([^"]*)"', disposition)
        payload = data[:-2] if data.endswith(b"\r\n") else data
        if file_match:
            files[name] = (file_match.group(1), payload)
        else:
            fields[name] = payload.decode("utf-8", errors="replace").strip()
    return fields, files
