# BuildCoach

BuildCoach checks visible tag evidence for one practice kit, the Desk Ledge, and asks for another view when a required tag is hidden.

It is a workshop aid for makers and instructors. A passing result does not show that a part is fastened, that a joint is square as a structure, or that the stand can hold weight. A visible tag is not proof of physical attachment.

The shipped demo uses synthetic photographs generated in this repository. A separate phone-camera or printed-card run is not validated.

## What a check can say

Each finding is one of:

- **supported** — the required tags are visible and agree with that rule
- **visible mismatch** — the tags are visible and disagree with that rule, on a named image
- **needs another view** — a required tag or a usable angle is missing, with a named view to take
- **retake** — two clean views disagree, so neither one is kept

The upright step, given only the top photo, stays incomplete and asks for the left side. Adding the left photo completes it when tag 1 is parallel to the base tag within 12 degrees.

## Supported toolchain

- Python 3.12 on Linux is the tested platform. Python 3.11 or newer should work.
- Pinned packages are in `pyproject.toml`: `opencv-python-headless==4.12.0.88`, `numpy==2.2.6`, and, for development, `pytest==8.4.2` and `ruff==0.14.14`.
- No account, no GPU, and no network call during a check.

## Clean install

From a fresh clone:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Runtime only, without the test tools:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

## Demo

After setup, from the repository root:

```bash
python -m buildcoach demo --output out/demo
```

Expected result:

- Occluded completions: `0`
- Contradictory completions: `0`
- Clear correct completions: `3` of `3` (`place-base`, `seat-complete`, `lip-ok`)
- The command exits 0

Reports:

- `out/demo/demo.txt` and `out/demo/metric.json`
- `out/demo/seat-top-only/report.txt` — top photo only, asks for the left side, not complete
- `out/demo/seat-complete/report.txt` — left photo added, complete
- `out/demo/seat-rotated/report.txt` — upright tag turned a quarter turn, visible mismatch

The top-only prompt is: `Show the left side so tag 1 and the base tag are visible together.`

## Other commands

```bash
python -m buildcoach validate src/buildcoach/fixtures/sessions/valid/place-base.json
python -m buildcoach check src/buildcoach/fixtures/sessions/valid/seat-top-only.json --output out/one
python -m buildcoach serve --port 8765
```

`validate` prints JSON and exits 0 for a usable session, or exits 2 with an error category for a bad one. `check` writes `report.json` and `report.txt` even when the step is not complete. The upload page is on `http://127.0.0.1:8765/` and is loopback only. Use Tab to reach the step control, the file fields, and the sample links. The text under the drawing lists the same tag corners as the overlay.

Exit codes: `0` report or acceptance, `1` demo metric failed, `2` rejected input, `3` the report could not be written.

## Kit and fixtures

The guide is `src/buildcoach/fixtures/guide/desk-ledge.svg`. Printable tag sheets are `src/buildcoach/fixtures/tags/`. Photos are synthetic, seed `20261123`, produced by `scripts/render_fixtures.py`. Checksums and terms are in `src/buildcoach/fixtures/MANIFEST.json`. No third-party photographs are included. Shapes and limits are in `docs/data-contract.md`. The hand calculation for the angle and the placement band is in `src/buildcoach/fixtures/oracle/worked-example.md`.

## License and notices

MIT. See `LICENSE`. Third-party package licenses are in `THIRD_PARTY.md`. Security reports: `SECURITY.md`. Contribution steps: `CONTRIBUTING.md`. Release notes: `CHANGELOG.md`.
