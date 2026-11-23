# Data contract

Schema version `1.0.0`. Units are stated on every report.

## Session input

```json
{
  "schema_version": "1.0.0",
  "kit_id": "desk-ledge",
  "step_id": "seat-upright",
  "images": [
    {"id": "top-hidden", "path": "../../images/seat-top-hidden.png", "claimed_view": "top"}
  ]
}
```

| Field | Values | Bounds |
| --- | --- | --- |
| `schema_version` | `1.0.0` | Anything else is `unsupported_value`. |
| `kit_id` | `desk-ledge` | One kit in this release. |
| `step_id` | `place-base`, `seat-upright`, `set-lip` | Unknown ids are `unsupported_value`. |
| `images` | 1 or 2 objects | Zero or three or more is `malformed_input`. |
| `images[].id` | non-empty string | Unique inside the session. |
| `images[].path` | relative path | Must resolve inside the fixture root. Absolute paths and paths that escape the root are `path_rejected`. |
| `images[].claimed_view` | `top`, `left`, `right`, `front`, `back`, or omitted | A label is not trusted when it disagrees with the base tag. `underside` is `unsupported_value`. |

Image bytes, after the path is accepted:

| Limit | Value | Error |
| --- | --- | --- |
| File size | 8_000_000 bytes | `oversized_input` |
| Edge | 4096 px | `oversized_input` |
| Pixel count | 8_000_000 | `oversized_input` |
| Format | PNG or JPEG | `unreadable_image` |
| Smallest side | 16 px | `unreadable_image` |

Files are not resized. A resized photo could hide a tag.

## Report output

`completed` is true only when every rule on the step is `supported`.

Finding `status` is one of `supported`, `visible_mismatch`, `needs_another_view`, `retake`.

`category` names the reason: `supported`, `insufficient_evidence`, `identity_mismatch`, `orientation_mismatch`, `placement_mismatch`, `implausible_layout`, `low_resolution`, `poor_perspective`, `mirrored_layout`, `duplicate_marker`, `contradictory_views`.

Angles are degrees. Positions are widths of the base tag. Tag size is pixels.

A `request` object, when present, has `view` (`top`, `left`, or `front`) and a `prompt` sentence.

Input errors are a separate object: `ok: false`, `error_category`, `message`, optional `path`. They are not step verdicts.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Validation accepted, a report was written, or the demo metric held. |
| 1 | The demo metric failed. |
| 2 | The session or image was rejected. JSON on stdout, one sentence on stderr. |
| 3 | The report could not be written. |
