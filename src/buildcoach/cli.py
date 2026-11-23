"""Command line. Machine JSON goes to stdout. Diagnostics go to stderr."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from buildcoach import __version__
from buildcoach.contracts import PACKAGE_FIXTURES, load_json, load_kit, validate_session_body
from buildcoach.errors import InputError
from buildcoach.pipeline import check_session, write_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="buildcoach",
        description=(
            "Check visible tag evidence for the Desk Ledge practice kit. "
            "A pass is not a strength, torque, or safety result."
        ),
    )
    parser.add_argument("--version", action="version", version=f"buildcoach {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="Accept a session file or reject it with a category.")
    validate.add_argument("session", type=Path)

    check = sub.add_parser("check", help="Evaluate a session and write report.json and report.txt.")
    check.add_argument("session", type=Path)
    check.add_argument("--output", type=Path, required=True)

    demo = sub.add_parser("demo", help="Run the fixture demo and write a metric report.")
    demo.add_argument("--output", type=Path, default=Path("out/demo"))

    serve = sub.add_parser("serve", help="Local upload page on 127.0.0.1.")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--output", type=Path, default=Path("out/web"))

    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            return _validate(args.session)
        if args.command == "check":
            return _check(args.session, args.output)
        if args.command == "demo":
            return _demo(args.output)
        if args.command == "serve":
            from buildcoach.web import serve

            print(f"BuildCoach on http://127.0.0.1:{args.port}/", file=sys.stderr)
            serve(args.port, args.output)
            return 0
    except InputError as exc:
        print(json.dumps(exc.to_dict(), indent=2, sort_keys=True), flush=True)
        print(exc.message, file=sys.stderr)
        return 2
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    return 2


def _validate(session: Path) -> int:
    kit = load_kit()
    body = validate_session_body(load_json(session), kit)
    # Confirm the files exist and stay inside the fixture root when they are packaged.
    from buildcoach.contracts import resolve_image_path

    images = []
    for image in body["images"]:
        path = resolve_image_path(session, image["path"], PACKAGE_FIXTURES)
        images.append({"id": image["id"], "path": str(path)})
    print(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "ok": True,
                "kit_id": body["kit_id"],
                "step_id": body["step_id"],
                "images": images,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _check(session: Path, output: Path) -> int:
    report = check_session(session)
    json_path, text_path = write_report(report, output)
    print(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "ok": True,
                "completed": report["completed"],
                "step_id": report["step_id"],
                "report_json": str(json_path),
                "report_txt": str(text_path),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _demo(output: Path) -> int:
    """Run the acceptance sessions. Exit 1 when the metric fails."""
    started = time.perf_counter()
    cases = {
        "place-base": "sessions/valid/place-base.json",
        "seat-top-only": "sessions/valid/seat-top-only.json",
        "seat-complete": "sessions/valid/seat-complete.json",
        "seat-rolled": "sessions/valid/seat-rolled.json",
        "seat-rotated": "sessions/valid/seat-rotated.json",
        "seat-occluded": "sessions/valid/seat-occluded.json",
        "seat-contradictory": "sessions/valid/seat-contradictory.json",
        "seat-mirror": "sessions/valid/seat-mirror.json",
        "seat-duplicate": "sessions/valid/seat-duplicate.json",
        "seat-wrong-id": "sessions/valid/seat-wrong-id.json",
        "seat-far": "sessions/valid/seat-far.json",
        "seat-tiny": "sessions/valid/seat-tiny.json",
        "lip-ok": "sessions/valid/lip-ok.json",
        "lip-misplaced": "sessions/valid/lip-misplaced.json",
    }
    reports = {}
    for name, relative in cases.items():
        reports[name] = check_session(PACKAGE_FIXTURES / relative)
    elapsed = time.perf_counter() - started
    clear = ["place-base", "seat-complete", "lip-ok"]
    metric = {
        "schema_version": "1.0.0",
        "occluded_completions": int(reports["seat-occluded"]["completed"]),
        "contradictory_completions": int(reports["seat-contradictory"]["completed"]),
        "clear_correct_completions": sum(int(reports[name]["completed"]) for name in clear),
        "clear_correct_cases": clear,
        "completed": {name: report["completed"] for name, report in reports.items()},
        "elapsed_seconds": round(elapsed, 3),
    }
    output.mkdir(parents=True, exist_ok=True)
    # Keep one readable proof report plus the metric bundle.
    write_report(reports["seat-top-only"], output / "seat-top-only")
    write_report(reports["seat-complete"], output / "seat-complete")
    write_report(reports["seat-rotated"], output / "seat-rotated")
    (output / "metric.json").write_text(json.dumps(metric, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "BuildCoach fixture demo",
        f"Occluded completions: {metric['occluded_completions']} (required 0)",
        f"Contradictory completions: {metric['contradictory_completions']} (required 0)",
        f"Clear correct completions: {metric['clear_correct_completions']} of {len(clear)}",
        f"Elapsed seconds: {metric['elapsed_seconds']}",
        f"Reports: {output}",
    ]
    text = "\n".join(lines) + "\n"
    (output / "demo.txt").write_text(text, encoding="utf-8")
    print(text, end="")
    ok = (
        metric["occluded_completions"] == 0
        and metric["contradictory_completions"] == 0
        and metric["clear_correct_completions"] == len(clear)
        and reports["seat-top-only"]["completed"] is False
        and reports["seat-rolled"]["completed"] is True
        and reports["seat-rotated"]["completed"] is False
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
