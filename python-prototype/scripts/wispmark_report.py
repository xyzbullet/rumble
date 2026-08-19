#!/usr/bin/env python3
"""Parse a WispMark markdown report and compare throughput against a 10 Gb/s target.

Example usage:
    python scripts/wispmark_report.py /workspace/wispmark/wispmark-results.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

TARGET_GBPS = 10.0


def parse_markdown(path: Path) -> list[tuple[str, float]]:
    """Return (label, value_mib_s) for rows in the markdown tables."""
    text = path.read_text(encoding="utf-8")
    rows: list[tuple[str, float]] = []
    for line in text.splitlines():
        if "|" not in line or "---" in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        label = cells[0]
        if not label or label in {"|", "--"}:
            continue
        numeric = []
        for cell in cells[1:]:
            if not cell:
                continue
            match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(?:MiB/s|GiB/s|MB/s|GB/s)", cell, re.I)
            if match:
                numeric.append(float(match.group(1)))
        if numeric:
            rows.append((label, max(numeric)))
    return rows


def main() -> int:
    if len(sys.argv) < 2:
        default = Path("/workspaces/wispmark/wispmark-results.md")
        if not default.exists():
            print("usage: python wispmark_report.py <path/to/wispmark-results.md>")
            return 2
        report_path = default
    else:
        report_path = Path(sys.argv[1])

    if not report_path.exists():
        print(f"Report not found: {report_path}")
        return 2

    results = parse_markdown(report_path)
    if not results:
        print(f"No benchmark rows found in {report_path}")
        return 2

    best_label, best_value = max(results, key=lambda item: item[1])
    best_gbps = (best_value * 8.0) / 1000.0
    status = "PASS" if best_gbps >= TARGET_GBPS else "FAIL"

    print(f"WispMark report: {report_path}")
    print(f"Best throughput: {best_value:.2f} MiB/s ({best_gbps:.2f} Gb/s)")
    print(f"Target: {TARGET_GBPS:.0f} Gb/s")
    print(f"Result: {status}")
    print()
    print("Top entries:")
    for label, value in sorted(results, key=lambda item: item[1], reverse=True)[:5]:
        print(f"- {label}: {value:.2f} MiB/s ({(value * 8.0) / 1000.0:.2f} Gb/s)")

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
