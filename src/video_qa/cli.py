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
from video_qa.profiles import BUILTINS, load_profile
from video_qa.reports import RENDERERS


def _timeout(value: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise argparse.ArgumentTypeError("timeout must be finite and positive")
    return result


def list_profiles_text() -> str:
    lines: list[str] = ["Built-in profiles and thresholds:\n"]
    for name, p in BUILTINS.items():
        lines.append(f"Profile: {name}")
        lines.append(
            f"  Raster: {p.width}x{p.height} "
            f"(aspect ratio: {p.aspect_ratio:.5f} +/- {p.aspect_tolerance:g})"
        )
        lines.append(f"  Frame rate: {p.min_fps:g}-{p.max_fps:g} fps")
        lines.append(f"  Duration: {p.min_duration:g}-{p.max_duration:g} s")
        lines.append(f"  Max freeze: <= {p.max_freeze:g} s (noise: {p.freeze_noise_db:g} dB)")
        lines.append(
            f"  Max black: <= {p.max_black:g} s "
            f"(pixel th: {p.black_pixel_threshold:g}, pic th: {p.black_picture_ratio:g})"
        )
        lines.append(f"  Max silence: <= {p.max_silence:g} s (noise: {p.silence_db:g} dB)")
        lines.append(f"  Audio required: {p.require_audio}")
        lines.append(f"  Max peak: <= {p.max_peak_dbfs:g} dBFS / dBTP")
        lines.append(
            f"  Target loudness: {p.target_lufs:g} +/- {p.lufs_tolerance:g} LUFS "
            f"(severity: {p.loudness_severity})"
        )
        lines.append("")
    return "\n".join(lines).strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="video-qa", description="Local rendered-video quality gate"
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--list-profiles",
        action="store_true",
        help="Print presets and their thresholds, then exit",
    )
    sub = parser.add_subparsers(dest="command")
    check = sub.add_parser("check", help="Decode a video and evaluate quality rules")
    check.add_argument("input", type=Path, nargs="?", default=None, help="Input video file path")
    check.add_argument(
        "--list-profiles",
        action="store_true",
        help="Print presets and their thresholds, then exit",
    )
    check.add_argument("--profile", default="shorts", help="Preset name or JSON/TOML path")
    for flag in ("max-freeze", "max-black", "max-silence", "max-duration", "target-lufs"):
        check.add_argument(f"--{flag}", type=float, default=None)
    check.add_argument(
        "--fail-on-warn",
        action="store_true",
        help="Treat warnings as failures and exit with code 1",
    )
    check.add_argument("--format", choices=RENDERERS, default="human")
    check.add_argument("--output", type=Path, help="Write report here instead of stdout")
    check.add_argument(
        "--timeout",
        type=_timeout,
        default=300,
        help="Timeout in seconds per subprocess (default: 300)",
    )
    check.add_argument("--ffmpeg", help="FFmpeg executable path")
    check.add_argument(
        "--ffprobe",
        help="ffprobe executable path (optional; falls back to ffmpeg when omitted)",
    )
    args = parser.parse_args(argv)
    if getattr(args, "list_profiles", False):
        print(list_profiles_text())
        return 0
    if not args.command:
        parser.print_help()
        return 2
    if args.input is None:
        check.error("the following arguments are required: input")
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
    if not report.passed or (getattr(args, "fail_on_warn", False) and report.warnings > 0):
        return 1
    return 0
