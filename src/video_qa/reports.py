"""Human, strict JSON, and JUnit XML views of the same report."""

from __future__ import annotations

import json
import math
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict
from typing import Any

from video_qa.models import Report


def _json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return "-inf" if value == -math.inf else None
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def json_report(report: Report) -> str:
    data = {
        "schema_version": 1,
        **asdict(report),
        "passed": report.passed,
        "failures": report.failures,
        "warnings": report.warnings,
    }
    return json.dumps(_json_safe(data), indent=2, ensure_ascii=True, allow_nan=False)


def _xml_safe(text: str) -> str:
    return re.sub(r"[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD\U00010000-\U0010FFFF]", "?", text)


def junit_report(report: Report) -> str:
    suite = ET.Element(
        "testsuite",
        {
            "name": "video-qa",
            "tests": str(len(report.checks)),
            "failures": str(report.failures),
            "errors": "0",
            "skipped": "0",
        },
    )
    properties = ET.SubElement(suite, "properties")
    for key, value in (
        ("input", report.path),
        ("profile", report.profile),
        ("warnings", str(report.warnings)),
    ):
        ET.SubElement(properties, "property", {"name": key, "value": _xml_safe(value)})
    for check in report.checks:
        case = ET.SubElement(
            suite,
            "testcase",
            {
                "classname": "video_qa",
                "name": _xml_safe(check.name),
            },
        )
        if check.status == "fail":
            ET.SubElement(case, "failure", {"message": _xml_safe(check.message)}).text = _xml_safe(
                check.message
            )
        elif check.status == "warn":
            ET.SubElement(case, "system-out").text = "WARNING: " + _xml_safe(check.message)
    return ET.tostring(suite, encoding="unicode", xml_declaration=True)


def human_report(report: Report) -> str:
    lines = [f"{report.path} (profile: {report.profile})", "STATUS  CHECK           DETAIL"]
    lines.extend(f"{c.status.upper():<7} {c.name:<15} {c.message}" for c in report.checks)
    lines.append(
        f"{'PASS' if report.passed else 'FAIL'}: "
        f"{report.failures} failure(s), {report.warnings} warning(s)"
    )
    return "\n".join(lines)


RENDERERS = {"human": human_report, "json": json_report, "junit": junit_report}
