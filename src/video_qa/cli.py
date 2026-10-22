"""Command-line interface. Quality/analysis failures exit 1; usage errors exit 2."""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import replace
from pathlib import Path

from video_qa import __version__
from video_qa.analyzer import AnalysisError, analyze
from video_qa.models import Check, Report
from video_qa.parsers import ParseError
from video_qa.profiles import load_profile
from video_qa.reports import RENDERERS


def _timeout(value: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise argparse.ArgumentTypeError("timeout must be finite and positive")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="video-qa", description="Local rendered-video quality gate"
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="Decode a video and evaluate quality rules")
    check.add_argument("input", type=Path)
    check.add_argument("--profile", default="shorts", help="Preset name or JSON/TOML path")
    for flag in ("max-freeze", "max-black", "max-silence", "max-duration", "target-lufs"):
        check.add_argument(f"--{flag}", type=float, default=None)
    check.add_argument("--format", choices=RENDERERS, default="human")
    check.add_argument("--output", type=Path, help="Write report here instead of stdout")
    check.add_argument(
        "--timeout",
        type=_timeout,
        default=300,
        help="Timeout in seconds per subprocess (default: 300)",
    )
    check.add_argument("--ffmpeg", help="FFmpeg executable path")
    check.add_argument("--ffprobe", help="ffprobe executable path (required separately from extra)")
    args = parser.parse_args(argv)
    try:
        profile = load_profile(args.profile)
        overrides = {
            key: getattr(args, key)
            for key in (
                "max_freeze",
                "max_black",
                "max_silence",
                "max_duration",
                "target_lufs",
            )
            if getattr(args, key) is not None
        }
        profile = replace(profile, **overrides)
    except (OSError, ValueError, ImportError) as exc:
        parser.error(str(exc))
    if args.output and args.output.resolve() == args.input.resolve():
        parser.error("Report output must differ from the input video")
    try:
        report = analyze(
            args.input, profile, ffmpeg=args.ffmpeg, ffprobe=args.ffprobe, timeout=args.timeout
        )
    except (AnalysisError, ParseError) as exc:
        report = Report(str(args.input), profile.name, [Check("analysis", "fail", str(exc))])
    rendered = RENDERERS[args.format](report) + "\n"
    try:
        if args.output:
            # Refuse existing hard links/symlinks to the source as well.
            if args.output.exists() and args.input.exists() and args.output.samefile(args.input):
                parser.error("Report output must differ from the input video")
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
    except OSError as exc:
        print(f"Cannot write report: {exc}", file=sys.stderr)
        return 1
    return 0 if report.passed else 1
