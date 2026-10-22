#!/usr/bin/env python3
"""Generate sample reports in examples/ using synthetic video decoding."""

import subprocess
import tempfile
from dataclasses import replace
from pathlib import Path

from video_qa.analyzer import analyze, find_ffmpeg
from video_qa.profiles import Profile
from video_qa.reports import human_report, json_report, junit_report


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    examples_dir = repo_root / "examples"
    examples_dir.mkdir(exist_ok=True)

    ffmpeg = find_ffmpeg()
    profile = Profile(name="shorts")

    with tempfile.TemporaryDirectory() as td:
        clip = Path(td) / "out.mp4"
        subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostdin",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc=size=1080x1920:rate=30",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440",
                "-t",
                "3",
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                str(clip),
            ],
            capture_output=True,
            check=True,
        )

        report = analyze(clip, profile, ffmpeg=ffmpeg)
        clean_report = replace(report, path="out.mp4")

        json_out = json_report(clean_report) + "\n"
        junit_out = junit_report(clean_report) + "\n"
        human_out = human_report(clean_report) + "\n"

        (examples_dir / "report.json").write_text(json_out, encoding="utf-8")
        (examples_dir / "junit.xml").write_text(junit_out, encoding="utf-8")

        print("=== Generated Human Report ===")
        print(human_out)
        print("=== Generated JUnit XML ===")
        print(junit_out)
        print("Wrote examples/report.json and examples/junit.xml successfully.")


if __name__ == "__main__":
    main()
