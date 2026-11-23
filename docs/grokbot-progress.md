# Grokbot progress

## P01 — Research overlap and confirm the MVP

- **Phase and status:** P01 PASS
- **Files changed:** `docs/overlap.md`, `docs/project-contract.md`, `docs/research/p01-aruco-probe.json`
- **Commands and results:** Web and GitHub reads on 2026-11-23. Observed OpenCV 4.12.0 probe: visible ids `[0]`, covered ids `[]`, 90° roll ids `[0]`, no named view request and no completion object. Contender products were not executed because of a missing license or a paid model API. Decision: proceed with an original kit.
- **Artifact paths:** `docs/overlap.md`, `docs/project-contract.md`, `docs/research/p01-aruco-probe.json`
- **Open issues:** Phone-camera transfer is unmeasured.
- **Next phase:** P02

## P02 — Create the repository and data contracts

- **Phase and status:** P02 PASS
- **Files changed:** `pyproject.toml`, `src/buildcoach/`, `scripts/render_fixtures.py`, `README.md`, `docs/data-contract.md`, fixtures and sessions
- **Commands and results:**
  - `python -m pip install -e ".[dev]"` installed the pinned toolchain.
  - `python scripts/render_fixtures.py` wrote the synthetic kit. Detector id checks inside the generator passed.
  - `python -m buildcoach validate src/buildcoach/fixtures/sessions/valid/place-base.json` exited 0 with `ok: true`.
  - `python -m buildcoach validate src/buildcoach/fixtures/sessions/invalid/unknown-step.json` exited 2, category `unsupported_value`, message names `weld-frame` and the three supported steps.
- **Artifact paths:** `src/buildcoach/fixtures/`, `docs/data-contract.md`
- **Open issues:** None for this gate.
- **Next phase:** P03

## P03 — Build the working core

- **Phase and status:** P03 PASS
- **Files changed:** `src/buildcoach/evaluate.py`, `src/buildcoach/geometry.py`, `src/buildcoach/markers.py`, `tests/test_acceptance.py`, `tests/test_geometry.py`
- **Commands and results:** `python -m pytest -q` — 28 passed. Top-only session requests view `left` and does not complete. Adding the left photo completes. The quarter-turned tag is `orientation_mismatch` on `left-rotated` (about 98°). The rolled photo stays complete and the relative angle stays within 2° of the unrolled photo.
- **Artifact paths:** `out/demo/seat-top-only/report.json`, `out/demo/seat-complete/report.json`, `out/demo/seat-rotated/report.json` (local demo output, not committed)
- **Open issues:** None for this gate.
- **Next phase:** P04

## P04 — Ship the user workflow and reports

- **Phase and status:** P04 PASS
- **Files changed:** `src/buildcoach/cli.py`, `src/buildcoach/web.py`, `src/buildcoach/report.py`, `tests/test_web.py`
- **Commands and results:**
  - `python -m buildcoach demo --output out/demo` printed occluded completions 0, contradictory completions 0, clear correct completions 3 of 3, elapsed 0.159 s.
  - Browser check on `http://127.0.0.1:8765/`: Tab focused the skip link with a solid outline. The top-only sample announced "Completed: no." and the left-view prompt. The corner table listed tag 0 on `top-hidden` as `[[388.0, 588.0], [557.0, 588.0], [557.0, 757.0], [388.0, 757.0]]`, and the canvas had 1635 drawn pixels. The complete sample announced "Completed: yes." and the finding corners matched the overlay table for `left-ok`. The rotated sample announced "Completed: no." and named `left-rotated`. A non-image upload returned HTTP 400 with status text "The file is too small to be a PNG or JPEG." At 390 px width, `scrollWidth` equalled `clientWidth` (no horizontal overflow).
- **Artifact paths:** `out/demo/demo.txt`, `out/demo/metric.json`
- **Open issues:** None for this gate.
- **Next phase:** P05

## P05 — Verify correctness, security, and performance

- **Phase and status:** P05 PASS
- **Files changed:** `docs/validation.md`, `tests/test_security.py`, `tests/test_perf.py`
- **Commands and results:** `ruff check`, `ruff format --check`, and `compileall` passed. Pytest 28 passed. Demo budget 5.0 s, observed 0.159 s. Public advisory lookup: no advisory on `opencv-python-headless` 4.12.0.88; CVE-2025-53644 is fixed in OpenCV 4.12.0; CVE-2019-5063 stops at wheel 4.1.0.25; no direct NumPy 2.2.6 advisory on Snyk. No native sanitizer, because this repo does not compile C or C++.
- **Artifact paths:** `docs/validation.md`
- **Open issues:** Phone photos remain unvalidated and the report says so.
- **Next phase:** P06

## P06 — Prepare a reproducible open-source release

- **Phase and status:** P06 PASS
- **Files changed:** `README.md`, `SECURITY.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `THIRD_PARTY.md`, `.github/workflows/ci.yml`, `LICENSE` (unchanged MIT)
- **Commands and results:** README install and `python -m buildcoach demo --output out/demo` match the observed metric. `python -m build --wheel` produced `buildcoach-0.1.0-py3-none-any.whl` with 37 fixture files, including the kit, images, guide, tags, and manifest. The workflow uses `contents: read`, pinned action SHAs, and no secrets. Hosted CI is the P07 gate.
- **Artifact paths:** `.github/workflows/ci.yml`, wheel built under `/tmp/bc-dist` and not committed
- **Open issues:** Hosted CI has not run yet.
- **Next phase:** P07

## P07 — Publish and verify on GitHub

- **Phase and status:** P07 PASS
- **Files changed:** `docs/grokbot-progress.md` after the tested commit. The tag stays on the commit CI verified.
- **Commands and results:**
  - Destination checked: `https://github.com/Harry0052/buildcoach` is public, default branch `main`, license SPDX `MIT`. The push remote is that repository.
  - Pull request: https://github.com/Harry0052/buildcoach/pull/1
  - First CI run on `9d8503a` failed at ruff format for `web.py`: https://github.com/Harry0052/buildcoach/actions/runs/45116317686
  - Format fix `88492047703bf84f671575d741aed58b8a7298cb` passed CI: https://github.com/Harry0052/buildcoach/actions/runs/45116375813 (job https://github.com/Harry0052/buildcoach/actions/runs/45116375813/job/137500065263). Lint, compile, test, validate, demo, and artifact upload all succeeded.
  - Tag `v0.1.0` points at `88492047703bf84f671575d741aed58b8a7298cb`. A fresh clone of `https://github.com/Harry0052/buildcoach` at `v0.1.0` resolved to that SHA. Installing that tree into an empty prefix and running `python -m buildcoach demo` reported occluded completions 0, contradictory completions 0, clear correct completions 3 of 3. The top-only report asks for the left view and is not complete. The complete report is complete.
- **Artifact paths:** tag `v0.1.0`. Wheel is built from the tag with `python -m build --wheel` and is not committed. A GitHub Release object was not opened.
- **Open issues:** Phone-camera transfer is still unvalidated. The owner merges the pull request.
- **Next phase:** none. The owner merges.
