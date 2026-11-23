"""Human-readable summary. Machine JSON is the report object itself."""

from __future__ import annotations


def summary_text(report: dict) -> str:
    lines = [
        f"BuildCoach {report['kit_id']} {report['kit_version']} — {report['step_title']}",
        f"Completed: {'yes' if report['completed'] else 'no'}",
        "Units: angles in degrees, positions in base-tag widths, tag size in pixels.",
        "Limitations:",
    ]
    for item in report["limitations"]:
        lines.append(f"- {item}")
    lines.append("Findings:")
    for finding in report["findings"]:
        images = ", ".join(finding.get("image_ids") or []) or "none"
        lines.append(
            f"- {finding['rule_id']}: {finding['status'].replace('_', ' ')} (image {images}; {finding.get('category')})"
        )
        lines.append(f"  {finding['detail']}")
        request = finding.get("request")
        if request and request.get("prompt"):
            lines.append(f"  Ask: {request['prompt']} [view {request.get('view')}]")
        evidence = finding.get("evidence") or {}
        if "relative_deg" in evidence:
            lines.append(
                f"  Measured relative angle: {evidence['relative_deg']} degrees "
                f"(expected {evidence['expected_deg']} ± {evidence['tolerance_deg']})."
            )
        if "corners_px" in evidence and isinstance(evidence["corners_px"], dict):
            for marker_id, corners in evidence["corners_px"].items():
                lines.append(f"  Tag {marker_id} corners px: {corners}")
        elif "corners_px" in evidence:
            lines.append(f"  Corners px: {evidence['corners_px']}")
    lines.append("Inputs:")
    for item in report["inputs"]:
        lines.append(
            f"- {item['image_id']}: view {item['view_class']}, ids {item['detected_ids']}, sha256 {item['sha256'][:12]}"
        )
    return "\n".join(lines) + "\n"
