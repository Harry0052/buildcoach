# Security

BuildCoach reads local images and writes a report. It does not authenticate users and it does not call a network service during a check.

## Reporting

Open a private vulnerability report on the public repository:

https://github.com/Harry0052/buildcoach/security/advisories/new

Please include the version, the command you ran, and the kind of input that triggered the problem. Do not include personal photos if a synthetic file shows the same behavior.

## What a check is allowed to do

- Read session JSON and image files that stay inside the configured fixture or upload root.
- Reject files over 8 MB, over 4096 px on a side, or over 8 million pixels, without resizing them.
- Write `report.json` and `report.txt` only under the `--output` directory.
- Serve the upload page on `127.0.0.1` only.

A mirrored photo, a repeated tag id, or an implausible tag layout is a failed check, not a successful assembly.
